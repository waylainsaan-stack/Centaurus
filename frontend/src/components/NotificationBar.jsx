import React, { useState } from "react";
import { Bell, X, Check } from "lucide-react";
import { postApi } from "@/hooks/useApi";

export default function NotificationBar({ notifications, unreadCount, refetchNotifs, refetchUnread }) {
  const [expanded, setExpanded] = useState(false);
  const items = notifications?.notifications || [];

  const markRead = async () => {
    await postApi("/notifications/read");
    refetchNotifs();
    refetchUnread();
  };

  if (unreadCount === 0 && !expanded) return null;

  return (
    <>
      {/* Floating notification badge */}
      {unreadCount > 0 && !expanded && (
        <button
          data-testid="notification-badge"
          onClick={() => setExpanded(true)}
          className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-4 py-3 animate-in"
          style={{ background: '#FF003C', color: '#fff', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}
        >
          <Bell size={14} />
          {unreadCount} NEW ALERT{unreadCount > 1 ? 'S' : ''}
        </button>
      )}

      {/* Expanded panel */}
      {expanded && (
        <div className="fixed bottom-0 right-0 z-50 w-full max-w-sm" style={{ maxHeight: '50vh' }}>
          <div style={{ background: '#0A0A0A', border: '1px solid #27272a' }}>
            <div className="flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid #27272a' }}>
              <span className="text-xs font-mono uppercase tracking-widest" style={{ color: '#a1a1aa' }}>NOTIFICATIONS</span>
              <div className="flex gap-2">
                <button data-testid="mark-all-read" onClick={markRead} className="flex items-center gap-1 text-xs font-mono" style={{ color: '#00FF41' }}>
                  <Check size={12} /> CLEAR
                </button>
                <button onClick={() => setExpanded(false)} style={{ color: '#52525b' }}><X size={14} /></button>
              </div>
            </div>
            <div className="overflow-y-auto" style={{ maxHeight: 300 }}>
              {items.length === 0 && (
                <div className="px-4 py-6 text-center text-xs font-mono" style={{ color: '#52525b' }}>No notifications</div>
              )}
              {items.slice(0, 10).map((n, i) => (
                <div
                  key={i}
                  className="px-4 py-2"
                  style={{
                    borderBottom: '1px solid #18181b',
                    background: n.read ? 'transparent' : 'rgba(255,0,60,0.05)',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono" style={{ color: '#52525b' }}>
                      {new Date(n.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span
                      className="text-xs font-mono font-bold"
                      style={{ color: n.type?.includes('buy') || n.type?.includes('above') ? '#00FF41' : '#FF003C' }}
                    >
                      [{n.type?.toUpperCase()}]
                    </span>
                  </div>
                  <div className="text-xs font-mono mt-1" style={{ color: '#a1a1aa' }}>{n.message}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
