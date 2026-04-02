from fastapi import FastAPI, APIRouter, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio
import ccxt
import pandas as pd
import ta as ta_lib
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Binance setup
SYMBOL = os.environ.get('TRADING_SYMBOL', 'BTC/USDT')
TIMEFRAME = os.environ.get('TRADING_TIMEFRAME', '1m')

def create_exchange():
    # Use binanceus for public data (binance.com geo-restricted from this datacenter)
    # Auth keys stored for trading when deployed on unrestricted infrastructure
    config = {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}
    return ccxt.binanceus(config)

exchange = create_exchange()

# Bot state
bot_state = {
    "running": False,
    "task": None,
    "last_price": None,
    "last_signal": "WAIT",
    "last_indicators": {},
    "last_orderbook": {},
    "last_ai_insight": "",
    "started_at": None,
    "iterations": 0,
    "errors": [],
}

# App setup
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
class BotStatus(BaseModel):
    running: bool
    last_price: Optional[float] = None
    last_signal: str = "WAIT"
    started_at: Optional[str] = None
    iterations: int = 0
    symbol: str = SYMBOL
    timeframe: str = TIMEFRAME

class SignalRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str
    price: float
    signal: str
    rsi: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None
    ob_signal: str = ""
    ai_signal: str = ""
    rsi_signal: str = ""
    ai_insight: str = ""

class AIInsight(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str
    insight: str
    signal: str
    price: float

# ---- MARKET DATA ----

def fetch_price_sync():
    try:
        ticker = exchange.fetch_ticker(SYMBOL)
        return {
            "price": ticker['last'],
            "high": ticker.get('high'),
            "low": ticker.get('low'),
            "volume": ticker.get('baseVolume'),
            "change": ticker.get('percentage'),
            "bid": ticker.get('bid'),
            "ask": ticker.get('ask'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
        return None

def fetch_orderbook_sync():
    try:
        ob = exchange.fetch_order_book(SYMBOL, limit=10)
        bids = ob['bids'][:10]
        asks = ob['asks'][:10]
        bid_vol = sum([b[1] for b in bids])
        ask_vol = sum([a[1] for a in asks])
        signal = 'BUY' if bid_vol > ask_vol else 'SELL'
        return {
            "bids": [{"price": b[0], "amount": b[1]} for b in bids],
            "asks": [{"price": a[0], "amount": a[1]} for a in asks],
            "bid_volume": round(bid_vol, 4),
            "ask_volume": round(ask_vol, 4),
            "signal": signal,
            "ratio": round(bid_vol / ask_vol, 2) if ask_vol > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching orderbook: {e}")
        return None

def fetch_ohlcv_sync(limit=200):
    try:
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=limit)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV: {e}")
        return None

def compute_indicators(df):
    if df is None or len(df) < 50:
        return df, {}
    df['rsi'] = ta_lib.momentum.RSIIndicator(df['close']).rsi()
    df['ema50'] = ta_lib.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema200'] = ta_lib.trend.EMAIndicator(df['close'], window=200).ema_indicator()
    last = df.iloc[-1]
    indicators = {
        "rsi": round(float(last['rsi']), 2) if pd.notna(last['rsi']) else None,
        "ema50": round(float(last['ema50']), 2) if pd.notna(last['ema50']) else None,
        "ema200": round(float(last['ema200']), 2) if pd.notna(last['ema200']) else None,
        "price": round(float(last['close']), 2),
        "ema_crossover": "BULLISH" if pd.notna(last['ema50']) and pd.notna(last['ema200']) and last['ema50'] > last['ema200'] else "BEARISH",
    }
    if indicators['rsi'] is not None:
        if indicators['rsi'] < 30:
            indicators['rsi_zone'] = 'OVERSOLD'
        elif indicators['rsi'] > 70:
            indicators['rsi_zone'] = 'OVERBOUGHT'
        else:
            indicators['rsi_zone'] = 'NEUTRAL'
    return df, indicators

# ---- AI ANALYSIS ----

async def ai_analyze(price, indicators, ob_data):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            return {"signal": "HOLD", "insight": "No API key configured for AI analysis."}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"crypto-bot-{uuid.uuid4()}",
            system_message="You are an expert cryptocurrency market analyst. Analyze the given market data and provide a concise trading signal (BUY, SELL, or HOLD) with a brief 2-3 sentence explanation. Be direct and data-driven."
        ).with_model("openai", "gpt-5.2")

        prompt = f"""Analyze BTC/USDT market data:
- Current Price: ${price:,.2f}
- RSI(14): {indicators.get('rsi', 'N/A')} ({indicators.get('rsi_zone', 'N/A')})
- EMA50: ${indicators.get('ema50', 'N/A')}
- EMA200: ${indicators.get('ema200', 'N/A')}
- EMA Crossover: {indicators.get('ema_crossover', 'N/A')}
- Order Book: Bid Vol={ob_data.get('bid_volume', 'N/A')}, Ask Vol={ob_data.get('ask_volume', 'N/A')}, Pressure={ob_data.get('signal', 'N/A')}

Respond in this exact JSON format:
{{"signal": "BUY|SELL|HOLD", "insight": "your 2-3 sentence analysis"}}"""

        msg = UserMessage(text=prompt)
        response = await chat.send_message(msg)
        
        try:
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError:
            signal = "HOLD"
            if "BUY" in response.upper():
                signal = "BUY"
            elif "SELL" in response.upper():
                signal = "SELL"
            return {"signal": signal, "insight": response[:300]}
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return {"signal": "HOLD", "insight": f"AI analysis unavailable: {str(e)[:100]}"}

# ---- SIGNAL DECISION ----

def decide_signal(ai_signal, ob_signal, indicators):
    rsi = indicators.get('rsi')
    rsi_signal = 'HOLD'
    if rsi is not None:
        if rsi < 30:
            rsi_signal = 'BUY'
        elif rsi > 70:
            rsi_signal = 'SELL'

    signals = [ai_signal, ob_signal, rsi_signal]
    buy_count = signals.count('BUY')
    sell_count = signals.count('SELL')

    if buy_count >= 2:
        return 'STRONG BUY', rsi_signal
    elif sell_count >= 2:
        return 'STRONG SELL', rsi_signal
    elif buy_count == 1 and sell_count == 0:
        return 'BUY', rsi_signal
    elif sell_count == 1 and buy_count == 0:
        return 'SELL', rsi_signal
    else:
        return 'WAIT', rsi_signal

# ---- BOT LOOP ----

async def bot_loop():
    global bot_state
    logger.info("Bot loop started")
    while bot_state["running"]:
        try:
            # 1. Fetch price
            price_data = await asyncio.to_thread(fetch_price_sync)
            if price_data is None:
                bot_state["errors"].append({"time": datetime.now(timezone.utc).isoformat(), "error": "Failed to fetch price"})
                await asyncio.sleep(30)
                continue
            
            price = price_data["price"]
            bot_state["last_price"] = price

            # 2. Fetch order book
            ob_data = await asyncio.to_thread(fetch_orderbook_sync)
            if ob_data:
                bot_state["last_orderbook"] = ob_data

            # 3. Fetch OHLCV & compute indicators
            df = await asyncio.to_thread(fetch_ohlcv_sync, 200)
            df, indicators = compute_indicators(df)
            if indicators:
                bot_state["last_indicators"] = indicators

            # 4. AI analysis (every 5 iterations to save credits)
            ai_result = {"signal": "HOLD", "insight": ""}
            if bot_state["iterations"] % 5 == 0:
                ai_result = await ai_analyze(price, indicators, ob_data or {})
                bot_state["last_ai_insight"] = ai_result.get("insight", "")
                # Store AI insight
                insight_doc = {
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "insight": ai_result.get("insight", ""),
                    "signal": ai_result.get("signal", "HOLD"),
                    "price": price,
                }
                await db.ai_insights.insert_one(insight_doc)

            # 5. Decide signal
            ob_signal = ob_data["signal"] if ob_data else "HOLD"
            final_signal, rsi_signal = decide_signal(ai_result.get("signal", "HOLD"), ob_signal, indicators)
            bot_state["last_signal"] = final_signal

            # 6. Log signal to DB
            signal_doc = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": price,
                "signal": final_signal,
                "rsi": indicators.get("rsi"),
                "ema50": indicators.get("ema50"),
                "ema200": indicators.get("ema200"),
                "ob_signal": ob_signal,
                "ai_signal": ai_result.get("signal", "HOLD"),
                "rsi_signal": rsi_signal,
                "ai_insight": ai_result.get("insight", ""),
            }
            await db.signals.insert_one(signal_doc)

            bot_state["iterations"] += 1
            logger.info(f"Iteration {bot_state['iterations']}: {final_signal} @ ${price:,.2f}")

            # Wait 60 seconds
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Bot loop error: {e}")
            bot_state["errors"].append({"time": datetime.now(timezone.utc).isoformat(), "error": str(e)[:200]})
            await asyncio.sleep(30)

    logger.info("Bot loop stopped")

# ---- API ROUTES ----

@api_router.get("/")
async def root():
    return {"message": "Crypto AI Trading Bot API"}

# Bot control
@api_router.get("/bot/status")
async def get_bot_status():
    return BotStatus(
        running=bot_state["running"],
        last_price=bot_state["last_price"],
        last_signal=bot_state["last_signal"],
        started_at=bot_state["started_at"],
        iterations=bot_state["iterations"],
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
    )

@api_router.post("/bot/start")
async def start_bot():
    if bot_state["running"]:
        return {"status": "already_running"}
    bot_state["running"] = True
    bot_state["started_at"] = datetime.now(timezone.utc).isoformat()
    bot_state["iterations"] = 0
    bot_state["errors"] = []
    bot_state["task"] = asyncio.create_task(bot_loop())
    return {"status": "started"}

@api_router.post("/bot/stop")
async def stop_bot():
    if not bot_state["running"]:
        return {"status": "already_stopped"}
    bot_state["running"] = False
    if bot_state["task"]:
        bot_state["task"].cancel()
        bot_state["task"] = None
    return {"status": "stopped"}

# Market data (live fetch, no bot needed)
@api_router.get("/market/price")
async def get_price():
    data = await asyncio.to_thread(fetch_price_sync)
    if data is None:
        return {"error": "Failed to fetch price"}
    return data

@api_router.get("/market/ohlcv")
async def get_ohlcv(limit: int = 100):
    df = await asyncio.to_thread(fetch_ohlcv_sync, min(limit, 500))
    if df is None:
        return {"error": "Failed to fetch OHLCV data"}
    records = []
    for _, row in df.iterrows():
        records.append({
            "time": row['time'].isoformat(),
            "open": round(float(row['open']), 2),
            "high": round(float(row['high']), 2),
            "low": round(float(row['low']), 2),
            "close": round(float(row['close']), 2),
            "volume": round(float(row['volume']), 4),
        })
    return {"data": records, "symbol": SYMBOL, "timeframe": TIMEFRAME}

@api_router.get("/market/orderbook")
async def get_orderbook():
    data = await asyncio.to_thread(fetch_orderbook_sync)
    if data is None:
        return {"error": "Failed to fetch order book"}
    return data

@api_router.get("/market/indicators")
async def get_indicators():
    df = await asyncio.to_thread(fetch_ohlcv_sync, 200)
    _, indicators = compute_indicators(df)
    return indicators

# Signals
@api_router.get("/signals/current")
async def get_current_signal():
    return {
        "signal": bot_state["last_signal"],
        "price": bot_state["last_price"],
        "indicators": bot_state["last_indicators"],
        "orderbook": bot_state["last_orderbook"],
        "ai_insight": bot_state["last_ai_insight"],
        "iterations": bot_state["iterations"],
    }

@api_router.get("/signals/history")
async def get_signal_history(limit: int = 50):
    signals = await db.signals.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"signals": signals}

# AI insights
@api_router.post("/ai/analyze")
async def trigger_ai_analysis():
    price_data = await asyncio.to_thread(fetch_price_sync)
    if not price_data:
        return {"error": "Could not fetch price"}
    price = price_data["price"]

    df = await asyncio.to_thread(fetch_ohlcv_sync, 200)
    _, indicators = compute_indicators(df)

    ob_data = await asyncio.to_thread(fetch_orderbook_sync)

    result = await ai_analyze(price, indicators, ob_data or {})

    insight_doc = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "insight": result.get("insight", ""),
        "signal": result.get("signal", "HOLD"),
        "price": price,
    }
    await db.ai_insights.insert_one(insight_doc)

    return {
        "signal": result.get("signal", "HOLD"),
        "insight": result.get("insight", ""),
        "price": price,
        "indicators": indicators,
    }

@api_router.get("/ai/insights")
async def get_ai_insights(limit: int = 20):
    insights = await db.ai_insights.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"insights": insights}

# Errors
@api_router.get("/bot/errors")
async def get_bot_errors():
    return {"errors": bot_state["errors"][-20:]}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    bot_state["running"] = False
    if bot_state["task"]:
        bot_state["task"].cancel()
    client.close()
