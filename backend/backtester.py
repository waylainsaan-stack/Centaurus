import pandas as pd
import numpy as np
import ta as ta_lib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def compute_signals_for_backtest(df):
    """Compute TA signals for each row in the dataframe."""
    df = df.copy()
    df['rsi'] = ta_lib.momentum.RSIIndicator(df['close']).rsi()
    df['ema50'] = ta_lib.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema200'] = ta_lib.trend.EMAIndicator(df['close'], window=200).ema_indicator()
    df['macd'] = ta_lib.trend.MACD(df['close']).macd()
    df['macd_signal'] = ta_lib.trend.MACD(df['close']).macd_signal()

    signals = []
    for i in range(len(df)):
        row = df.iloc[i]
        score = 0
        rsi = row['rsi']
        if pd.notna(rsi):
            if rsi < 30:
                score += 2
            elif rsi < 40:
                score += 1
            elif rsi > 70:
                score -= 2
            elif rsi > 60:
                score -= 1

        if pd.notna(row['ema50']) and pd.notna(row['ema200']):
            if row['ema50'] > row['ema200']:
                score += 1
            else:
                score -= 1

        if pd.notna(row['macd']) and pd.notna(row['macd_signal']):
            if row['macd'] > row['macd_signal']:
                score += 1
            else:
                score -= 1

        if score >= 3:
            signals.append("STRONG BUY")
        elif score >= 1:
            signals.append("BUY")
        elif score <= -3:
            signals.append("STRONG SELL")
        elif score <= -1:
            signals.append("SELL")
        else:
            signals.append("WAIT")

    df['signal'] = signals
    return df


def run_backtest(df, initial_capital=10000, position_size_pct=10, stop_loss_pct=2.0, take_profit_pct=5.0, signal_filter="STRONG"):
    """
    Run backtest on historical OHLCV data.
    signal_filter: "STRONG" = only STRONG BUY/SELL, "ALL" = all BUY/SELL signals
    """
    if df is None or len(df) < 210:
        return {"error": "Need at least 210 candles for backtesting"}

    df = compute_signals_for_backtest(df)
    df = df.dropna(subset=['rsi', 'ema50', 'ema200']).reset_index(drop=True)

    capital = initial_capital
    position = None  # {side, entry_price, amount, stop_loss, take_profit}
    trades = []
    equity_curve = []
    peak_equity = initial_capital
    max_drawdown = 0

    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close']
        signal = row['signal']
        current_equity = capital + (((price - position['entry_price']) * position['amount']) if position and position['side'] == 'BUY' else ((position['entry_price'] - price) * position['amount']) if position else 0)

        equity_curve.append({"time": row['time'].isoformat() if hasattr(row['time'], 'isoformat') else str(row['time']), "equity": round(current_equity, 2), "price": round(price, 2)})

        if current_equity > peak_equity:
            peak_equity = current_equity
        dd = (peak_equity - current_equity) / peak_equity * 100
        if dd > max_drawdown:
            max_drawdown = dd

        # Check stop loss / take profit
        if position:
            pnl = 0
            close_reason = None
            if position['side'] == 'BUY':
                if price <= position['stop_loss']:
                    pnl = (price - position['entry_price']) * position['amount']
                    close_reason = "STOP_LOSS"
                elif price >= position['take_profit']:
                    pnl = (price - position['entry_price']) * position['amount']
                    close_reason = "TAKE_PROFIT"
            else:  # SELL
                if price >= position['stop_loss']:
                    pnl = (position['entry_price'] - price) * position['amount']
                    close_reason = "STOP_LOSS"
                elif price <= position['take_profit']:
                    pnl = (position['entry_price'] - price) * position['amount']
                    close_reason = "TAKE_PROFIT"

            if close_reason:
                capital += pnl
                trades.append({
                    "entry_time": position['entry_time'],
                    "exit_time": row['time'].isoformat() if hasattr(row['time'], 'isoformat') else str(row['time']),
                    "side": position['side'], "entry_price": round(position['entry_price'], 2),
                    "exit_price": round(price, 2), "amount": position['amount'],
                    "pnl": round(pnl, 2), "pnl_pct": round(pnl / (position['entry_price'] * position['amount']) * 100, 2),
                    "reason": close_reason,
                })
                position = None

        # Open new position
        if position is None:
            should_trade = False
            if signal_filter == "STRONG":
                should_trade = signal in ["STRONG BUY", "STRONG SELL"]
            else:
                should_trade = signal in ["BUY", "STRONG BUY", "SELL", "STRONG SELL"]

            if should_trade:
                side = "BUY" if "BUY" in signal else "SELL"
                amount = (capital * position_size_pct / 100) / price
                sl = price * (1 - stop_loss_pct / 100) if side == "BUY" else price * (1 + stop_loss_pct / 100)
                tp = price * (1 + take_profit_pct / 100) if side == "BUY" else price * (1 - take_profit_pct / 100)
                position = {
                    "side": side, "entry_price": price, "amount": amount,
                    "stop_loss": sl, "take_profit": tp,
                    "entry_time": row['time'].isoformat() if hasattr(row['time'], 'isoformat') else str(row['time']),
                }

    # Close any open position at end
    if position:
        last_price = df.iloc[-1]['close']
        pnl = (last_price - position['entry_price']) * position['amount'] if position['side'] == 'BUY' else (position['entry_price'] - last_price) * position['amount']
        capital += pnl
        trades.append({
            "entry_time": position['entry_time'],
            "exit_time": df.iloc[-1]['time'].isoformat() if hasattr(df.iloc[-1]['time'], 'isoformat') else str(df.iloc[-1]['time']),
            "side": position['side'], "entry_price": round(position['entry_price'], 2),
            "exit_price": round(last_price, 2), "amount": position['amount'],
            "pnl": round(pnl, 2), "pnl_pct": round(pnl / (position['entry_price'] * position['amount']) * 100, 2),
            "reason": "END_OF_DATA",
        })

    # Calculate metrics
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in trades)
    returns = [t['pnl_pct'] for t in trades] if trades else [0]
    avg_return = np.mean(returns) if returns else 0
    std_return = np.std(returns) if len(returns) > 1 else 1
    sharpe = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0

    return {
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round((capital - initial_capital) / initial_capital * 100, 2),
        "total_trades": len(trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "avg_win": round(np.mean([t['pnl'] for t in wins]), 2) if wins else 0,
        "avg_loss": round(np.mean([t['pnl'] for t in losses]), 2) if losses else 0,
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 2),
        "profit_factor": round(abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)), 2) if losses and sum(t['pnl'] for t in losses) != 0 else 0,
        "trades": trades[-20:],  # Last 20 trades
        "equity_curve": equity_curve[::max(1, len(equity_curve)//100)],  # Sampled to ~100 points
        "settings": {
            "position_size_pct": position_size_pct,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "signal_filter": signal_filter,
        },
        "candles_tested": len(df),
    }
