import React, { useState } from "react";
import { X, ArrowUpRight, ArrowDownRight, Shield } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function TradePanel({ symbol, priceData, onClose, refetchTrades }) {
  const [side, setSide] = useState("BUY");
  const [amount, setAmount] = useState("");
  const [orderType, setOrderType] = useState("MARKET");
  const [limitPrice, setLimitPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);

  const price = priceData?.price || 0;
  const base = symbol.split("/")[0];

  const executeTrade = async () => {
    if (!amount || parseFloat(amount) <= 0) return;
    setExecuting(true);
    setResult(null);
    try {
      const res = await postApi("/trades/execute", {
        symbol,
        side,
        type: orderType,
        amount: parseFloat(amount),
        price: orderType === "LIMIT" ? parseFloat(limitPrice) : null,
        stop_loss: stopLoss ? parseFloat(stopLoss) : null,
        take_profit: takeProfit ? parseFloat(takeProfit) : null,
      });
      setResult(res);
      refetchTrades();
    } catch (e) {
      setResult({ error: e.message });
    } finally {
      setExecuting(false);
    }
  };

  const setQuickSL = (pct) => {
    if (!price) return;
    const sl = side === "BUY" ? price * (1 - pct / 100) : price * (1 + pct / 100);
    setStopLoss(sl.toFixed(2));
  };

  const setQuickTP = (pct) => {
    if (!price) return;
    const tp = side === "BUY" ? price * (1 + pct / 100) : price * (1 - pct / 100);
    setTakeProfit(tp.toFixed(2));
  };

  return (
    <div data-testid="trade-panel" className="fixed inset-0 z-50 flex items-start justify-end" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div className="w-full max-w-md h-full overflow-y-auto" style={{ background: '#0A0A0A', borderLeft: '1px solid #27272a' }}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid #27272a' }}>
          <h2 className="font-heading text-lg font-bold uppercase tracking-tight" style={{ color: '#fafafa' }}>
            TRADE {symbol}
          </h2>
          <button data-testid="close-trade-panel" onClick={onClose} className="btn-terminal p-2"><X size={16} /></button>
        </div>

        <div className="p-4 space-y-4">
          {/* Current price */}
          <div className="text-center py-3" style={{ background: '#000', border: '1px solid #27272a' }}>
            <div className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>CURRENT PRICE</div>
            <div className="text-2xl font-heading font-black" style={{ color: '#fafafa' }}>
              ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
          </div>

          {/* Side toggle */}
          <div className="grid grid-cols-2 gap-0">
            <button
              data-testid="side-buy"
              onClick={() => setSide("BUY")}
              className="py-3 text-sm font-mono font-bold uppercase tracking-widest transition-colors duration-75"
              style={{
                background: side === "BUY" ? 'rgba(0,255,65,0.15)' : 'transparent',
                border: '1px solid',
                borderColor: side === "BUY" ? '#00FF41' : '#27272a',
                color: side === "BUY" ? '#00FF41' : '#52525b',
              }}
            >
              <ArrowUpRight size={14} className="inline mr-1" /> BUY
            </button>
            <button
              data-testid="side-sell"
              onClick={() => setSide("SELL")}
              className="py-3 text-sm font-mono font-bold uppercase tracking-widest transition-colors duration-75"
              style={{
                background: side === "SELL" ? 'rgba(255,0,60,0.15)' : 'transparent',
                border: '1px solid',
                borderColor: side === "SELL" ? '#FF003C' : '#27272a',
                color: side === "SELL" ? '#FF003C' : '#52525b',
              }}
            >
              <ArrowDownRight size={14} className="inline mr-1" /> SELL
            </button>
          </div>

          {/* Order type */}
          <div className="grid grid-cols-2 gap-0">
            {["MARKET", "LIMIT"].map(t => (
              <button
                key={t}
                data-testid={`order-type-${t.toLowerCase()}`}
                onClick={() => setOrderType(t)}
                className="py-2 text-xs font-mono uppercase tracking-widest transition-colors duration-75"
                style={{
                  background: orderType === t ? '#18181b' : 'transparent',
                  border: '1px solid #27272a',
                  color: orderType === t ? '#fafafa' : '#52525b',
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Amount */}
          <div>
            <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#52525b' }}>
              AMOUNT ({base})
            </label>
            <input
              data-testid="trade-amount"
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              placeholder="0.001"
              className="w-full p-3 text-sm font-mono"
              style={{ background: '#000', border: '1px solid #27272a', color: '#fafafa', outline: 'none' }}
            />
            <div className="flex gap-1 mt-1">
              {[0.001, 0.005, 0.01, 0.05].map(v => (
                <button key={v} onClick={() => setAmount(String(v))} className="text-xs font-mono px-2 py-1" style={{ background: '#18181b', color: '#a1a1aa', border: '1px solid #27272a' }}>{v}</button>
              ))}
            </div>
          </div>

          {/* Limit price */}
          {orderType === "LIMIT" && (
            <div>
              <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#52525b' }}>LIMIT PRICE (USDT)</label>
              <input
                data-testid="limit-price"
                type="number"
                value={limitPrice}
                onChange={e => setLimitPrice(e.target.value)}
                placeholder={price.toFixed(2)}
                className="w-full p-3 text-sm font-mono"
                style={{ background: '#000', border: '1px solid #27272a', color: '#fafafa', outline: 'none' }}
              />
            </div>
          )}

          {/* Risk Management */}
          <div style={{ borderTop: '1px solid #27272a', paddingTop: 16 }}>
            <div className="flex items-center gap-2 mb-3">
              <Shield size={14} style={{ color: '#a1a1aa' }} />
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#a1a1aa' }}>RISK MANAGEMENT</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#FF003C' }}>STOP LOSS (USDT)</label>
                <input
                  data-testid="stop-loss-input"
                  type="number"
                  value={stopLoss}
                  onChange={e => setStopLoss(e.target.value)}
                  placeholder="Optional"
                  className="w-full p-3 text-sm font-mono"
                  style={{ background: '#000', border: '1px solid #27272a', color: '#FF003C', outline: 'none' }}
                />
                <div className="flex gap-1 mt-1">
                  {[1, 2, 3, 5].map(pct => (
                    <button key={pct} onClick={() => setQuickSL(pct)} className="text-xs font-mono px-2 py-1" style={{ background: 'rgba(255,0,60,0.1)', color: '#FF003C', border: '1px solid #27272a' }}>-{pct}%</button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#00FF41' }}>TAKE PROFIT (USDT)</label>
                <input
                  data-testid="take-profit-input"
                  type="number"
                  value={takeProfit}
                  onChange={e => setTakeProfit(e.target.value)}
                  placeholder="Optional"
                  className="w-full p-3 text-sm font-mono"
                  style={{ background: '#000', border: '1px solid #27272a', color: '#00FF41', outline: 'none' }}
                />
                <div className="flex gap-1 mt-1">
                  {[2, 5, 10, 15].map(pct => (
                    <button key={pct} onClick={() => setQuickTP(pct)} className="text-xs font-mono px-2 py-1" style={{ background: 'rgba(0,255,65,0.1)', color: '#00FF41', border: '1px solid #27272a' }}>+{pct}%</button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Execute button */}
          <button
            data-testid="execute-trade-button"
            onClick={executeTrade}
            disabled={executing || !amount}
            className="w-full py-4 text-sm font-mono font-bold uppercase tracking-widest transition-colors duration-75"
            style={{
              background: side === "BUY" ? '#00FF41' : '#FF003C',
              color: '#000',
              border: 'none',
              opacity: executing || !amount ? 0.4 : 1,
              cursor: executing || !amount ? 'not-allowed' : 'pointer',
            }}
          >
            {executing ? 'EXECUTING...' : `${side} ${amount || '0'} ${base}`}
          </button>

          {/* Result */}
          {result && !result.error && (
            <div data-testid="trade-result" className="p-3 animate-in" style={{ background: 'rgba(0,255,65,0.1)', border: '1px solid #00FF41' }}>
              <div className="text-xs font-mono uppercase" style={{ color: '#00FF41' }}>
                {result.status} | {result.side} {result.amount} @ ${result.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              {result.stop_loss && <div className="text-xs font-mono" style={{ color: '#FF003C' }}>SL: ${result.stop_loss.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>}
              {result.take_profit && <div className="text-xs font-mono" style={{ color: '#00FF41' }}>TP: ${result.take_profit.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>}
            </div>
          )}
          {result?.error && (
            <div className="p-3" style={{ background: 'rgba(255,0,60,0.1)', border: '1px solid #FF003C' }}>
              <div className="text-xs font-mono" style={{ color: '#FF003C' }}>ERR: {result.error}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
