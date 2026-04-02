import React, { useState } from "react";
import { BarChart3 } from "lucide-react";
import { postApi } from "@/hooks/useApi";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export default function BacktestPanel({ symbol, onClose }) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [settings, setSettings] = useState({ limit: 500, position_size_pct: 10, stop_loss_pct: 2, take_profit_pct: 5, signal_filter: "STRONG" });

  const runBacktest = async () => {
    setRunning(true);
    try {
      const res = await postApi("/backtest/run", { symbol, ...settings });
      setResult(res);
    } catch (e) {
      setResult({ error: e.message });
    }
    setRunning(false);
  };

  const equityCurve = result?.equity_curve || [];
  const isProfit = (result?.total_return_pct || 0) >= 0;

  return (
    <div data-testid="backtest-panel" className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto" style={{ background: '#0A0A0A', border: '1px solid #27272a' }}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid #27272a' }}>
          <h2 className="font-heading text-lg font-bold uppercase tracking-tight flex items-center gap-2" style={{ color: '#fafafa' }}>
            <BarChart3 size={18} /> BACKTEST {symbol}
          </h2>
          <button data-testid="close-backtest" onClick={onClose} className="btn-terminal text-xs">CLOSE</button>
        </div>

        <div className="p-4 space-y-4">
          {/* Settings */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {[
              { key: 'limit', label: 'CANDLES', min: 100, max: 1000, step: 100 },
              { key: 'position_size_pct', label: 'SIZE %', min: 1, max: 50, step: 1 },
              { key: 'stop_loss_pct', label: 'SL %', min: 0.5, max: 10, step: 0.5 },
              { key: 'take_profit_pct', label: 'TP %', min: 1, max: 20, step: 1 },
            ].map(({ key, label, min, max, step }) => (
              <div key={key}>
                <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#52525b' }}>{label}</label>
                <input type="number" value={settings[key]} min={min} max={max} step={step}
                  onChange={e => setSettings(s => ({ ...s, [key]: parseFloat(e.target.value) }))}
                  className="w-full p-2 text-xs font-mono" style={{ background: '#000', border: '1px solid #27272a', color: '#fafafa', outline: 'none' }} />
              </div>
            ))}
            <div>
              <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#52525b' }}>FILTER</label>
              <div className="flex">
                {["STRONG", "ALL"].map(f => (
                  <button key={f} onClick={() => setSettings(s => ({ ...s, signal_filter: f }))}
                    className="flex-1 p-2 text-xs font-mono uppercase" style={{ background: settings.signal_filter === f ? '#18181b' : 'transparent', border: '1px solid #27272a', color: settings.signal_filter === f ? '#fafafa' : '#52525b' }}>{f}</button>
                ))}
              </div>
            </div>
          </div>

          <button data-testid="run-backtest-button" onClick={runBacktest} disabled={running}
            className="w-full py-3 text-sm font-mono font-bold uppercase tracking-widest" style={{ background: '#fafafa', color: '#000', opacity: running ? 0.4 : 1 }}>
            {running ? 'RUNNING BACKTEST...' : 'RUN BACKTEST'}
          </button>

          {/* Results */}
          {result && !result.error && (
            <div className="animate-in space-y-4">
              {/* Key metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { label: 'TOTAL RETURN', value: `${result.total_return_pct}%`, color: isProfit ? '#00FF41' : '#FF003C' },
                  { label: 'WIN RATE', value: `${result.win_rate}%`, color: result.win_rate >= 50 ? '#00FF41' : '#FF003C' },
                  { label: 'SHARPE', value: result.sharpe_ratio, color: result.sharpe_ratio >= 1 ? '#00FF41' : '#FDE047' },
                  { label: 'MAX DRAWDOWN', value: `${result.max_drawdown_pct}%`, color: '#FF003C' },
                  { label: 'TOTAL PNL', value: `$${result.total_pnl}`, color: isProfit ? '#00FF41' : '#FF003C' },
                  { label: 'TRADES', value: result.total_trades, color: '#fafafa' },
                  { label: 'AVG WIN', value: `$${result.avg_win}`, color: '#00FF41' },
                  { label: 'AVG LOSS', value: `$${result.avg_loss}`, color: '#FF003C' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="p-3 text-center" style={{ background: '#000', border: '1px solid #27272a' }}>
                    <div className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>{label}</div>
                    <div className="text-lg font-heading font-black mt-1" style={{ color }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Equity curve */}
              {equityCurve.length > 0 && (
                <div>
                  <div className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: '#52525b' }}>EQUITY CURVE</div>
                  <div style={{ width: '100%', height: 200 }}>
                    <ResponsiveContainer>
                      <AreaChart data={equityCurve}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#18181b" />
                        <XAxis dataKey="time" tick={false} axisLine={{ stroke: '#27272a' }} />
                        <YAxis tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={{ stroke: '#27272a' }} tickFormatter={v => `$${v.toLocaleString()}`} width={80} />
                        <Tooltip contentStyle={{ background: '#000', border: '1px solid #fafafa', fontFamily: 'JetBrains Mono', fontSize: 11 }} />
                        <Area type="monotone" dataKey="equity" stroke={isProfit ? '#00FF41' : '#FF003C'} fill={isProfit ? 'rgba(0,255,65,0.1)' : 'rgba(255,0,60,0.1)'} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Recent trades */}
              {result.trades?.length > 0 && (
                <div>
                  <div className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: '#52525b' }}>RECENT TRADES ({result.trades.length})</div>
                  <div className="overflow-x-auto">
                    <table className="w-full" style={{ fontFamily: 'JetBrains Mono', fontSize: 10 }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid #27272a' }}>
                          <th className="text-left px-2 py-1" style={{ color: '#52525b' }}>SIDE</th>
                          <th className="text-right px-2 py-1" style={{ color: '#52525b' }}>ENTRY</th>
                          <th className="text-right px-2 py-1" style={{ color: '#52525b' }}>EXIT</th>
                          <th className="text-right px-2 py-1" style={{ color: '#52525b' }}>PNL</th>
                          <th className="text-left px-2 py-1" style={{ color: '#52525b' }}>REASON</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.trades.map((t, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid #18181b' }}>
                            <td className="px-2 py-1 font-bold" style={{ color: t.side === 'BUY' ? '#00FF41' : '#FF003C' }}>{t.side}</td>
                            <td className="px-2 py-1 text-right" style={{ color: '#a1a1aa' }}>${t.entry_price}</td>
                            <td className="px-2 py-1 text-right" style={{ color: '#a1a1aa' }}>${t.exit_price}</td>
                            <td className="px-2 py-1 text-right font-bold" style={{ color: t.pnl >= 0 ? '#00FF41' : '#FF003C' }}>${t.pnl} ({t.pnl_pct}%)</td>
                            <td className="px-2 py-1" style={{ color: t.reason === 'TAKE_PROFIT' ? '#00FF41' : t.reason === 'STOP_LOSS' ? '#FF003C' : '#52525b' }}>{t.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
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
