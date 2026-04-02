import React, { useState, useCallback } from "react";
import TopBar from "./TopBar";
import PriceChart from "./PriceChart";
import SignalDisplay from "./SignalDisplay";
import IndicatorPanel from "./IndicatorPanel";
import OrderBook from "./OrderBook";
import AITerminal from "./AITerminal";
import TradeHistory from "./TradeHistory";
import { useApi } from "@/hooks/useApi";

export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  const triggerRefresh = useCallback(() => setRefreshKey(k => k + 1), []);

  const { data: botStatus, refetch: refetchStatus } = useApi("/bot/status", 5000);
  const { data: currentSignal } = useApi("/signals/current", 5000);
  const { data: priceData } = useApi("/market/price", 10000);
  const { data: ohlcvData } = useApi("/market/ohlcv?limit=100", 30000);
  const { data: orderbookData } = useApi("/market/orderbook", 8000);
  const { data: indicatorData } = useApi("/market/indicators", 15000);
  const { data: signalHistory } = useApi("/signals/history?limit=30", 10000);
  const { data: aiInsights } = useApi("/ai/insights?limit=10", 15000);

  return (
    <div data-testid="dashboard-container" className="min-h-screen" style={{ background: '#050505' }}>
      {/* Top Bar */}
      <TopBar
        botStatus={botStatus}
        priceData={priceData}
        refetchStatus={refetchStatus}
        triggerRefresh={triggerRefresh}
      />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 lg:gap-0">
        {/* Price Chart - 2 cols */}
        <div className="lg:col-span-2 border-b border-r" style={{ borderColor: '#27272a' }}>
          <PriceChart ohlcvData={ohlcvData} priceData={priceData} />
        </div>

        {/* Signal + Indicators - 1 col */}
        <div className="border-b" style={{ borderColor: '#27272a' }}>
          <SignalDisplay currentSignal={currentSignal} botStatus={botStatus} />
          <div style={{ borderTop: '1px solid #27272a' }}>
            <IndicatorPanel indicators={indicatorData} currentSignal={currentSignal} />
          </div>
        </div>
      </div>

      {/* Middle Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        {/* Order Book - 1 col */}
        <div className="border-b border-r" style={{ borderColor: '#27272a' }}>
          <OrderBook data={orderbookData} />
        </div>

        {/* AI Terminal - 2 cols */}
        <div className="lg:col-span-2 border-b" style={{ borderColor: '#27272a' }}>
          <AITerminal insights={aiInsights} currentSignal={currentSignal} />
        </div>
      </div>

      {/* Bottom: Trade History */}
      <TradeHistory signals={signalHistory} />
    </div>
  );
}
