# Crypto AI Trading Bot Dashboard - PRD

## Original Problem Statement
Build a crypto AI trading bot connecting to Binance API with real-time dashboard, LSTM prediction, live news sentiment, and combined TA+Fundamentals signal engine.

## Architecture
- **Backend**: FastAPI + ccxt (binanceus) + PyTorch LSTM + emergentintegrations (GPT-5.2) + MongoDB
- **Frontend**: React + Recharts + Tailwind CSS (Neo-Brutalist Terminal)
- **Data**: Binance US public API, CryptoPanic RSS, CoinDesk RSS, CoinTelegraph RSS
- **AI**: GPT-5.2 for market analysis + news sentiment
- **ML**: PyTorch LSTM for price direction prediction
- **Real-time**: WebSocket broadcasting from bot loop
- **DB**: MongoDB (signals, trades, alerts, notifications, AI insights, news, risk settings)

## Combined Signal Engine (5 Sources)
| Source | Weight | Type |
|--------|--------|------|
| Technical Analysis (RSI/EMA/MACD) | 25% | Technical |
| Order Book Pressure | 15% | Technical |
| LSTM Model Prediction | 20% | ML |
| News Sentiment (GPT-5.2) | 20% | Fundamental |
| AI Market Analysis (GPT-5.2) | 20% | Fundamental |

## What's Been Implemented

### Phase 1 - MVP (2026-04-02)
- Backend with 13 endpoints, bot loop, real-time dashboard

### Phase 2 - Trading Features (2026-04-02)
- Multi-pair (8 pairs), trade execution, risk management, alerts, notifications

### Phase 3 - AI/ML + News (2026-04-02)
- **LSTM Model**: PyTorch LSTM trained on 500 OHLCV candles, predicts price direction
- **Live News**: RSS feeds from CryptoPanic, CoinDesk, CoinTelegraph
- **News Sentiment**: GPT-5.2 analyzes headlines, returns BULLISH/BEARISH/NEUTRAL with score
- **Combined Signal**: Weighted engine merging 5 signal sources
- **WebSocket**: Real-time streaming of price, signal, indicators to frontend
- **Extended TA**: Added MACD, Bollinger Bands to indicators
- Tests: 100% backend (38/38), 100% frontend, 100% integration

## Prioritized Backlog
### P1
- Persistent LSTM model (save/load to disk)
- Twitter/X social sentiment integration
- Trailing stop-loss, auto-trade mode
### P2
- Telegram bot for push alerts
- Backtesting engine, PnL analytics
- Bloomberg/CMC direct feed integration
