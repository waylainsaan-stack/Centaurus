import React, { useState, useEffect } from "react";
import { X, Plus, Trash2, Bell } from "lucide-react";
import { postApi, deleteApi, useApi } from "@/hooks/useApi";

export default function AlertPanel({ symbol, onClose }) {
  const [alertType, setAlertType] = useState("price_above");
  const [alertValue, setAlertValue] = useState("");
  const [creating, setCreating] = useState(false);

  const symbolParam = encodeURIComponent(symbol);
  const { data: alertsData, refetch: refetchAlerts } = useApi(`/alerts?symbol=${symbolParam}`, 5000);
  const alerts = alertsData?.alerts || [];

  const createAlert = async () => {
    if (!alertType) return;
    setCreating(true);
    try {
      await postApi("/alerts/create", {
        symbol,
        type: alertType,
        value: alertValue ? parseFloat(alertValue) : null,
        enabled: true,
      });
      refetchAlerts();
      setAlertValue("");
    } catch (e) {
      console.error(e);
    } finally {
      setCreating(false);
    }
  };

  const removeAlert = async (id) => {
    await deleteApi(`/alerts/${id}`);
    refetchAlerts();
  };

  const alertTypes = [
    { value: "price_above", label: "PRICE ABOVE", needsValue: true },
    { value: "price_below", label: "PRICE BELOW", needsValue: true },
    { value: "signal_strong_buy", label: "STRONG BUY SIGNAL", needsValue: false },
    { value: "signal_strong_sell", label: "STRONG SELL SIGNAL", needsValue: false },
  ];

  const selectedType = alertTypes.find(t => t.value === alertType);

  return (
    <div data-testid="alert-panel" className="fixed inset-0 z-50 flex items-start justify-end" style={{ background: 'rgba(0,0,0,0.6)' }}>
      <div className="w-full max-w-md h-full overflow-y-auto" style={{ background: '#0A0A0A', borderLeft: '1px solid #27272a' }}>
        <div className="flex items-center justify-between p-4" style={{ borderBottom: '1px solid #27272a' }}>
          <h2 className="font-heading text-lg font-bold uppercase tracking-tight flex items-center gap-2" style={{ color: '#fafafa' }}>
            <Bell size={16} /> ALERTS
          </h2>
          <button data-testid="close-alert-panel" onClick={onClose} className="btn-terminal p-2"><X size={16} /></button>
        </div>

        <div className="p-4 space-y-4">
          <div className="text-xs font-mono uppercase tracking-widest" style={{ color: '#52525b' }}>
            CREATE ALERT FOR {symbol}
          </div>

          {/* Alert type selector */}
          <div className="grid grid-cols-2 gap-1">
            {alertTypes.map(t => (
              <button
                key={t.value}
                data-testid={`alert-type-${t.value}`}
                onClick={() => setAlertType(t.value)}
                className="py-2 px-2 text-xs font-mono uppercase tracking-widest transition-colors duration-75"
                style={{
                  background: alertType === t.value ? '#18181b' : 'transparent',
                  border: '1px solid',
                  borderColor: alertType === t.value ? '#fafafa' : '#27272a',
                  color: alertType === t.value ? '#fafafa' : '#52525b',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Value input for price alerts */}
          {selectedType?.needsValue && (
            <div>
              <label className="text-xs font-mono uppercase tracking-widest block mb-1" style={{ color: '#52525b' }}>
                PRICE (USDT)
              </label>
              <input
                data-testid="alert-value-input"
                type="number"
                value={alertValue}
                onChange={e => setAlertValue(e.target.value)}
                placeholder="e.g. 70000"
                className="w-full p-3 text-sm font-mono"
                style={{ background: '#000', border: '1px solid #27272a', color: '#fafafa', outline: 'none' }}
              />
            </div>
          )}

          <button
            data-testid="create-alert-button"
            onClick={createAlert}
            disabled={creating || (selectedType?.needsValue && !alertValue)}
            className="w-full py-3 text-xs font-mono font-bold uppercase tracking-widest flex items-center justify-center gap-2 transition-colors duration-75"
            style={{
              background: '#fafafa',
              color: '#000',
              opacity: creating || (selectedType?.needsValue && !alertValue) ? 0.4 : 1,
              cursor: creating ? 'not-allowed' : 'pointer',
            }}
          >
            <Plus size={14} /> {creating ? 'CREATING...' : 'ADD ALERT'}
          </button>

          {/* Active alerts */}
          <div style={{ borderTop: '1px solid #27272a', paddingTop: 16 }}>
            <div className="text-xs font-mono uppercase tracking-widest mb-3" style={{ color: '#52525b' }}>
              ACTIVE ALERTS ({alerts.filter(a => a.enabled).length})
            </div>

            {alerts.length === 0 && (
              <div className="text-xs font-mono py-4 text-center" style={{ color: '#52525b' }}>
                No alerts configured.
              </div>
            )}

            {alerts.map((alert, i) => {
              const typeInfo = alertTypes.find(t => t.value === alert.type);
              return (
                <div
                  key={alert.id || i}
                  className="flex items-center justify-between py-2 px-3 mb-1"
                  style={{
                    background: alert.enabled ? '#18181b' : '#0A0A0A',
                    border: '1px solid #27272a',
                    opacity: alert.enabled ? 1 : 0.5,
                  }}
                >
                  <div>
                    <div className="text-xs font-mono font-bold uppercase" style={{ color: alert.type.includes('buy') || alert.type.includes('above') ? '#00FF41' : '#FF003C' }}>
                      {typeInfo?.label || alert.type}
                    </div>
                    {alert.value && (
                      <div className="text-xs font-mono" style={{ color: '#a1a1aa' }}>
                        ${alert.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono" style={{ color: alert.enabled ? '#00FF41' : '#52525b' }}>
                      {alert.enabled ? 'ON' : 'OFF'}
                    </span>
                    <button
                      data-testid={`delete-alert-${i}`}
                      onClick={() => removeAlert(alert.id)}
                      className="p-1 transition-colors duration-75"
                      style={{ color: '#52525b' }}
                      onMouseEnter={e => e.target.style.color = '#FF003C'}
                      onMouseLeave={e => e.target.style.color = '#52525b'}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
