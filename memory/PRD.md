# Crypto AI Trading Bot Dashboard - PRD

## Original Problem Statement
Build a crypto AI trading bot connecting to Binance API with real-time dashboard, LSTM prediction, live news sentiment, combined TA+Fundamentals signal engine, backtesting, and auto-trading.

## Architecture
- **Backend**: FastAPI + ccxt + PyTorch LSTM + emergentintegrations (GPT-5.2) + MongoDB
- **Frontend**: React + Recharts + Tailwind CSS (Neo-Brutalist Terminal)
- **Data**: Binance US API, CryptoPanic RSS, CoinDesk RSS, CoinTelegraph RSS
- **AI**: GPT-5.2 for market analysis + news sentiment
- **ML**: PyTorch LSTM (persistent to disk) for price prediction
- **Real-time**: WebSocket broadcasting
- **DB**: MongoDB (signals, trades, alerts, notifications, insights, news, backtests, risk settings)

## What's Been Implemented

### Phase 1 - MVP: 13 endpoints, bot loop, dashboard
### Phase 2 - Trading: Multi-pair (8), trade execution, risk management, alerts
### Phase 3 - AI/ML: LSTM model, live news, combined 5-source signal, WebSocket, MACD/Bollinger
### Phase 4 - Strategy (2026-04-02):
- **LSTM Persistence**: Model weights saved to disk, survives restarts
- **Backtesting Engine**: Run strategy against historical data, equity curve, win rate, Sharpe ratio, max drawdown, profit factor
- **Auto-Trading Mode**: Bot auto-executes on STRONG signals with configurable position size, SL/TP, min confidence, cooldown
- Tests: 100% backend (47/47), 100% frontend, 100% integration

## 47 API Endpoints
Market (8) | Bot (4) | Signals (3) | AI (3) | LSTM (3) | News (4) | Trades (4) | Risk (2) | Alerts (3) | Notifications (3) | Backtest (2) | Auto-Trade (4) | Pairs (1) | Combined (1) | Errors (1) | WebSocket (1)

## Backlog
### P1: Twitter/X sentiment, Telegram alerts
### P2: Portfolio tracking, PnL analytics, multi-timeframe analysis
