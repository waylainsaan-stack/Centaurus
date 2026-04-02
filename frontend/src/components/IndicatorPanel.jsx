import React from "react";

function getRSIColor(rsi) {
  if (rsi === null || rsi === undefined) return '#52525b';
  if (rsi < 30) return '#00FF41';
  if (rsi > 70) return '#FF003C';
  return '#FDE047';
}

function getRSIZone(rsi) {
  if (rsi === null || rsi === undefined) return 'N/A';
  if (rsi < 30) return 'OVERSOLD';
  if (rsi > 70) return 'OVERBOUGHT';
  return 'NEUTRAL';
}

export default function IndicatorPanel({ indicators }) {
  const rsi = indicators?.rsi;
  const ema50 = indicators?.ema50;
  const ema200 = indicators?.ema200;
  const crossover = indicators?.ema_crossover;
  const price = indicators?.price;

  return (
    <div data-testid="indicator-panel" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <h3
        className="font-heading text-base font-bold uppercase tracking-widest mb-4"
        style={{ color: '#a1a1aa' }}
      >
        INDICATORS
      </h3>

      {/* RSI */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
            RSI (14)
          </span>
          <span className="text-xs font-mono font-bold" style={{ color: getRSIColor(rsi) }}>
            {rsi !== null && rsi !== undefined ? `${rsi} [${getRSIZone(rsi)}]` : '---'}
          </span>
        </div>
        <div className="progress-bar w-full">
          <div
            data-testid="rsi-bar"
            className="progress-fill"
            style={{
              width: rsi ? `${Math.min(rsi, 100)}%` : '0%',
              background: getRSIColor(rsi),
            }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-xs font-mono" style={{ color: '#00FF41' }}>30</span>
          <span className="text-xs font-mono" style={{ color: '#52525b' }}>50</span>
          <span className="text-xs font-mono" style={{ color: '#FF003C' }}>70</span>
        </div>
      </div>

      {/* EMA */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
            EMA 50
          </span>
          <span className="text-xs font-mono" style={{ color: '#fafafa' }}>
            {ema50 ? `$${ema50.toLocaleString()}` : '---'}
          </span>
        </div>
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
            EMA 200
          </span>
          <span className="text-xs font-mono" style={{ color: '#fafafa' }}>
            {ema200 ? `$${ema200.toLocaleString()}` : '---'}
          </span>
        </div>
      </div>

      {/* Crossover */}
      <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid #27272a' }}>
        <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
          EMA CROSS
        </span>
        <span
          data-testid="ema-crossover"
          className="text-xs font-mono font-bold uppercase"
          style={{ color: crossover === 'BULLISH' ? '#00FF41' : '#FF003C' }}
        >
          {crossover || '---'}
        </span>
      </div>

      {/* Current price vs EMA */}
      {price && ema50 && (
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
            PRICE vs EMA50
          </span>
          <span
            className="text-xs font-mono font-bold uppercase"
            style={{ color: price > ema50 ? '#00FF41' : '#FF003C' }}
          >
            {price > ema50 ? 'ABOVE' : 'BELOW'}
          </span>
        </div>
      )}
    </div>
  );
}
