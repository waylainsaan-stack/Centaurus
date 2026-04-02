from fastapi import FastAPI, APIRouter
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

# Supported trading pairs
SUPPORTED_PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT']
DEFAULT_SYMBOL = os.environ.get('TRADING_SYMBOL', 'BTC/USDT')
TIMEFRAME = os.environ.get('TRADING_TIMEFRAME', '1m')

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

# Bot state per symbol
bot_states = {}

def get_bot_state(symbol):
    if symbol not in bot_states:
        bot_states[symbol] = {
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
            "symbol": symbol,
        }
    return bot_states[symbol]

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---- MODELS ----

class TradeRequest(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    side: str  # BUY or SELL
    type: str = "MARKET"  # MARKET or LIMIT
    amount: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class AlertRule(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    type: str  # price_above, price_below, signal_strong_buy, signal_strong_sell
    value: Optional[float] = None
    enabled: bool = True

class RiskSettings(BaseModel):
    symbol: str = DEFAULT_SYMBOL
    stop_loss_pct: float = 2.0
    take_profit_pct: float = 5.0
    max_position_size: float = 0.1
    trailing_stop: bool = False
    trailing_stop_pct: float = 1.0

# ---- MARKET DATA (multi-pair) ----

def fetch_price_sync(symbol=DEFAULT_SYMBOL):
    try:
        ticker = exchange.fetch_ticker(symbol)
        return {
            "symbol": symbol,
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
        logger.error(f"Error fetching price for {symbol}: {e}")
        return None

def fetch_orderbook_sync(symbol=DEFAULT_SYMBOL):
    try:
        ob = exchange.fetch_order_book(symbol, limit=10)
        bids = ob['bids'][:10]
        asks = ob['asks'][:10]
        bid_vol = sum([b[1] for b in bids])
        ask_vol = sum([a[1] for a in asks])
        signal = 'BUY' if bid_vol > ask_vol else 'SELL'
        return {
            "symbol": symbol,
            "bids": [{"price": b[0], "amount": b[1]} for b in bids],
            "asks": [{"price": a[0], "amount": a[1]} for a in asks],
            "bid_volume": round(bid_vol, 4),
            "ask_volume": round(ask_vol, 4),
            "signal": signal,
            "ratio": round(bid_vol / ask_vol, 2) if ask_vol > 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error fetching orderbook for {symbol}: {e}")
        return None

def fetch_ohlcv_sync(symbol=DEFAULT_SYMBOL, limit=200):
    try:
        bars = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=limit)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV for {symbol}: {e}")
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

def fetch_multi_prices_sync():
    results = []
    for sym in SUPPORTED_PAIRS:
        try:
            ticker = exchange.fetch_ticker(sym)
            results.append({
                "symbol": sym,
                "price": ticker['last'],
                "change": ticker.get('percentage'),
                "volume": ticker.get('baseVolume'),
                "high": ticker.get('high'),
                "low": ticker.get('low'),
            })
        except Exception as e:
            logger.error(f"Error fetching {sym}: {e}")
            results.append({"symbol": sym, "price": None, "change": None, "volume": None, "high": None, "low": None})
    return results

# ---- AI ANALYSIS ----

async def ai_analyze(price, indicators, ob_data, symbol=DEFAULT_SYMBOL):
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        if not api_key:
            return {"signal": "HOLD", "insight": "No API key configured."}

        chat = LlmChat(
            api_key=api_key,
            session_id=f"crypto-bot-{uuid.uuid4()}",
            system_message="You are an expert cryptocurrency market analyst. Analyze the given market data and provide a concise trading signal (BUY, SELL, or HOLD) with a brief 2-3 sentence explanation. Be direct and data-driven."
        ).with_model("openai", "gpt-5.2")

        prompt = f"""Analyze {symbol} market data:
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
            return json.loads(cleaned)
        except json.JSONDecodeError:
            signal = "HOLD"
            if "BUY" in response.upper():
                signal = "BUY"
            elif "SELL" in response.upper():
                signal = "SELL"
            return {"signal": signal, "insight": response[:300]}
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return {"signal": "HOLD", "insight": f"AI unavailable: {str(e)[:100]}"}

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
    return 'WAIT', rsi_signal

# ---- ALERT ENGINE ----

async def check_alerts(symbol, price, signal):
    alerts = await db.alerts.find({"symbol": symbol, "enabled": True}, {"_id": 0}).to_list(100)
    triggered = []
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
            notif = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "type": alert["type"],
                "message": f"Alert triggered: {alert['type']} for {symbol} @ ${price:,.2f} | Signal: {signal}",
                "price": price,
                "signal": signal,
                "read": False,
            }
            await db.notifications.insert_one(notif)
            triggered.append(notif)
            # Disable one-shot price alerts after triggering
            if alert["type"] in ["price_above", "price_below"]:
                await db.alerts.update_one({"id": alert["id"]}, {"$set": {"enabled": False}})
    return triggered

# ---- BOT LOOP (per symbol) ----

async def bot_loop(symbol):
    state = get_bot_state(symbol)
    logger.info(f"Bot loop started for {symbol}")
    while state["running"]:
        try:
            price_data = await asyncio.to_thread(fetch_price_sync, symbol)
            if price_data is None:
                state["errors"].append({"time": datetime.now(timezone.utc).isoformat(), "error": "Failed to fetch price"})
                await asyncio.sleep(30)
                continue
            price = price_data["price"]
            state["last_price"] = price

            ob_data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
            if ob_data:
                state["last_orderbook"] = ob_data

            df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
            df, indicators = compute_indicators(df)
            if indicators:
                state["last_indicators"] = indicators

            ai_result = {"signal": "HOLD", "insight": ""}
            if state["iterations"] % 5 == 0:
                ai_result = await ai_analyze(price, indicators, ob_data or {}, symbol)
                state["last_ai_insight"] = ai_result.get("insight", "")
                await db.ai_insights.insert_one({
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "insight": ai_result.get("insight", ""),
                    "signal": ai_result.get("signal", "HOLD"),
                    "price": price,
                    "symbol": symbol,
                })

            ob_signal = ob_data["signal"] if ob_data else "HOLD"
            final_signal, rsi_signal = decide_signal(ai_result.get("signal", "HOLD"), ob_signal, indicators)
            state["last_signal"] = final_signal

            signal_doc = {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": price,
                "signal": final_signal,
                "symbol": symbol,
                "rsi": indicators.get("rsi"),
                "ema50": indicators.get("ema50"),
                "ema200": indicators.get("ema200"),
                "ob_signal": ob_signal,
                "ai_signal": ai_result.get("signal", "HOLD"),
                "rsi_signal": rsi_signal,
                "ai_insight": ai_result.get("insight", ""),
            }
            await db.signals.insert_one(signal_doc)

            # Check alerts
            await check_alerts(symbol, price, final_signal)

            # Auto-trade if enabled
            await check_auto_trade(symbol, price, final_signal, indicators)

            state["iterations"] += 1
            logger.info(f"[{symbol}] Iteration {state['iterations']}: {final_signal} @ ${price:,.2f}")
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(f"Bot loop error [{symbol}]: {e}")
            state["errors"].append({"time": datetime.now(timezone.utc).isoformat(), "error": str(e)[:200]})
            await asyncio.sleep(30)
    logger.info(f"Bot loop stopped for {symbol}")

# ---- TRADE EXECUTION ----

async def check_auto_trade(symbol, price, signal, indicators):
    settings = await db.risk_settings.find_one({"symbol": symbol}, {"_id": 0})
    if not settings or not settings.get("auto_trade"):
        return
    if signal in ["STRONG BUY", "STRONG SELL"]:
        side = "BUY" if "BUY" in signal else "SELL"
        amount = settings.get("max_position_size", 0.001)
        sl_pct = settings.get("stop_loss_pct", 2.0)
        tp_pct = settings.get("take_profit_pct", 5.0)
        stop_loss = price * (1 - sl_pct / 100) if side == "BUY" else price * (1 + sl_pct / 100)
        take_profit = price * (1 + tp_pct / 100) if side == "BUY" else price * (1 - tp_pct / 100)
        await execute_trade(symbol, side, "MARKET", amount, price, stop_loss, take_profit)

async def execute_trade(symbol, side, order_type, amount, price, stop_loss=None, take_profit=None):
    trade_doc = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "amount": amount,
        "price": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": "SIMULATED",
        "pnl": None,
        "closed_at": None,
        "close_price": None,
    }

    # Try real execution via authenticated exchange
    auth_ex = create_auth_exchange()
    if auth_ex:
        try:
            if order_type == "MARKET":
                if side == "BUY":
                    order = auth_ex.create_market_buy_order(symbol, amount)
                else:
                    order = auth_ex.create_market_sell_order(symbol, amount)
                trade_doc["status"] = "FILLED"
                trade_doc["exchange_order_id"] = order.get("id")
                trade_doc["price"] = order.get("average", price)
            elif order_type == "LIMIT" and price:
                if side == "BUY":
                    order = auth_ex.create_limit_buy_order(symbol, amount, price)
                else:
                    order = auth_ex.create_limit_sell_order(symbol, amount, price)
                trade_doc["status"] = "OPEN"
                trade_doc["exchange_order_id"] = order.get("id")
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            trade_doc["status"] = "SIMULATED"
            trade_doc["error"] = str(e)[:200]

    await db.trades.insert_one(trade_doc)

    # Create notification for trade
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "type": f"trade_{side.lower()}",
        "message": f"{'SIMULATED ' if trade_doc['status'] == 'SIMULATED' else ''}{side} {amount} {symbol.split('/')[0]} @ ${price:,.2f}" + (f" | SL: ${stop_loss:,.2f}" if stop_loss else "") + (f" | TP: ${take_profit:,.2f}" if take_profit else ""),
        "price": price,
        "signal": side,
        "read": False,
    })
    return trade_doc

# ---- API ROUTES ----

@api_router.get("/")
async def root():
    return {"message": "Crypto AI Trading Bot API"}

# Supported pairs
@api_router.get("/pairs")
async def get_pairs():
    return {"pairs": SUPPORTED_PAIRS, "default": DEFAULT_SYMBOL}

# Multi-pair prices
@api_router.get("/market/prices")
async def get_all_prices():
    data = await asyncio.to_thread(fetch_multi_prices_sync)
    return {"prices": data}

# Bot control
@api_router.get("/bot/status")
async def get_bot_status(symbol: str = DEFAULT_SYMBOL):
    state = get_bot_state(symbol)
    return {
        "running": state["running"],
        "last_price": state["last_price"],
        "last_signal": state["last_signal"],
        "started_at": state["started_at"],
        "iterations": state["iterations"],
        "symbol": symbol,
        "timeframe": TIMEFRAME,
    }

@api_router.post("/bot/start")
async def start_bot(symbol: str = DEFAULT_SYMBOL):
    state = get_bot_state(symbol)
    if state["running"]:
        return {"status": "already_running"}
    state["running"] = True
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["iterations"] = 0
    state["errors"] = []
    state["task"] = asyncio.create_task(bot_loop(symbol))
    return {"status": "started", "symbol": symbol}

@api_router.post("/bot/stop")
async def stop_bot(symbol: str = DEFAULT_SYMBOL):
    state = get_bot_state(symbol)
    if not state["running"]:
        return {"status": "already_stopped"}
    state["running"] = False
    if state["task"]:
        state["task"].cancel()
        state["task"] = None
    return {"status": "stopped", "symbol": symbol}

# Market data
@api_router.get("/market/price")
async def get_price(symbol: str = DEFAULT_SYMBOL):
    data = await asyncio.to_thread(fetch_price_sync, symbol)
    if data is None:
        return {"error": f"Failed to fetch price for {symbol}"}
    return data

@api_router.get("/market/ohlcv")
async def get_ohlcv(symbol: str = DEFAULT_SYMBOL, limit: int = 100):
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, min(limit, 500))
    if df is None:
        return {"error": f"Failed to fetch OHLCV for {symbol}"}
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
    return {"data": records, "symbol": symbol, "timeframe": TIMEFRAME}

@api_router.get("/market/orderbook")
async def get_orderbook(symbol: str = DEFAULT_SYMBOL):
    data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
    if data is None:
        return {"error": f"Failed to fetch order book for {symbol}"}
    return data

@api_router.get("/market/indicators")
async def get_indicators(symbol: str = DEFAULT_SYMBOL):
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
    _, indicators = compute_indicators(df)
    return indicators

# Signals
@api_router.get("/signals/current")
async def get_current_signal(symbol: str = DEFAULT_SYMBOL):
    state = get_bot_state(symbol)
    return {
        "signal": state["last_signal"],
        "price": state["last_price"],
        "indicators": state["last_indicators"],
        "orderbook": state["last_orderbook"],
        "ai_insight": state["last_ai_insight"],
        "iterations": state["iterations"],
        "symbol": symbol,
    }

@api_router.get("/signals/history")
async def get_signal_history(symbol: str = DEFAULT_SYMBOL, limit: int = 50):
    signals = await db.signals.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"signals": signals}

# AI insights
@api_router.post("/ai/analyze")
async def trigger_ai_analysis(symbol: str = DEFAULT_SYMBOL):
    price_data = await asyncio.to_thread(fetch_price_sync, symbol)
    if not price_data:
        return {"error": "Could not fetch price"}
    price = price_data["price"]
    df = await asyncio.to_thread(fetch_ohlcv_sync, symbol, 200)
    _, indicators = compute_indicators(df)
    ob_data = await asyncio.to_thread(fetch_orderbook_sync, symbol)
    result = await ai_analyze(price, indicators, ob_data or {}, symbol)
    await db.ai_insights.insert_one({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "insight": result.get("insight", ""),
        "signal": result.get("signal", "HOLD"),
        "price": price,
        "symbol": symbol,
    })
    return {"signal": result.get("signal", "HOLD"), "insight": result.get("insight", ""), "price": price, "indicators": indicators, "symbol": symbol}

@api_router.get("/ai/insights")
async def get_ai_insights(symbol: str = DEFAULT_SYMBOL, limit: int = 20):
    insights = await db.ai_insights.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"insights": insights}

# ---- TRADE ROUTES ----

@api_router.post("/trades/execute")
async def execute_trade_endpoint(req: TradeRequest):
    price_data = await asyncio.to_thread(fetch_price_sync, req.symbol)
    price = price_data["price"] if price_data else req.price or 0
    trade = await execute_trade(req.symbol, req.side, req.type, req.amount, price, req.stop_loss, req.take_profit)
    # Remove _id before returning
    trade.pop("_id", None)
    return trade

@api_router.get("/trades/history")
async def get_trade_history(symbol: str = DEFAULT_SYMBOL, limit: int = 50):
    trades = await db.trades.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"trades": trades}

@api_router.get("/trades/open")
async def get_open_trades(symbol: str = DEFAULT_SYMBOL):
    trades = await db.trades.find({"symbol": symbol, "status": {"$in": ["OPEN", "SIMULATED"]}}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return {"trades": trades}

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

# ---- RISK SETTINGS ----

@api_router.get("/risk/settings")
async def get_risk_settings(symbol: str = DEFAULT_SYMBOL):
    settings = await db.risk_settings.find_one({"symbol": symbol}, {"_id": 0})
    if not settings:
        settings = {"symbol": symbol, "stop_loss_pct": 2.0, "take_profit_pct": 5.0, "max_position_size": 0.001, "trailing_stop": False, "trailing_stop_pct": 1.0, "auto_trade": False}
    return settings

@api_router.post("/risk/settings")
async def save_risk_settings(settings: RiskSettings):
    doc = settings.model_dump()
    doc["auto_trade"] = False
    await db.risk_settings.update_one({"symbol": settings.symbol}, {"$set": doc}, upsert=True)
    return {"status": "saved"}

@api_router.post("/risk/auto-trade")
async def toggle_auto_trade(symbol: str = DEFAULT_SYMBOL, enabled: bool = False):
    await db.risk_settings.update_one({"symbol": symbol}, {"$set": {"auto_trade": enabled}}, upsert=True)
    return {"status": "updated", "auto_trade": enabled}

# ---- ALERT ROUTES ----

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
    alerts = await db.alerts.find({"symbol": symbol}, {"_id": 0}).to_list(100)
    return {"alerts": alerts}

@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    await db.alerts.delete_one({"id": alert_id})
    return {"status": "deleted"}

@api_router.get("/notifications")
async def get_notifications(limit: int = 30):
    notifs = await db.notifications.find({}, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return {"notifications": notifs}

@api_router.get("/notifications/unread")
async def get_unread_count():
    count = await db.notifications.count_documents({"read": False})
    return {"unread": count}

@api_router.post("/notifications/read")
async def mark_all_read():
    await db.notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"status": "done"}

# Bot errors
@api_router.get("/bot/errors")
async def get_bot_errors(symbol: str = DEFAULT_SYMBOL):
    state = get_bot_state(symbol)
    return {"errors": state["errors"][-20:]}

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
    for state in bot_states.values():
        state["running"] = False
        if state["task"]:
            state["task"].cancel()
    client.close()
