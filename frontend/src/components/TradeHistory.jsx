import React from "react";

function getSignalColor(signal) {
  if (!signal) return '#52525b';
  const s = signal.toUpperCase();
  if (s.includes('BUY')) return '#00FF41';
  if (s.includes('SELL')) return '#FF003C';
  return '#FDE047';
}

export default function TradeHistory({ signals }) {
  const rows = signals?.signals || [];

  return (
    <div data-testid="trade-history" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <h3
        className="font-heading text-base font-bold uppercase tracking-widest mb-4"
        style={{ color: '#a1a1aa' }}
      >
        SIGNAL LOG
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #27272a' }}>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>TIME</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>SIGNAL</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>PRICE</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>RSI</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>OB</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>AI</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>RSI SIG</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center" style={{ color: '#52525b' }}>
                  No signals recorded yet. Start the bot to begin monitoring.
                </td>
              </tr>
            )}
            {rows.map((row, i) => (
              <tr key={i} className="table-row" style={{ borderBottom: '1px solid #18181b' }}>
                <td className="px-3 py-2" style={{ color: '#52525b' }}>
                  {new Date(row.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </td>
                <td className="px-3 py-2 font-bold" style={{ color: getSignalColor(row.signal) }}>
                  {row.signal}
                </td>
                <td className="px-3 py-2 text-right" style={{ color: '#fafafa' }}>
                  ${row.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </td>
                <td className="px-3 py-2 text-right" style={{ color: '#a1a1aa' }}>
                  {row.rsi?.toFixed(1) || '---'}
                </td>
                <td className="px-3 py-2" style={{ color: getSignalColor(row.ob_signal) }}>
                  {row.ob_signal || '---'}
                </td>
                <td className="px-3 py-2" style={{ color: getSignalColor(row.ai_signal) }}>
                  {row.ai_signal || '---'}
                </td>
                <td className="px-3 py-2" style={{ color: getSignalColor(row.rsi_signal) }}>
                  {row.rsi_signal || '---'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
