import React, { useState } from "react";
import { Activity, Power, PowerOff, AlertTriangle } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function TopBar({ botStatus, priceData, refetchStatus }) {
  const [toggling, setToggling] = useState(false);
  const running = botStatus?.running;

  const toggleBot = async () => {
    setToggling(true);
    try {
      await postApi(running ? "/bot/stop" : "/bot/start");
      setTimeout(() => {
        refetchStatus();
        setToggling(false);
      }, 1000);
    } catch {
      setToggling(false);
    }
  };

  const price = priceData?.price;
  const change = priceData?.change;
  const isUp = change >= 0;

  return (
    <div
      data-testid="top-bar"
      className="flex items-center justify-between px-4 md:px-6 py-3"
      style={{ background: '#0A0A0A', borderBottom: '1px solid #27272a' }}
    >
      {/* Left: Bot identity */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div
            data-testid="bot-status-dot"
            className="w-2 h-2"
            style={{
              background: running ? '#00FF41' : '#FF003C',
              animation: running ? 'pulse-dot 1.5s ease-in-out infinite' : 'none',
            }}
          />
          <span className="text-xs uppercase tracking-widest" style={{ color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace' }}>
            STATUS: {running ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </div>
        <span className="font-heading text-lg font-black tracking-tighter uppercase" style={{ color: '#fafafa' }}>
          CRYPTO AI BOT
        </span>
        <span className="text-xs uppercase tracking-widest" style={{ color: '#52525b', fontFamily: 'JetBrains Mono, monospace' }}>
          {botStatus?.symbol || 'BTC/USDT'}
        </span>
      </div>

      {/* Center: Price */}
      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-widest" style={{ color: '#52525b' }}>PRICE</span>
          <span
            data-testid="current-price"
            className="font-mono text-lg font-bold"
            style={{ color: '#fafafa' }}
          >
            {price ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '---'}
          </span>
          {change !== undefined && change !== null && (
            <span
              data-testid="price-change"
              className="text-xs font-mono"
              style={{ color: isUp ? '#00FF41' : '#FF003C' }}
            >
              {isUp ? '+' : ''}{change?.toFixed(2)}%
            </span>
          )}
        </div>
        {botStatus?.iterations > 0 && (
          <div className="flex items-center gap-2">
            <Activity size={12} style={{ color: '#52525b' }} />
            <span className="text-xs font-mono" style={{ color: '#52525b' }}>
              ITER: {botStatus.iterations}
            </span>
          </div>
        )}
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-3">
        <button
          data-testid="start-stop-bot-button"
          onClick={toggleBot}
          disabled={toggling}
          className="btn-terminal flex items-center gap-2"
          style={running ? { borderColor: '#FF003C', color: '#FF003C' } : { borderColor: '#00FF41', color: '#00FF41' }}
        >
          {running ? <PowerOff size={14} /> : <Power size={14} />}
          {toggling ? 'WAIT' : running ? 'STOP' : 'START'}
        </button>
      </div>
    </div>
  );
}
