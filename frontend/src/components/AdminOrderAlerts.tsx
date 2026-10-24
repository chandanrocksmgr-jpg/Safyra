import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, BellOff, X } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import { formatPrice } from "@/lib/shop";
import type { AdminOrderAlert, AdminOrderAlertList } from "@/lib/adminAlerts";

const MUTE_KEY = "safyra-order-alert-muted";

/** Soft chime first, then a louder repeating alert until the admin opens or dismisses the order. */
function useAlertSound(active: boolean, muted: boolean) {
  const contextRef = useRef<AudioContext | null>(null);
  const roundRef = useRef(0);

  useEffect(() => {
    if (!active || muted) { roundRef.current = 0; return; }
    const play = (round: number) => {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return;
      const context = contextRef.current ?? new Ctor();
      contextRef.current = context;
      void context.resume();
      const soft = round === 0;
      const notes = soft ? [880, 1174] : [988, 1318, 988];
      notes.forEach((frequency, index) => {
        const oscillator = context.createOscillator();
        const gain = context.createGain();
        oscillator.type = soft ? "sine" : "triangle";
        oscillator.frequency.value = frequency;
        const start = context.currentTime + index * (soft ? 0.22 : 0.18);
        const peak = soft ? 0.12 : Math.min(0.42, 0.2 + round * 0.06);
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(peak, start + 0.04);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + (soft ? 0.5 : 0.36));
        oscillator.connect(gain).connect(context.destination);
        oscillator.start(start);
        oscillator.stop(start + (soft ? 0.55 : 0.4));
      });
    };
    play(roundRef.current);
    const timer = window.setInterval(() => { roundRef.current += 1; play(roundRef.current); }, 9000);
    return () => window.clearInterval(timer);
  }, [active, muted]);
}

export default function AdminOrderAlerts() {
  const queryClient = useQueryClient();
  const [muted, setMuted] = useState(() => window.localStorage.getItem(MUTE_KEY) === "1");
  const { data } = useQuery<AdminOrderAlertList>({
    queryKey: ["admin-order-alerts"],
    queryFn: () => apiGet<AdminOrderAlertList>("/admin/order-alerts"),
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });
  const alerts = useMemo<AdminOrderAlert[]>(() => data?.alerts ?? [], [data]);
  useAlertSound(alerts.length > 0, muted);

  const acknowledge = useMutation({
    mutationFn: (alertIds: string[]) => apiPost<{ acknowledged: number }>("/admin/order-alerts/ack", { alert_ids: alertIds }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["admin-order-alerts"] }); },
  });

  const toggleMute = () => {
    setMuted((current) => { window.localStorage.setItem(MUTE_KEY, current ? "0" : "1"); return !current; });
  };

  if (!alerts.length) return null;
  return <aside className="order-alert-stack" role="alert" aria-live="assertive" data-testid="admin-order-alert-banner">
    <div className="order-alert-head">
      <span className="order-alert-title"><BellRing size={16} /> {alerts.length === 1 ? "New paid order" : `${alerts.length} new paid orders`}</span>
      <div className="order-alert-tools">
        <button type="button" onClick={toggleMute} title={muted ? "Unmute alert sound" : "Mute alert sound"} data-testid="admin-order-alert-mute">{muted ? <BellOff size={15} /> : <BellRing size={15} />}</button>
        <button type="button" onClick={() => acknowledge.mutate([])} title="Dismiss all" data-testid="admin-order-alert-dismiss-all"><X size={15} /></button>
      </div>
    </div>
    <ul>
      {alerts.map((alert) => <li key={alert.id} data-testid={`admin-order-alert-${alert.request_number}`}>
        <div>
          <strong>{alert.request_number}</strong>
          <span>{alert.customer_name} · {alert.item_count} {alert.item_count === 1 ? "piece" : "pieces"} · {formatPrice(alert.total)}</span>
        </div>
        <div className="order-alert-actions">
          <Link to="/admin/orders" onClick={() => acknowledge.mutate([alert.id])} data-testid={`admin-order-alert-open-${alert.request_number}`}>Open</Link>
          <button type="button" onClick={() => acknowledge.mutate([alert.id])} data-testid={`admin-order-alert-dismiss-${alert.request_number}`}>Dismiss</button>
        </div>
      </li>)}
    </ul>
    {muted && <p className="order-alert-muted-note" data-testid="admin-order-alert-muted-note">Sound muted on this device. Alerts still appear here and by email.</p>}
  </aside>;
}
