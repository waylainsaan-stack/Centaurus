import React from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: '#000',
        border: '1px solid #fafafa',
        padding: '8px 12px',
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '11px',
      }}
    >
      <div style={{ color: '#a1a1aa', marginBottom: 4 }}>{d.label}</div>
      <div style={{ color: '#fafafa' }}>O: ${d.open?.toLocaleString()}</div>
      <div style={{ color: '#fafafa' }}>H: ${d.high?.toLocaleString()}</div>
      <div style={{ color: '#fafafa' }}>L: ${d.low?.toLocaleString()}</div>
      <div style={{ color: '#fafafa', fontWeight: 700 }}>C: ${d.close?.toLocaleString()}</div>
      <div style={{ color: '#52525b' }}>V: {d.volume?.toFixed(2)}</div>
    </div>
  );
}

export default function PriceChart({ ohlcvData, priceData }) {
  const chartData = (ohlcvData?.data || []).map((d, i) => ({
    ...d,
    label: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    idx: i,
  }));

  const prices = chartData.map(d => d.close).filter(Boolean);
  const minPrice = prices.length ? Math.min(...prices) * 0.9999 : 0;
  const maxPrice = prices.length ? Math.max(...prices) * 1.0001 : 100;
  const isUp = chartData.length >= 2 && chartData[chartData.length - 1]?.close >= chartData[0]?.close;

  return (
    <div data-testid="price-chart-panel" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <div className="flex items-center justify-between mb-4">
        <h3
          className="font-heading text-base font-bold uppercase tracking-widest"
          style={{ color: '#a1a1aa' }}
        >
          {ohlcvData?.symbol || 'BTC/USDT'} PRICE
        </h3>
        <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
          {ohlcvData?.timeframe || '1m'} CANDLES
        </span>
      </div>

      <div style={{ width: '100%', height: 320 }}>
        {chartData.length > 0 ? (
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <defs>
                <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isUp ? '#00FF41' : '#FF003C'} stopOpacity={0.15} />
                  <stop offset="100%" stopColor={isUp ? '#00FF41' : '#FF003C'} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#18181b" />
              <XAxis
                dataKey="label"
                tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={{ stroke: '#27272a' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[minPrice, maxPrice]}
                tick={{ fill: '#52525b', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                axisLine={{ stroke: '#27272a' }}
                tickLine={false}
                tickFormatter={v => `$${v.toLocaleString()}`}
                width={90}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="close"
                stroke={isUp ? '#00FF41' : '#FF003C'}
                strokeWidth={2}
                fill="url(#priceGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-full">
            <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
              LOADING CHART DATA...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
