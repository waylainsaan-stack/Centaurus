import React from "react";

function getSignalStyle(signal) {
  if (!signal) return { color: '#FDE047', bg: 'rgba(253,224,71,0.1)', border: '#FDE047' };
  const s = signal.toUpperCase();
  if (s.includes('BUY')) return { color: '#00FF41', bg: 'rgba(0,255,65,0.1)', border: '#00FF41' };
  if (s.includes('SELL')) return { color: '#FF003C', bg: 'rgba(255,0,60,0.1)', border: '#FF003C' };
  return { color: '#FDE047', bg: 'rgba(253,224,71,0.1)', border: '#FDE047' };
}

export default function SignalDisplay({ currentSignal, botStatus }) {
  const signal = currentSignal?.signal || botStatus?.last_signal || 'WAIT';
  const style = getSignalStyle(signal);
  const price = currentSignal?.price || botStatus?.last_price;

  return (
    <div
      data-testid="signal-display"
      className="p-4 md:p-6 flex flex-col items-center justify-center"
      style={{
        background: style.bg,
        borderLeft: `2px solid ${style.border}`,
        minHeight: 200,
      }}
    >
      <span className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: '#a1a1aa' }}>
        TRADING SIGNAL
      </span>
      <span
        data-testid="signal-value"
        className="font-heading font-black tracking-tighter uppercase leading-none"
        style={{ color: style.color, fontSize: 'clamp(2.5rem, 6vw, 5rem)' }}
      >
        {signal}
      </span>
      {price && (
        <span className="text-sm font-mono mt-3" style={{ color: '#a1a1aa' }}>
          @ ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      )}

      {/* Sub-signals breakdown */}
      {currentSignal && (
        <div className="flex gap-4 mt-4">
          {currentSignal.indicators?.rsi && (
            <SubSignal label="RSI" value={currentSignal.indicators.rsi_zone || 'N/A'} />
          )}
          {currentSignal.orderbook?.signal && (
            <SubSignal label="OB" value={currentSignal.orderbook.signal} />
          )}
        </div>
      )}
    </div>
  );
}

function SubSignal({ label, value }) {
  const style = getSignalStyle(value);
  return (
    <div className="flex items-center gap-1">
      <span className="text-xs font-mono uppercase" style={{ color: '#52525b' }}>{label}:</span>
      <span className="text-xs font-mono font-bold uppercase" style={{ color: style.color }}>{value}</span>
    </div>
  );
}
