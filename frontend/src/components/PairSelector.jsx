import React from "react";

const PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT'];

export default function PairSelector({ activeSymbol, onSelect }) {
  return (
    <div data-testid="pair-selector" className="flex gap-1 flex-wrap">
      {PAIRS.map(pair => (
        <button
          key={pair}
          onClick={() => onSelect(pair)}
          className="text-xs font-mono uppercase tracking-widest px-3 py-1 transition-colors duration-75"
          style={{
            background: pair === activeSymbol ? '#18181b' : 'transparent',
            border: '1px solid',
            borderColor: pair === activeSymbol ? '#fafafa' : '#27272a',
            color: pair === activeSymbol ? '#fafafa' : '#52525b',
          }}
        >
          {pair.split('/')[0]}
        </button>
      ))}
    </div>
  );
}
