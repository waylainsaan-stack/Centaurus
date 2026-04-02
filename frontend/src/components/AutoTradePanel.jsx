import React, { useState } from "react";
import { Bot, Power, PowerOff, Settings } from "lucide-react";
import { postApi, useApi } from "@/hooks/useApi";

export default function AutoTradePanel({ symbol, onClose }) {
  const [saving, setSaving] = useState(false);
  const sp = encodeURIComponent(symbol);
  const { data: status, refetch } = useApi(`/auto-trade/status?symbol=${sp}`, 5000);

  const enabled = status?.enabled || false;
  const settings = status?.settings || {};
  const recentTrades = status?.recent_auto_trades || [];

  const [form, setForm] = useState({
    max_position_size: settings.max_position_size || 0.001,
    stop_loss_pct: settings.stop_loss_pct || 2.0,
    take_profit_pct: settings.take_profit_pct || 5.0,
    min_confidence: settings.min_confidence || 30,
    cooldown_minutes: settings.cooldown_minutes || 5,
  });

  // Update form when settings load
  React.useEffect(() => {
    if (settings.max_position_size) {
      setForm({
        max_position_size: settings.max_position_size || 0.001,
        stop_loss_pct: settings.stop_loss_pct || 2.0,
        take_profit_pct: settings.take_profit_pct || 5.0,
        min_confidence: settings.min_confidence || 30,
        cooldown_minutes: settings.cooldown_minutes || 5,
      });
    }
  }, [settings.max_position_size, settings.stop_loss_pct, settings.take_profit_pct, settings.min_confidence, settings.cooldown_minutes]);

  const toggle = async () => {
    await postApi(enabled ? `/auto-trade/disable?symbol=${sp}` : `/auto-trade/enable?symbol=${sp}`);
    refetch();
  };

  const saveSettings = async () => {
    setSaving(true);
    const params = new URLSearchParams({ symbol, ...Object.fromEntries(Object.entries(form).map(([k, v]) => [k, String(v)])) });
    await postApi(`/auto-trade/settings?${params.toString()}`);
    setSaving(false);
    refetch();
  };

  return (
    <div data-testid="auto-trade-panel" className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.7)' }}>
      <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto" style={{ background: '#0A0A0A', border: '1px solid #27272a' }}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid #27272a' }}>
          <h2 className="font-heading text-lg font-bold uppercase tracking-tight flex items-center gap-2" style={{ color: '#fafafa' }}>
            <Bot size={18} /> AUTO-TRADE {symbol.split('/')[0]}
          </h2>
          <button data-testid="close-auto-trade" onClick={onClose} className="btn-terminal text-xs">CLOSE</button>
        </div>

        <div className="p-4 space-y-4">
          {/* Enable/Disable toggle */}
          <div className="flex items-center justify-between p-4" style={{ background: enabled ? 'rgba(0,255,65,0.05)' : '#000', border: `1px solid ${enabled ? '#00FF41' : '#27272a'}` }}>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3" style={{ background: enabled ? '#00FF41' : '#FF003C', animation: enabled ? 'pulse-dot 1.5s ease-in-out infinite' : 'none' }} />
              <div>
                <div className="text-sm font-mono font-bold uppercase" style={{ color: enabled ? '#00FF41' : '#FF003C' }}>
                  {enabled ? 'AUTO-TRADE ACTIVE' : 'AUTO-TRADE OFF'}
                </div>
                <div className="text-xs font-mono" style={{ color: '#52525b' }}>
                  {enabled ? 'Bot will execute trades on STRONG signals' : 'Enable to let bot trade automatically'}
                </div>
              </div>
            </div>
            <button data-testid="toggle-auto-trade" onClick={toggle} className="btn-terminal flex items-center gap-2"
              style={enabled ? { borderColor: '#FF003C', color: '#FF003C' } : { borderColor: '#00FF41', color: '#00FF41' }}>
              {enabled ? <PowerOff size={14} /> : <Power size={14} />}
              {enabled ? 'DISABLE' : 'ENABLE'}
            </button>
          </div>

          {/* Warning */}
          <div className="p-3 text-xs font-mono" style={{ background: 'rgba(253,224,71,0.1)', border: '1px solid #FDE047', color: '#FDE047' }}>
            WARNING: Auto-trade executes real trades (SIMULATED on this server). Only enable after validating strategy with backtesting.
          </div>

          {/* Settings */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Settings size={14} style={{ color: '#a1a1aa' }} />
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#a1a1aa' }}>SETTINGS</span>
            </div>
            <div className="space-y-3">
              {[
                { key: 'max_position_size', label: 'POSITION SIZE', placeholder: '0.001', suffix: symbol.split('/')[0] },
                { key: 'stop_loss_pct', label: 'STOP LOSS', placeholder: '2.0', suffix: '%' },
                { key: 'take_profit_pct', label: 'TAKE PROFIT', placeholder: '5.0', suffix: '%' },
                { key: 'min_confidence', label: 'MIN CONFIDENCE', placeholder: '30', suffix: '%' },
                { key: 'cooldown_minutes', label: 'COOLDOWN', placeholder: '5', suffix: 'MIN' },
              ].map(({ key, label, placeholder, suffix }) => (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>{label}</span>
                  <div className="flex items-center gap-1">
                    <input type="number" value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) || 0 }))}
                      placeholder={placeholder} className="w-24 p-2 text-xs font-mono text-right"
                      style={{ background: '#000', border: '1px solid #27272a', color: '#fafafa', outline: 'none' }} />
                    <span className="text-xs font-mono" style={{ color: '#52525b' }}>{suffix}</span>
                  </div>
                </div>
              ))}
            </div>
            <button data-testid="save-auto-settings" onClick={saveSettings} disabled={saving}
              className="w-full mt-3 py-2 text-xs font-mono font-bold uppercase tracking-widest" style={{ background: '#fafafa', color: '#000', opacity: saving ? 0.4 : 1 }}>
              {saving ? 'SAVING...' : 'SAVE SETTINGS'}
            </button>
          </div>

          {/* Recent auto-trades */}
          {recentTrades.length > 0 && (
            <div>
              <div className="text-xs font-mono uppercase tracking-widest mb-2" style={{ color: '#52525b' }}>RECENT AUTO-TRADES</div>
              {recentTrades.map((t, i) => (
                <div key={i} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid #18181b' }}>
                  <div>
                    <span className="text-xs font-mono font-bold" style={{ color: t.side === 'BUY' ? '#00FF41' : '#FF003C' }}>{t.side}</span>
                    <span className="text-xs font-mono ml-2" style={{ color: '#a1a1aa' }}>{t.amount} @ ${t.price?.toLocaleString()}</span>
                  </div>
                  <div className="text-xs font-mono" style={{ color: '#52525b' }}>
                    {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
