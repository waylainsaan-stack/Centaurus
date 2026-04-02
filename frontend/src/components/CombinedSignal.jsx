import React from "react";

function getSignalStyle(signal) {
  if (!signal) return { color: '#FDE047', bg: 'rgba(253,224,71,0.1)', border: '#FDE047' };
  const s = signal.toUpperCase();
  if (s.includes('BUY')) return { color: '#00FF41', bg: 'rgba(0,255,65,0.1)', border: '#00FF41' };
  if (s.includes('SELL')) return { color: '#FF003C', bg: 'rgba(255,0,60,0.1)', border: '#FF003C' };
  return { color: '#FDE047', bg: 'rgba(253,224,71,0.1)', border: '#FDE047' };
}

export default function CombinedSignal({ combined, currentSignal, botStatus }) {
  const signal = combined?.signal || currentSignal?.signal || botStatus?.last_signal || 'WAIT';
  const style = getSignalStyle(signal);
  const price = currentSignal?.price || botStatus?.last_price;
  const confidence = combined?.confidence || 0;
  const breakdown = combined?.breakdown || {};
  const components = combined?.components || {};

  return (
    <div data-testid="combined-signal" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      {/* Main signal */}
      <div className="flex flex-col items-center justify-center mb-4 py-4" style={{ background: style.bg, borderLeft: `3px solid ${style.border}` }}>
        <span className="text-xs font-mono uppercase tracking-widest mb-1" style={{ color: '#a1a1aa' }}>COMBINED SIGNAL</span>
        <span data-testid="signal-value" className="font-heading font-black tracking-tighter uppercase leading-none" style={{ color: style.color, fontSize: 'clamp(2rem, 5vw, 4rem)' }}>
          {signal}
        </span>
        {price && <span className="text-sm font-mono mt-2" style={{ color: '#a1a1aa' }}>@ ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>}
        {confidence > 0 && <span className="text-xs font-mono mt-1" style={{ color: style.color }}>CONFIDENCE: {confidence}%</span>}
      </div>

      {/* Signal breakdown */}
      <div className="space-y-2">
        <div className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: '#52525b' }}>SIGNAL SOURCES</div>
        {[
          { key: 'technical', label: 'TA (RSI/EMA/MACD)', weight: '25%' },
          { key: 'orderbook', label: 'ORDER BOOK', weight: '15%' },
          { key: 'lstm', label: 'LSTM PREDICTION', weight: '20%' },
          { key: 'news', label: 'NEWS SENTIMENT', weight: '20%' },
          { key: 'ai', label: 'GPT-5.2 AI', weight: '20%' },
        ].map(({ key, label, weight }) => {
          const sig = components[key] || 'HOLD';
          const score = breakdown[key] || 0;
          const sigStyle = getSignalStyle(sig);
          return (
            <div key={key} className="flex items-center justify-between py-1" style={{ borderBottom: '1px solid #18181b' }}>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono" style={{ color: '#52525b' }}>{weight}</span>
                <span className="text-xs font-mono uppercase" style={{ color: '#a1a1aa' }}>{label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold" style={{ color: sigStyle.color }}>{sig}</span>
                <span className="text-xs font-mono" style={{ color: score > 0 ? '#00FF41' : score < 0 ? '#FF003C' : '#52525b' }}>
                  {score > 0 ? '+' : ''}{(score * 100).toFixed(0)}
                </span>
              </div>
            </div>
          );
        })}

        {/* Total score bar */}
        {combined?.score !== undefined && (
          <div className="mt-3 pt-2" style={{ borderTop: '1px solid #27272a' }}>
            <div className="flex justify-between mb-1">
              <span className="text-xs font-mono" style={{ color: '#FF003C' }}>SELL</span>
              <span className="text-xs font-mono font-bold" style={{ color: style.color }}>
                SCORE: {combined.score > 0 ? '+' : ''}{(combined.score * 100).toFixed(0)}
              </span>
              <span className="text-xs font-mono" style={{ color: '#00FF41' }}>BUY</span>
            </div>
            <div className="h-2 w-full relative" style={{ background: '#18181b' }}>
              <div className="absolute top-0 h-full" style={{ left: '50%', width: '1px', background: '#52525b' }} />
              <div
                className="absolute top-0 h-full"
                style={{
                  left: combined.score >= 0 ? '50%' : `${50 + combined.score * 50}%`,
                  width: `${Math.abs(combined.score) * 50}%`,
                  background: combined.score >= 0 ? '#00FF41' : '#FF003C',
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
