import React from "react";

export default function MultiPairTicker({ prices, activeSymbol, onSelect }) {
  const items = prices || [];

  return (
    <div
      data-testid="multi-pair-ticker"
      className="flex overflow-x-auto gap-0"
      style={{ background: '#0A0A0A', borderBottom: '1px solid #27272a' }}
    >
      {items.map((p) => {
        const isActive = p.symbol === activeSymbol;
        const isUp = (p.change || 0) >= 0;
        return (
          <button
            key={p.symbol}
            data-testid={`pair-${p.symbol.replace('/', '-')}`}
            onClick={() => onSelect(p.symbol)}
            className="flex items-center gap-3 px-4 py-2 shrink-0 transition-colors duration-75"
            style={{
              background: isActive ? '#18181b' : 'transparent',
              borderRight: '1px solid #27272a',
              borderBottom: isActive ? '2px solid #fafafa' : '2px solid transparent',
              cursor: 'pointer',
            }}
          >
            <span className="text-xs font-mono font-bold uppercase" style={{ color: isActive ? '#fafafa' : '#52525b' }}>
              {p.symbol.split('/')[0]}
            </span>
            <span className="text-xs font-mono" style={{ color: '#fafafa' }}>
              {p.price ? `$${p.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '---'}
            </span>
            {p.change !== null && p.change !== undefined && (
              <span className="text-xs font-mono" style={{ color: isUp ? '#00FF41' : '#FF003C' }}>
                {isUp ? '+' : ''}{p.change?.toFixed(2)}%
              </span>
            )}
          </button>
        );
      })}
      {items.length === 0 && (
        <div className="px-4 py-2 text-xs font-mono" style={{ color: '#52525b' }}>
          LOADING PAIRS...
        </div>
      )}
    </div>
  );
}
