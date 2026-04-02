from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
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

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SUPPORTED_PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT']
DEFAULT_SYMBOL = os.environ.get('TRADING_SYMBOL', 'BTC/USDT')
TIMEFRAME = os.environ.get('TRADING_TIMEFRAME', '1m')

from lstm_model import get_lstm
from news_fetcher import fetch_all_news, analyze_news_sentiment

def create_exchange():
    config = {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}
    return ccxt.binanceus(config)

def create_auth_exchange():
    api_key = os.environ.get('BINANCE_API_KEY', '')
    private_key = os.environ.get('BINANCE_PRIVATE_KEY', '').replace('\\n', '\n')
    config = {'enableRateLimit': True, 'options': {'defaultType': 'spot'}}
    if api_key and private_key:
        config['apiKey'] = api_key
        config['secret'] = private_key
        return ccxt.binance(config)
    return None

exchange = create_exchange()

# ---- WEBSOCKET MANAGER ----
class WSManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        logger.info(f"WS client connected. Total: {len(self.connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        logger.info(f"WS client disconnected. Total: {len(self.connections)}")

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

ws_manager = WSManager()

# Bot state per symbol
bot_states = {}

def get_bot_state(symbol):
    if symbol not in bot_states:
        bot_states[symbol] = {
            "running": False, "task": None, "last_price": None,
            "last_signal": "WAIT", "last_indicators": {},
            "last_orderbook": {}, "last_ai_insight": "",
            "last_news_sentiment": {}, "last_lstm": {},
            "last_combined": {}, "started_at": None,
            "iterations": 0, "errors": [], "symbol": symbol,
        }
    return bot_states[symbol]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---- MODELS ----
class TradeRequest(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    side: str
    type: str = "MARKET"
    amount: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class AlertRule(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    type: str
    value: Optional[float] = None
    enabled: bool = True

class RiskSettings(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 5.0
    max_position_size: float = 0.001
    trailing_stop: bool = False
    trailing_stop_pct: float = 1.0

# ---- MARKET DATA ----
def fetch_price_sync(symbol=DEFAULT_SYMBOL):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return {
            "symbol": symbol, "price": ticker['last'],
            "high": ticker.get('high'), "low": ticker.get('low'),
            "volume": ticker.get('baseVolume'), "change": ticker.get('percentage'),
            "bid": ticker.get('bid'), "ask": ticker.get('ask'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Price fetch error {symbol}: {e}")
        return None

def fetch_orderbook_sync(symbol=DEFAULT_SYMBOL):
    try:
        ob = exchange.fetch_order_book(symbol, limit=10)
        bids, asks = ob['bids'][:10], ob['asks'][:10]
        bid_vol = sum(b[1] for b in bids)
        ask_vol = sum(a[1] for a in asks)
        return {
            "symbol": symbol,
            "bids": [{"price": b[0], "amount": b[1]} for b in bids],
            "asks": [{"price": a[0], "amount": a[1]} for a in asks],
            "bid_volume": round(bid_vol, 4), "ask_volume": round(ask_vol, 4),
            "signal": 'BUY' if bid_vol > ask_vol else 'SELL',
            "ratio": round(bid_vol / ask_vol, 2) if ask_vol > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Orderbook fetch error {symbol}: {e}")
        return None

def fetch_ohlcv_sync(symbol=DEFAULT_SYMBOL, limit=200):
    try:
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"OHLCV fetch error {symbol}: {e}")
        return None

def compute_indicators(df):
    if df is None or len(df) < 50:
        return df, {}
    df['rsi'] = ta_lib.momentum.RSIIndicator(df['close']).rsi()
    df['ema50'] = ta_lib.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema200'] = ta_lib.trend.EMAIndicator(df['close'], window=200).ema_indicator()
    df['macd'] = ta_lib.trend.MACD(df['close']).macd()
    df['macd_signal'] = ta_lib.trend.MACD(df['close']).macd_signal()
    df['bb_high'] = ta_lib.volatility.BollingerBands(df['close']).bollinger_hband()
    df['bb_low'] = ta_lib.volatility.BollingerBands(df['close']).bollinger_lband()
    last = df.iloc[-1]
    indicators = {
        "rsi": round(float(last['rsi']), 2) if pd.notna(last['rsi']) else None,
        "ema50": round(float(last['ema50']), 2) if pd.notna(last['ema50']) else None,
        "ema200": round(float(last['ema200']), 2) if pd.notna(last['ema200']) else None,
        "price": round(float(last['close']), 2),
        "ema_crossover": "BULLISH" if pd.notna(last['ema50']) and pd.notna(last['ema200']) and last['ema50'] > last['ema200'] else "BEARISH",
        "macd": round(float(last['macd']), 4) if pd.notna(last['macd']) else None,
        "macd_signal": round(float(last['macd_signal']), 4) if pd.notna(last['macd_signal']) else None,
        "macd_trend": "BULLISH" if pd.notna(last['macd']) and pd.notna(last['macd_signal']) and last['macd'] > last['macd_signal'] else "BEARISH",
        "bb_high": round(float(last['bb_high']), 2) if pd.notna(last['bb_high']) else None,
        "bb_low": round(float(last['bb_low']), 2) if pd.notna(last['bb_low']) else None,
    }
    if indicators['rsi'] is not None:
        indicators['rsi_zone'] = 'OVERSOLD' if indicators['rsi'] < 30 else ('OVERBOUGHT' if indicators['rsi'] > 70 else 'NEUTRAL')
    return df, indicators

def fetch_multi_prices_sync():
    results = []
    for sym in SUPPORTED_PAIRS:
        try:
            ticker = exchange.fetch_ticker(sym)
            results.append({"symbol": sym, "price": ticker['last'], "change": ticker.get('percentage'), "volume": ticker.get('baseVolume'), "high": ticker.get('high'), "low": ticker.get('low')})
        except Exception:
            results.append({"symbol": sym, "price": None, "change": None, "volume": None, "high": None, "low": None})
    return results

# ---- AI ANALYSIS ----
async def ai_analyze_text(prompt_text):
    """Generic AI text analysis. Returns raw response string."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            return '{"signal": "HOLD", "insight": "No API key."}'
        chat = LlmChat(api_key=api_key, session_id=f"crypto-{uuid.uuid4()}", system_message="You are an expert crypto market analyst. Always respond in valid JSON only.").with_model("openai", "gpt-5.2")
        return await chat.send_message(UserMessage(text=prompt_text))
    except Exception as e:
        logger.error(f"AI error: {e}")
        return json.dumps({"signal": "HOLD", "insight": str(e)[:100]})

async def ai_market_analysis(price, indicators, ob_data, symbol=DEFAULT_SYMBOL):
    prompt = f"""Analyze {symbol} market data:
- Price: ${price:,.2f}
- RSI(14): {indicators.get('rsi', 'N/A')} ({indicators.get('rsi_zone', 'N/A')})
- EMA50: ${indicators.get('ema50', 'N/A')}, EMA200: ${indicators.get('ema200', 'N/A')}
- EMA Cross: {indicators.get('ema_crossover', 'N/A')}
- MACD: {indicators.get('macd', 'N/A')}, Signal: {indicators.get('macd_signal', 'N/A')}, Trend: {indicators.get('macd_trend', 'N/A')}
- Bollinger: High=${indicators.get('bb_high', 'N/A')}, Low=${indicators.get('bb_low', 'N/A')}
- Order Book: Bid={ob_data.get('bid_volume', 'N/A')}, Ask={ob_data.get('ask_volume', 'N/A')}, Pressure={ob_data.get('signal', 'N/A')}

Respond in exact JSON: {{"signal": "BUY|SELL|HOLD", "insight": "2-3 sentence analysis"}}"""
    resp = await ai_analyze_text(prompt)
    try:
        cleaned = resp.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(cleaned)
    except Exception:
        sig = "HOLD"
        if "BUY" in resp.upper():
            sig = "BUY"
        elif "SELL" in resp.upper():
            sig = "SELL"
        return {"signal": sig, "insight": resp[:300]}

async def ai_news_sentiment(news_articles, symbol):
    if not news_articles:
        return {"sentiment": "NEUTRAL", "score": 0, "summary": "No news.", "signal": "HOLD"}
    headlines = "\n".join([f"- [{a['source']}] {a['title']}" for a in news_articles[:10]])
    prompt = f"""Analyze these {symbol} crypto news headlines for market sentiment:

{headlines}

Respond in exact JSON: {{"sentiment": "BULLISH|BEARISH|NEUTRAL", "score": -100 to 100, "summary": "1-2 sentence summary", "signal": "BUY|SELL|HOLD"}}"""
    resp = await ai_analyze_text(prompt)
    try:
        cleaned = resp.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(cleaned)
    except Exception:
        return {"sentiment": "NEUTRAL", "score": 0, "summary": resp[:200], "signal": "HOLD"}

# ---- COMBINED SIGNAL ENGINE ----
def compute_combined_signal(ta_signal, ob_signal, rsi_signal, lstm_result, news_sentiment, ai_result):
    """
    Weighted combination of all signal sources:
    - Technical (RSI, EMA, MACD): 25%
    - Order Book: 15%
    - LSTM Prediction: 20%
    - News Sentiment: 20%
    - AI Analysis: 20%
    """
    def signal_to_score(sig):
        s = (sig or "").upper()
        if "STRONG BUY" in s or s == "BUY":
            return 1
        elif "STRONG SELL" in s or s == "SELL":
            return -1
        return 0

    scores = {
        "technical": signal_to_score(ta_signal) * 0.25,
        "orderbook": signal_to_score(ob_signal) * 0.15,
        "lstm": signal_to_score(lstm_result.get("signal", "HOLD")) * 0.20,
        "news": signal_to_score(news_sentiment.get("signal", "HOLD")) * 0.20,
        "ai": signal_to_score(ai_result.get("signal", "HOLD")) * 0.20,
    }

    total = sum(scores.values())
    confidence = abs(total) * 100

    if total >= 0.45:
        final = "STRONG BUY"
    elif total >= 0.2:
        final = "BUY"
    elif total <= -0.45:
        final = "STRONG SELL"
    elif total <= -0.2:
        final = "SELL"
    else:
        final = "WAIT"

    return {
        "signal": final,
        "score": round(total, 3),
        "confidence": round(min(confidence, 100), 1),
        "breakdown": scores,
        "components": {
            "technical": ta_signal,
            "orderbook": ob_signal,
            "lstm": lstm_result.get("signal", "HOLD"),
            "news": news_sentiment.get("signal", "HOLD"),
            "ai": ai_result.get("signal", "HOLD"),
        }
    }

def compute_ta_signal(indicators):
    """Pure TA signal from indicators."""
    score = 0
    rsi = indicators.get('rsi')
    if rsi is not None:
        if rsi < 30:
            score += 1
        elif rsi > 70:
            score -= 1
    if indicators.get('ema_crossover') == 'BULLISH':
        score += 1
    else:
        score -= 1
    if indicators.get('macd_trend') == 'BULLISH':
        score += 1
    else:
        score -= 1
    if score >= 2:
        return "BUY"
    elif score <= -2:
        return "SELL"
    return "HOLD"

# ---- ALERT ENGINE ----
async def check_alerts(symbol, price, signal):
    alerts = await db.alerts.find({"symbol": symbol, "enabled": True}, {"_id": 0}).to_list(100)
    for alert in alerts:
        fire = False
        if alert["type"] == "price_above" and price >= alert.get("value", 0):
            fire = True
        elif alert["type"] == "price_below" and price <= alert.get("value", 0):
            fire = True
        elif alert["type"] == "signal_strong_buy" and "STRONG BUY" in signal:
            fire = True
        elif alert["type"] == "signal_strong_sell" and "STRONG SELL" in signal:
            fire = True
        if fire:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol, "type": alert["type"],
                "message": f"Alert: {alert['type']} for {symbol} @ ${price:,.2f} | Signal: {signal}",
                "price": price, "signal": signal, "read": False,
            })
            if alert["type"] in ["price_above", "price_below"]:
                await db.alerts.update_one({"id": alert["id"]}, {"$set": {"enabled": False}})

# ---- BOT LOOP ----
async def bot_loop(symbol):
    state = get_bot_state(symbol)
    logger.info(f"Bot started: {symbol}")

    # Train LSTM on startup
    lstm = get_lstm(symbol)
    df_train = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 500)
    if df_train is not None and len(df_train) > 60:
        await asyncio.to_thread(lstm.train, df_train)
        logger.info(f"LSTM trained for {symbol}")

    while state["running"]:
        try:
            # 1. Price
            price_data = await asyncio.to_thread(fetch_price_sync, symbol)
            if not price_data:
                await asyncio.sleep(30)
                continue
            price = price_data["price"]
            state["last_price"] = price

            # 2. Order book
            ob_data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
            if ob_data:
                state["last_orderbook"] = ob_data

            # 3. OHLCV + indicators
            df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
            df, indicators = compute_indicators(df)
            if indicators:
                state["last_indicators"] = indicators

            # 4. LSTM prediction
            lstm_result = {"signal": "HOLD", "confidence": 0, "predicted_direction": "NEUTRAL"}
            if lstm.trained and df is not None:
                lstm_result = await asyncio.to_thread(lstm.predict, df)
            state["last_lstm"] = lstm_result

            # 5. News + sentiment (every 3 iterations)
            news_sentiment = state.get("last_news_sentiment", {"signal": "HOLD"})
            if state["iterations"] % 3 == 0:
                news = await fetch_all_news(symbol)
                if news:
                    news_sentiment = await ai_news_sentiment(news, symbol)
                    state["last_news_sentiment"] = news_sentiment
                    # Store news
                    await db.news.insert_one({
                        "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
                        "symbol": symbol, "articles": news[:5],
                        "sentiment": news_sentiment,
                    })

            # 6. AI market analysis (every 5 iterations)
            ai_result = {"signal": "HOLD", "insight": ""}
            if state["iterations"] % 5 == 0:
                ai_result = await ai_market_analysis(price, indicators, ob_data or {}, symbol)
                state["last_ai_insight"] = ai_result.get("insight", "")
                await db.ai_insights.insert_one({
                    "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
                    "insight": ai_result.get("insight", ""), "signal": ai_result.get("signal", "HOLD"),
                    "price": price, "symbol": symbol,
                })

            # 7. Combined signal
            ta_signal = compute_ta_signal(indicators)
            ob_signal = ob_data["signal"] if ob_data else "HOLD"
            combined = compute_combined_signal(ta_signal, ob_signal, indicators.get("rsi_zone", "NEUTRAL"), lstm_result, news_sentiment, ai_result)
            state["last_signal"] = combined["signal"]
            state["last_combined"] = combined

            # 8. Store signal
            await db.signals.insert_one({
                "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": price, "signal": combined["signal"], "symbol": symbol,
                "rsi": indicators.get("rsi"), "ema50": indicators.get("ema50"), "ema200": indicators.get("ema200"),
                "ob_signal": ob_signal, "ai_signal": ai_result.get("signal", "HOLD"),
                "rsi_signal": ta_signal, "ai_insight": ai_result.get("insight", ""),
                "lstm_signal": lstm_result.get("signal", "HOLD"),
                "lstm_confidence": lstm_result.get("confidence", 0),
                "news_signal": news_sentiment.get("signal", "HOLD"),
                "news_score": news_sentiment.get("score", 0),
                "combined_score": combined["score"],
                "combined_confidence": combined["confidence"],
            })

            # 9. Alerts
            await check_alerts(symbol, price, combined["signal"])

            # 10. Broadcast via WebSocket
            await ws_manager.broadcast({
                "type": "update", "symbol": symbol,
                "price": price_data, "signal": combined,
                "indicators": indicators, "lstm": lstm_result,
                "news_sentiment": news_sentiment,
                "orderbook": {"signal": ob_signal, "ratio": ob_data.get("ratio") if ob_data else 0},
                "iteration": state["iterations"],
            })

            state["iterations"] += 1
            logger.info(f"[{symbol}] #{state['iterations']}: {combined['signal']} ({combined['confidence']}%) @ ${price:,.2f}")
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Bot error [{symbol}]: {e}")
            state["errors"].append({"time": datetime.now(timezone.utc).isoformat(), "error": str(e)[:200]})
            await asyncio.sleep(30)

    logger.info(f"Bot stopped: {symbol}")

# ---- TRADE EXECUTION ----
async def execute_trade(symbol, side, order_type, amount, price, stop_loss=None, take_profit=None):
    trade_doc = {
        "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol, "side": side, "type": order_type, "amount": amount,
        "price": price, "stop_loss": stop_loss, "take_profit": take_profit,
        "status": "SIMULATED", "pnl": None, "closed_at": None, "close_price": None,
    }
    auth_ex = create_auth_exchange()
    if auth_ex:
        try:
            if order_type == "MARKET":
                order = auth_ex.create_market_buy_order(symbol, amount) if side == "BUY" else auth_ex.create_market_sell_order(symbol, amount)
                trade_doc["status"] = "FILLED"
                trade_doc["exchange_order_id"] = order.get("id")
                trade_doc["price"] = order.get("average", price)
            elif order_type == "LIMIT" and price:
                order = auth_ex.create_limit_buy_order(symbol, amount, price) if side == "BUY" else auth_ex.create_limit_sell_order(symbol, amount, price)
                trade_doc["status"] = "OPEN"
                trade_doc["exchange_order_id"] = order.get("id")
        except Exception as e:
            trade_doc["status"] = "SIMULATED"
            trade_doc["error"] = str(e)[:200]
    await db.trades.insert_one(trade_doc)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol, "type": f"trade_{side.lower()}",
        "message": f"{'SIM ' if trade_doc['status']=='SIMULATED' else ''}{side} {amount} {symbol.split('/')[0]} @ ${price:,.2f}" + (f" | SL:${stop_loss:,.2f}" if stop_loss else "") + (f" | TP:${take_profit:,.2f}" if take_profit else ""),
        "price": price, "signal": side, "read": False,
    })
    return trade_doc

# ---- API ROUTES ----

@api_router.get("/")
async def root():
    return {"message": "Crypto AI Trading Bot API v2"}

@api_router.get("/pairs")
async def get_pairs():
    return {"pairs": SUPPORTED_PAIRS, "default": DEFAULT_SYMBOL}

@api_router.get("/market/prices")
async def get_all_prices():
    return {"prices": await asyncio.to_thread(fetch_multi_prices_sync)}

@api_router.get("/bot/status")
async def get_bot_status(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    return {"running": s["running"], "last_price": s["last_price"], "last_signal": s["last_signal"], "started_at": s["started_at"], "iterations": s["iterations"], "symbol": symbol, "timeframe": TIMEFRAME}

@api_router.post("/bot/start")
async def start_bot(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    if s["running"]:
        return {"status": "already_running"}
    s["running"] = True
    s["started_at"] = datetime.now(timezone.utc).isoformat()
    s["iterations"] = 0
    s["errors"] = []
    s["task"] = asyncio.create_task(bot_loop(symbol))
    return {"status": "started", "symbol": symbol}

@api_router.post("/bot/stop")
async def stop_bot(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    if not s["running"]:
        return {"status": "already_stopped"}
    s["running"] = False
    if s["task"]:
        s["task"].cancel()
        s["task"] = None
    return {"status": "stopped", "symbol": symbol}

@api_router.get("/market/price")
async def get_price(symbol: str = DEFAULT_SYMBOL):
    data = await asyncio.to_thread(fetch_price_sync, symbol)
    return data or {"error": f"Failed for {symbol}"}

@api_router.get("/market/ohlcv")
async def get_ohlcv(symbol: str = DEFAULT_SYMBOL, limit: int = 100):
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, min(limit, 500))
    if df is None:
        return {"error": f"Failed for {symbol}"}
    records = [{"time": r['time'].isoformat(), "open": round(float(r['open']), 2), "high": round(float(r['high']), 2), "low": round(float(r['low']), 2), "close": round(float(r['close']), 2), "volume": round(float(r['volume']), 4)} for _, r in df.iterrows()]
    return {"data": records, "symbol": symbol, "timeframe": TIMEFRAME}

@api_router.get("/market/orderbook")
async def get_orderbook(symbol: str = DEFAULT_SYMBOL):
    data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
    return data or {"error": f"Failed for {symbol}"}

@api_router.get("/market/indicators")
async def get_indicators(symbol: str = DEFAULT_SYMBOL):
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
    _, ind = compute_indicators(df)
    return ind

# Signals
@api_router.get("/signals/current")
async def get_current_signal(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    return {
        "signal": s["last_signal"], "price": s["last_price"],
        "indicators": s["last_indicators"], "orderbook": s["last_orderbook"],
        "ai_insight": s["last_ai_insight"], "iterations": s["iterations"],
        "symbol": symbol, "lstm": s.get("last_lstm", {}),
        "news_sentiment": s.get("last_news_sentiment", {}),
        "combined": s.get("last_combined", {}),
    }

@api_router.get("/signals/history")
async def get_signal_history(symbol: str = DEFAULT_SYMBOL, limit: int = 50):
    return {"signals": await db.signals.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)}

# AI
@api_router.post("/ai/analyze")
async def trigger_ai_analysis(symbol: str = DEFAULT_SYMBOL):
    price_data = await asyncio.to_thread(fetch_price_sync, symbol)
    if not price_data:
        return {"error": "Could not fetch price"}
    price = price_data["price"]
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
    _, indicators = compute_indicators(df)
    ob_data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
    result = await ai_market_analysis(price, indicators, ob_data or {}, symbol)
    await db.ai_insights.insert_one({"id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "insight": result.get("insight", ""), "signal": result.get("signal", "HOLD"), "price": price, "symbol": symbol})
    return {"signal": result.get("signal", "HOLD"), "insight": result.get("insight", ""), "price": price, "indicators": indicators, "symbol": symbol}

@api_router.get("/ai/insights")
async def get_ai_insights(symbol: str = DEFAULT_SYMBOL, limit: int = 20):
    return {"insights": await db.ai_insights.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)}

# LSTM
@api_router.get("/lstm/status")
async def get_lstm_status(symbol: str = DEFAULT_SYMBOL):
    lstm = get_lstm(symbol)
    s = get_bot_state(symbol)
    return {"trained": lstm.trained, "prediction": s.get("last_lstm", {}), "symbol": symbol}

@api_router.post("/lstm/train")
async def train_lstm(symbol: str = DEFAULT_SYMBOL):
    lstm = get_lstm(symbol)
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 500)
    if df is None:
        return {"error": "Failed to fetch data"}
    success = await asyncio.to_thread(lstm.train, df)
    return {"status": "trained" if success else "failed", "symbol": symbol}

@api_router.get("/lstm/predict")
async def predict_lstm(symbol: str = DEFAULT_SYMBOL):
    lstm = get_lstm(symbol)
    if not lstm.trained:
        return {"error": "LSTM not trained yet", "signal": "HOLD"}
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
    result = await asyncio.to_thread(lstm.predict, df)
    return result

# News
@api_router.get("/news")
async def get_news(symbol: str = DEFAULT_SYMBOL):
    articles = await fetch_all_news(symbol)
    return {"articles": articles, "symbol": symbol, "count": len(articles)}

@api_router.get("/news/sentiment")
async def get_news_sentiment(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    return s.get("last_news_sentiment", {"sentiment": "NEUTRAL", "score": 0, "summary": "Not analyzed yet.", "signal": "HOLD"})

@api_router.post("/news/analyze")
async def analyze_news_now(symbol: str = DEFAULT_SYMBOL):
    articles = await fetch_all_news(symbol)
    if not articles:
        return {"error": "No news found", "articles": []}
    sentiment = await ai_news_sentiment(articles, symbol)
    await db.news.insert_one({"id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "symbol": symbol, "articles": articles[:5], "sentiment": sentiment})
    return {"articles": articles[:10], "sentiment": sentiment, "symbol": symbol}

@api_router.get("/news/history")
async def get_news_history(symbol: str = DEFAULT_SYMBOL, limit: int = 10):
    return {"news": await db.news.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)}

# Combined signal
@api_router.get("/signal/combined")
async def get_combined_signal(symbol: str = DEFAULT_SYMBOL):
    s = get_bot_state(symbol)
    return s.get("last_combined", {"signal": "WAIT", "score": 0, "confidence": 0, "breakdown": {}, "components": {}})

# Trades
@api_router.post("/trades/execute")
async def execute_trade_endpoint(req: TradeRequest):
    price_data = await asyncio.to_thread(fetch_price_sync, req.symbol)
    price = price_data["price"] if price_data else req.price or 0
    trade = await execute_trade(req.symbol, req.side, req.type, req.amount, price, req.stop_loss, req.take_profit)
    trade.pop("_id", None)
    return trade

@api_router.get("/trades/history")
async def get_trade_history(symbol: str = DEFAULT_SYMBOL, limit: int = 50):
    return {"trades": await db.trades.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)}

@api_router.get("/trades/open")
async def get_open_trades(symbol: str = DEFAULT_SYMBOL):
    return {"trades": await db.trades.find({"symbol": symbol, "status": {"$in": ["OPEN", "SIMULATED"]}}, {"_id": 0}).sort("timestamp", -1).to_list(50)}

@api_router.post("/trades/close/{trade_id}")
async def close_trade(trade_id: str):
    trade = await db.trades.find_one({"id": trade_id}, {"_id": 0})
    if not trade:
        return {"error": "Trade not found"}
    price_data = await asyncio.to_thread(fetch_price_sync, trade["symbol"])
    close_price = price_data["price"] if price_data else trade["price"]
    pnl = (close_price - trade["price"]) * trade["amount"] if trade["side"] == "BUY" else (trade["price"] - close_price) * trade["amount"]
    await db.trades.update_one({"id": trade_id}, {"$set": {"status": "CLOSED", "closed_at": datetime.now(timezone.utc).isoformat(), "close_price": close_price, "pnl": round(pnl, 2)}})
    return {"status": "closed", "pnl": round(pnl, 2), "close_price": close_price}

# Risk
@api_router.get("/risk/settings")
async def get_risk_settings(symbol: str = DEFAULT_SYMBOL):
    s = await db.risk_settings.find_one({"symbol": symbol}, {"_id": 0})
    return s or {"symbol": symbol, "stop_loss_pct": 2.0, "take_profit_pct": 5.0, "max_position_size": 0.001, "trailing_stop": False, "trailing_stop_pct": 1.0, "auto_trade": False}

@api_router.post("/risk/settings")
async def save_risk_settings(settings: RiskSettings):
    doc = settings.model_dump()
    doc["auto_trade"] = False
    await db.risk_settings.update_one({"symbol": settings.symbol}, {"$set": doc}, upsert=True)
    return {"status": "saved"}

# Alerts
@api_router.post("/alerts/create")
async def create_alert(rule: AlertRule):
    doc = rule.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.alerts.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/alerts")
async def get_alerts(symbol: str = DEFAULT_SYMBOL):
    return {"alerts": await db.alerts.find({"symbol": symbol}, {"_id": 0}).to_list(100)}

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    await db.alerts.delete_one({"id": alert_id})
    return {"status": "deleted"}

# Notifications
@api_router.get("/notifications")
async def get_notifications(limit: int = 30):
    return {"notifications": await db.notifications.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)}

@api_router.get("/notifications/unread")
async def get_unread_count():
    return {"unread": await db.notifications.count_documents({"read": False})}

@api_router.post("/notifications/read")
async def mark_all_read():
    await db.notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"status": "done"}

@api_router.get("/bot/errors")
async def get_bot_errors(symbol: str = DEFAULT_SYMBOL):
    return {"errors": get_bot_state(symbol)["errors"][-20:]}

# ---- WEBSOCKET ----
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send commands like {"action": "subscribe", "symbol": "BTC/USDT"}
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

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
    for s in bot_states.values():
        s["running"] = False
        if s["task"]:
            s["task"].cancel()
    client.close()
