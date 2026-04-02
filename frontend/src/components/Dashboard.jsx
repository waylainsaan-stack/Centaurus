import React, { useState } from "react";
import TopBar from "./TopBar";
import PairSelector from "./PairSelector";
import PriceChart from "./PriceChart";
import SignalDisplay from "./SignalDisplay";
import IndicatorPanel from "./IndicatorPanel";
import OrderBook from "./OrderBook";
import AITerminal from "./AITerminal";
import TradeHistory from "./TradeHistory";
import TradePanel from "./TradePanel";
import AlertPanel from "./AlertPanel";
import NotificationBar from "./NotificationBar";
import MultiPairTicker from "./MultiPairTicker";
import { useApi } from "@/hooks/useApi";

export default function Dashboard() {
  const [activeSymbol, setActiveSymbol] = useState("BTC/USDT");
  const [showAlerts, setShowAlerts] = useState(false);
  const [showTrade, setShowTrade] = useState(false);

  const symbolParam = encodeURIComponent(activeSymbol);

  const { data: botStatus, refetch: refetchStatus } = useApi(`/bot/status?symbol=${symbolParam}`, 5000);
  const { data: currentSignal } = useApi(`/signals/current?symbol=${symbolParam}`, 5000);
  const { data: priceData } = useApi(`/market/price?symbol=${symbolParam}`, 10000);
  const { data: ohlcvData } = useApi(`/market/ohlcv?symbol=${symbolParam}&limit=100`, 30000);
  const { data: orderbookData } = useApi(`/market/orderbook?symbol=${symbolParam}`, 8000);
  const { data: indicatorData } = useApi(`/market/indicators?symbol=${symbolParam}`, 15000);
  const { data: signalHistory } = useApi(`/signals/history?symbol=${symbolParam}&limit=30`, 10000);
  const { data: aiInsights } = useApi(`/ai/insights?symbol=${symbolParam}&limit=10`, 15000);
  const { data: tradeHistory, refetch: refetchTrades } = useApi(`/trades/history?symbol=${symbolParam}&limit=20`, 10000);
  const { data: notifications, refetch: refetchNotifs } = useApi("/notifications?limit=20", 8000);
  const { data: unreadCount, refetch: refetchUnread } = useApi("/notifications/unread", 5000);
  const { data: allPrices } = useApi("/market/prices", 15000);

  return (
    <div data-testid="dashboard-container" className="min-h-screen" style={{ background: '#050505' }}>
      {/* Notification bar */}
      <NotificationBar
        notifications={notifications}
        unreadCount={unreadCount?.unread || 0}
        refetchNotifs={refetchNotifs}
        refetchUnread={refetchUnread}
      />

      {/* Top Bar */}
      <TopBar
        botStatus={botStatus}
        priceData={priceData}
        refetchStatus={refetchStatus}
        activeSymbol={activeSymbol}
        showAlerts={showAlerts}
        setShowAlerts={setShowAlerts}
        showTrade={showTrade}
        setShowTrade={setShowTrade}
        unreadCount={unreadCount?.unread || 0}
      />

      {/* Multi-pair ticker strip */}
      <MultiPairTicker
        prices={allPrices?.prices}
        activeSymbol={activeSymbol}
        onSelect={setActiveSymbol}
      />

      {/* Modals */}
      {showAlerts && (
        <AlertPanel symbol={activeSymbol} onClose={() => setShowAlerts(false)} />
      )}
      {showTrade && (
        <TradePanel
          symbol={activeSymbol}
          priceData={priceData}
          onClose={() => setShowTrade(false)}
          refetchTrades={refetchTrades}
        />
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        <div className="lg:col-span-2 border-b border-r" style={{ borderColor: '#27272a' }}>
          <PriceChart ohlcvData={ohlcvData} priceData={priceData} />
        </div>
        <div className="border-b" style={{ borderColor: '#27272a' }}>
          <SignalDisplay currentSignal={currentSignal} botStatus={botStatus} />
          <div style={{ borderTop: '1px solid #27272a' }}>
            <IndicatorPanel indicators={indicatorData} currentSignal={currentSignal} />
          </div>
        </div>
      </div>

      {/* Middle Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        <div className="border-b border-r" style={{ borderColor: '#27272a' }}>
          <OrderBook data={orderbookData} />
        </div>
        <div className="lg:col-span-2 border-b" style={{ borderColor: '#27272a' }}>
          <AITerminal insights={aiInsights} currentSignal={currentSignal} symbol={activeSymbol} />
        </div>
      </div>

      {/* Trade History + Signal Log */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
        <div className="border-r" style={{ borderColor: '#27272a' }}>
          <TradeHistory signals={signalHistory} title="SIGNAL LOG" />
        </div>
        <div>
          <TradeLog trades={tradeHistory} />
        </div>
      </div>
    </div>
  );
}

function TradeLog({ trades }) {
  const rows = trades?.trades || [];
  return (
    <div data-testid="trade-log" className="p-4 md:p-6" style={{ background: '#0A0A0A' }}>
      <h3 className="font-heading text-base font-bold uppercase tracking-widest mb-4" style={{ color: '#a1a1aa' }}>
        TRADE LOG
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #27272a' }}>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>TIME</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>SIDE</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>AMT</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>PRICE</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>SL</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>TP</th>
              <th className="text-left px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>STATUS</th>
              <th className="text-right px-3 py-2 uppercase tracking-widest" style={{ color: '#52525b' }}>PNL</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={8} className="px-3 py-8 text-center" style={{ color: '#52525b' }}>No trades yet. Use TRADE to execute.</td></tr>
            )}
            {rows.map((t, i) => (
              <tr key={i} className="table-row" style={{ borderBottom: '1px solid #18181b' }}>
                <td className="px-3 py-2" style={{ color: '#52525b' }}>{new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                <td className="px-3 py-2 font-bold" style={{ color: t.side === 'BUY' ? '#00FF41' : '#FF003C' }}>{t.side}</td>
                <td className="px-3 py-2 text-right" style={{ color: '#fafafa' }}>{t.amount}</td>
                <td className="px-3 py-2 text-right" style={{ color: '#fafafa' }}>${t.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td className="px-3 py-2 text-right" style={{ color: '#FF003C' }}>{t.stop_loss ? `$${t.stop_loss.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '---'}</td>
                <td className="px-3 py-2 text-right" style={{ color: '#00FF41' }}>{t.take_profit ? `$${t.take_profit.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '---'}</td>
                <td className="px-3 py-2" style={{ color: t.status === 'FILLED' ? '#00FF41' : t.status === 'CLOSED' ? '#a1a1aa' : '#FDE047' }}>{t.status}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: t.pnl > 0 ? '#00FF41' : t.pnl < 0 ? '#FF003C' : '#52525b' }}>
                  {t.pnl !== null ? `$${t.pnl.toFixed(2)}` : '---'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
