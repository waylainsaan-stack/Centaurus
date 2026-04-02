import React, { useState } from "react";
import { Activity, Power, PowerOff, Bell, TrendingUp } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function TopBar({ botStatus, priceData, refetchStatus, activeSymbol, showAlerts, setShowAlerts, showTrade, setShowTrade, unreadCount, wsConnected }) {
  const [toggling, setToggling] = useState(false);
  const running = botStatus?.running;
  const symbolParam = encodeURIComponent(activeSymbol);

  const toggleBot = async () => {
    setToggling(true);
    try {
      await postApi(running ? `/bot/stop?symbol=${symbolParam}` : `/bot/start?symbol=${symbolParam}`);
      setTimeout(() => { refetchStatus(); setToggling(false); }, 1000);
    } catch { setToggling(false); }
  };

  const price = priceData?.price;
  const change = priceData?.change;
  const isUp = change >= 0;

  return (
    <div data-testid="top-bar" className="flex items-center justify-between px-4 md:px-6 py-3" style={{ background: '#0A0A0A', borderBottom: '1px solid #27272a' }}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div data-testid="bot-status-dot" className="w-2 h-2" style={{ background: running ? '#00FF41' : '#FF003C', animation: running ? 'pulse-dot 1.5s ease-in-out infinite' : 'none' }} />
          <span className="text-xs uppercase tracking-widest" style={{ color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace' }}>
            {running ? 'ACTIVE' : 'INACTIVE'}
          </span>
        </div>
        <span className="font-heading text-lg font-black tracking-tighter uppercase" style={{ color: '#fafafa' }}>CRYPTO AI BOT</span>
        <span className="text-xs uppercase tracking-widest" style={{ color: '#52525b', fontFamily: 'JetBrains Mono, monospace' }}>{activeSymbol}</span>
        {wsConnected && <span className="text-xs font-mono px-1" style={{ color: '#00FF41', background: 'rgba(0,255,65,0.1)' }}>WS</span>}
      </div>

      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-widest" style={{ color: '#52525b' }}>PRICE</span>
          <span data-testid="current-price" className="font-mono text-lg font-bold" style={{ color: '#fafafa' }}>
            {price ? `$${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '---'}
          </span>
          {change !== undefined && change !== null && (
            <span data-testid="price-change" className="text-xs font-mono" style={{ color: isUp ? '#00FF41' : '#FF003C' }}>
              {isUp ? '+' : ''}{change?.toFixed(2)}%
            </span>
          )}
        </div>
        {botStatus?.iterations > 0 && (
          <div className="flex items-center gap-2">
            <Activity size={12} style={{ color: '#52525b' }} />
            <span className="text-xs font-mono" style={{ color: '#52525b' }}>ITER: {botStatus.iterations}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button data-testid="alerts-button" onClick={() => setShowAlerts(!showAlerts)} className="btn-terminal flex items-center gap-2 relative">
          <Bell size={14} />
          ALERTS
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 text-[10px] flex items-center justify-center font-bold" style={{ background: '#FF003C', color: '#fff' }}>{unreadCount}</span>
          )}
        </button>
        <button data-testid="trade-button" onClick={() => setShowTrade(!showTrade)} className="btn-terminal flex items-center gap-2" style={{ borderColor: '#00FF41', color: '#00FF41' }}>
          <TrendingUp size={14} />
          TRADE
        </button>
        <button data-testid="start-stop-bot-button" onClick={toggleBot} disabled={toggling} className="btn-terminal flex items-center gap-2" style={running ? { borderColor: '#FF003C', color: '#FF003C' } : { borderColor: '#00FF41', color: '#00FF41' }}>
          {running ? <PowerOff size={14} /> : <Power size={14} />}
          {toggling ? 'WAIT' : running ? 'STOP' : 'START'}
        </button>
      </div>
    </div>
  );
}
