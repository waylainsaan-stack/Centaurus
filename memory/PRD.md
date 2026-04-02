# Crypto AI Trading Bot Dashboard - PRD

## Original Problem Statement
Build a crypto AI trading bot that connects to Binance API with a real-time web dashboard. Bot monitors BTC/USDT using RSI/EMA indicators, order book analysis, and GPT-5.2 AI for market signal generation.

## Architecture
- **Backend**: FastAPI + ccxt (binanceus) + emergentintegrations (GPT-5.2) + MongoDB
- **Frontend**: React + Recharts + Tailwind CSS (Neo-Brutalist Terminal design)
- **Data Source**: Binance US public API (binance.com geo-restricted from server)
- **AI**: OpenAI GPT-5.2 via Emergent LLM key
- **Database**: MongoDB for signal history, AI insights

## User Persona
Crypto trader wanting automated market monitoring with AI-driven signal analysis

## Core Requirements
1. Live BTC/USDT price from Binance
2. Technical indicators (RSI-14, EMA-50, EMA-200)
3. Order book pressure analysis
4. GPT-5.2 AI market analysis
5. Combined signal engine (STRONG BUY / STRONG SELL / WAIT)
6. Real-time dashboard with charts
7. Bot start/stop controls
8. Signal and AI insight history logging

## What's Been Implemented (2026-04-02)
- Full backend with 13 API endpoints for market data, bot control, signals, AI
- Background bot loop with 60s interval
- Real-time dashboard: price chart, signal display, indicators, order book, AI terminal, trade history
- All tests passing (100% backend, 100% frontend)
- Live Binance data flowing via binanceus exchange

## Prioritized Backlog
### P0 (Critical)
- None - core MVP complete

### P1 (Important)
- Trade execution (place real orders via Binance Ed25519 auth)
- Risk management (stop-loss, take-profit settings)
- Multiple trading pair support
- Portfolio balance display

### P2 (Nice to Have)
- LSTM/ML model for price prediction
- WebSocket for real-time price streaming (instead of polling)
- Email/Telegram alerts on strong signals
- Backtesting engine
- PnL tracking and performance analytics

## Next Tasks
1. Top up Emergent Universal Key for continuous AI analysis
2. Add Binance API key (alphanumeric) to enable authenticated endpoints
3. Implement trade execution when ready for live trading
4. Add WebSocket real-time streaming
