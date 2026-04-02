import React from "react";

export default function OrderBook({ data }) {
  const bids = data?.bids || [];
  const asks = data?.asks || [];
  const bidVol = data?.bid_volume;
  const askVol = data?.ask_volume;
  const ratio = data?.ratio;
  const signal = data?.signal;

  return (
    <div data-testid="orderbook-panel" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <div className="flex items-center justify-between mb-4">
        <h3
          className="font-heading text-base font-bold uppercase tracking-widest"
          style={{ color: '#a1a1aa' }}
        >
          ORDER BOOK
        </h3>
        {signal && (
          <span
            data-testid="orderbook-signal"
            className="text-xs font-mono font-bold uppercase"
            style={{ color: signal === 'BUY' ? '#00FF41' : '#FF003C' }}
          >
            PRESSURE: {signal}
          </span>
        )}
      </div>

      {/* Volume bar */}
      {bidVol !== undefined && askVol !== undefined && (
        <div className="mb-4">
          <div className="flex justify-between mb-1">
            <span className="text-xs font-mono" style={{ color: '#00FF41' }}>
              BIDS: {bidVol}
            </span>
            <span className="text-xs font-mono" style={{ color: '#52525b' }}>
              {ratio}x
            </span>
            <span className="text-xs font-mono" style={{ color: '#FF003C' }}>
              ASKS: {askVol}
            </span>
          </div>
          <div className="flex h-2 w-full" style={{ background: '#18181b' }}>
            <div
              style={{
                width: `${(bidVol / (bidVol + askVol)) * 100}%`,
                background: '#00FF41',
              }}
            />
            <div
              style={{
                width: `${(askVol / (bidVol + askVol)) * 100}%`,
                background: '#FF003C',
              }}
            />
          </div>
        </div>
      )}

      {/* Two columns: Bids | Asks */}
      <div className="grid grid-cols-2 gap-0">
        {/* Bids */}
        <div style={{ borderRight: '1px solid #27272a' }}>
          <div className="flex justify-between px-2 py-1" style={{ borderBottom: '1px solid #27272a' }}>
            <span className="text-xs font-mono uppercase" style={{ color: '#52525b' }}>PRICE</span>
            <span className="text-xs font-mono uppercase" style={{ color: '#52525b' }}>QTY</span>
          </div>
          {bids.slice(0, 8).map((b, i) => (
            <div key={i} className="flex justify-between px-2 py-1 table-row">
              <span className="text-xs font-mono" style={{ color: '#00FF41' }}>
                {b.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
              <span className="text-xs font-mono" style={{ color: '#a1a1aa' }}>
                {b.amount?.toFixed(5)}
              </span>
            </div>
          ))}
        </div>

        {/* Asks */}
        <div>
          <div className="flex justify-between px-2 py-1" style={{ borderBottom: '1px solid #27272a' }}>
            <span className="text-xs font-mono uppercase" style={{ color: '#52525b' }}>PRICE</span>
            <span className="text-xs font-mono uppercase" style={{ color: '#52525b' }}>QTY</span>
          </div>
          {asks.slice(0, 8).map((a, i) => (
            <div key={i} className="flex justify-between px-2 py-1 table-row">
              <span className="text-xs font-mono" style={{ color: '#FF003C' }}>
                {a.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </span>
              <span className="text-xs font-mono" style={{ color: '#a1a1aa' }}>
                {a.amount?.toFixed(5)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
