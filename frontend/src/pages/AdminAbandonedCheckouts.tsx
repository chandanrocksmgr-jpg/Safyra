import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, MailCheck, Search, ShoppingBag } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import SafeProductImage from "@/components/SafeProductImage";
import { apiGet, apiPatch } from "@/lib/api";
import type { CheckoutSessionAdmin, CheckoutSessionList, CheckoutSessionStatus, ReminderStatus } from "@/lib/abandonedCheckout";
import { formatPrice } from "@/lib/shop";

const checkoutStatuses: CheckoutSessionStatus[] = ["In progress", "Abandoned", "Completed"];
const reminderStatuses: ReminderStatus[] = ["Not scheduled", "Scheduled", "Sending", "Sent", "Failed"];

function reminderCopy(session: CheckoutSessionAdmin) {
  if (session.reminder_status === "Sent") return `Provider accepted the one permitted recovery email${session.reminder_sent_at ? ` on ${new Date(session.reminder_sent_at).toLocaleString("en-IN")}` : ""}.`;
  if (session.reminder_status === "Failed") return "The single delivery attempt failed. It will not retry automatically, preventing duplicate reminders.";
  if (session.reminder_status === "Scheduled") return "One recovery email is scheduled for two hours after the customer’s last activity.";
  if (session.reminder_status === "Sending") return "The one permitted recovery email is being processed.";
  return session.email ? "No reminder is currently scheduled." : "No email was captured, so no email reminder can be sent.";
}

function CheckoutDetail({ session }: { session: CheckoutSessionAdmin }) {
  const queryClient = useQueryClient();
  const [notes, setNotes] = useState(session.internal_notes);
  const mutation = useMutation({
    mutationFn: () => apiPatch<CheckoutSessionAdmin>(`/checkout-sessions/${session.id}`, { internal_notes: notes }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["admin-abandoned-checkouts"] }); toast.success("Checkout notes updated"); },
    onError: () => toast.error("Checkout notes could not be updated"),
  });
  return <article className="admin-checkout-detail" data-testid="admin-checkout-detail">
    <header className="admin-checkout-detail-header" data-testid="admin-checkout-detail-header">
      <div><span className="eyebrow">Checkout</span><h2 data-testid="admin-checkout-reference">{session.checkout_number}</h2><p data-testid="admin-checkout-last-activity">Last activity {new Date(session.last_activity_at).toLocaleString("en-IN")}</p></div>
      <div className="admin-order-statuses"><span data-testid="admin-checkout-status">{session.status}</span><span data-testid="admin-checkout-reminder-status">Email: {session.reminder_status}</span></div>
    </header>
    <section className="admin-order-section" data-testid="admin-checkout-customer">
      <h3>Customer details</h3>
      <p><strong>{session.name}</strong><br />{session.email || "No email captured"}<br />{session.phone || "No mobile captured"}</p>
      {(session.address || session.city || session.country) && <p>{session.address}<br />{[session.city, session.state_region, session.postal_code].filter(Boolean).join(", ")}<br />{session.country}</p>}
    </section>
    <section className="admin-order-section" data-testid="admin-checkout-items">
      <h3>Checkout items</h3>
      {session.items.map((item) => <div className="admin-order-item" key={`${item.product_id}-${item.set_type}-${item.size}-${item.color}`} data-testid={`admin-checkout-item-${item.product_id}`}><SafeProductImage src={item.image_url} alt={item.title} productName={item.title} /><div><strong>{item.title}</strong><span>{[item.set_type, `Size ${item.size}`, item.color, `Qty ${item.quantity}`].filter(Boolean).join(" · ")}</span></div><strong>{formatPrice(item.line_total)}</strong></div>)}
      {session.discount_total > 0 && <div className="summary-line" data-testid="admin-checkout-discount"><span>Discount</span><strong>−{formatPrice(session.discount_total)}</strong></div>}
      <div className="summary-line" data-testid="admin-checkout-subtotal"><span>Saved product subtotal</span><strong>{formatPrice(session.subtotal)}</strong></div>
    </section>
    <section className="admin-order-section admin-recovery-status" data-testid="admin-checkout-recovery-status">
      <h3>Automatic recovery email</h3>
      <div>{session.reminder_status === "Sent" ? <MailCheck size={22} /> : session.status === "Completed" ? <CheckCircle2 size={22} /> : <Clock3 size={22} />}<p>{reminderCopy(session)}</p></div>
      {session.reminder_email_id && <small data-testid="admin-checkout-email-id">Provider reference: {session.reminder_email_id}</small>}
      <small>Checkout recovery is transactional and separate from marketing preferences. No WhatsApp message is sent automatically.</small>
    </section>
    {session.completed_request_number && <section className="admin-order-section" data-testid="admin-checkout-completed-order"><h3>Completed order request</h3><p>This checkout became <strong>{session.completed_request_number}</strong> and will not receive a recovery email.</p></section>}
    <form className="admin-editor-card" onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }} data-testid="admin-checkout-notes-form"><h3>Internal notes</h3><textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record follow-up context without changing customer consent." data-testid="admin-checkout-notes" /><button className="button button-dark" disabled={mutation.isPending} data-testid="admin-checkout-save-notes">Save notes</button></form>
    <section className="admin-order-section admin-order-history" data-testid="admin-checkout-activity"><h3>Checkout activity</h3>{[...session.activity].reverse().map((event, index) => <div key={`${event.created_at}-${index}`}><span>{new Date(event.created_at).toLocaleString("en-IN")}</span><p>{event.message}</p></div>)}</section>
  </article>;
}

export default function AdminAbandonedCheckouts() {
  const [searchDraft, setSearchDraft] = useState("");
  const [filters, setFilters] = useState({ q: "", status: "", reminder: "" });
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const params = new URLSearchParams({ page: String(page), page_size: "25" });
  if (filters.q) params.set("q", filters.q);
  if (filters.status) params.set("status", filters.status);
  if (filters.reminder) params.set("reminder_status", filters.reminder);
  const { data, isLoading, isError } = useQuery({ queryKey: ["admin-abandoned-checkouts", "list", filters, page], queryFn: () => apiGet<CheckoutSessionList>(`/checkout-sessions?${params}`), retry: false });
  const sessions = data?.items ?? [];
  const activeId = selectedId ?? sessions[0]?.id ?? null;
  const { data: selected } = useQuery({ queryKey: ["admin-abandoned-checkouts", "detail", activeId], queryFn: () => apiGet<CheckoutSessionAdmin>(`/checkout-sessions/${activeId}`), enabled: Boolean(activeId), retry: false });
  const submitSearch = (event: FormEvent) => { event.preventDefault(); setPage(1); setSelectedId(null); setFilters({ ...filters, q: searchDraft.trim() }); };
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / 25));

  return <AdminShell eyebrow="Checkout recovery" title="Abandoned checkouts" description="Review captured checkouts, completion links, and the single transactional recovery email without duplicate reminders.">
    <form className="admin-checkout-toolbar" onSubmit={submitSearch} data-testid="admin-checkout-search-form">
      <label className="admin-search-field"><Search size={15} /><input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Reference, customer, contact or product" data-testid="admin-checkout-search" /></label>
      <select value={filters.status} onChange={(event) => { setFilters({ ...filters, status: event.target.value }); setPage(1); setSelectedId(null); }} data-testid="admin-checkout-status-filter"><option value="">All checkout statuses</option>{checkoutStatuses.map((status) => <option key={status}>{status}</option>)}</select>
      <select value={filters.reminder} onChange={(event) => { setFilters({ ...filters, reminder: event.target.value }); setPage(1); setSelectedId(null); }} data-testid="admin-checkout-reminder-filter"><option value="">All email statuses</option>{reminderStatuses.map((status) => <option key={status}>{status}</option>)}</select>
      <button className="button button-dark" data-testid="admin-checkout-search-submit">Search</button>
    </form>
    <div className="admin-checkout-layout">
      <aside className="admin-checkout-list" data-testid="admin-checkout-list">
        <div className="admin-checkout-list-heading"><span className="eyebrow">Captured checkouts</span><strong data-testid="admin-checkout-count">{data?.total ?? 0}</strong></div>
        {isLoading && <p data-testid="admin-checkout-loading">Loading checkouts…</p>}
        {isError && <div className="form-error" data-testid="admin-checkout-error">Checkouts could not be loaded.</div>}
        {!isLoading && !sessions.length && <div className="admin-waitlist-empty" data-testid="admin-checkout-empty"><ShoppingBag size={24} /><p>No matching checkout sessions.</p></div>}
        {sessions.map((session) => <button key={session.id} className={activeId === session.id ? "admin-checkout-row is-active" : "admin-checkout-row"} onClick={() => setSelectedId(session.id)} data-testid={`admin-checkout-row-${session.id}`}><span><strong>{session.checkout_number}</strong><small>{session.name}</small><small>{session.items.length} item{session.items.length === 1 ? "" : "s"} · {formatPrice(session.subtotal)}</small></span><span><b>{session.status}</b><small>Email: {session.reminder_status}</small></span></button>)}
        {data && data.total > 25 && <div className="admin-pagination" data-testid="admin-checkout-pagination"><button disabled={page === 1} onClick={() => { setPage((current) => current - 1); setSelectedId(null); }} data-testid="admin-checkout-previous">Previous</button><span>Page {page} of {totalPages}</span><button disabled={page >= totalPages} onClick={() => { setPage((current) => current + 1); setSelectedId(null); }} data-testid="admin-checkout-next">Next</button></div>}
      </aside>
      <section>{selected ? <CheckoutDetail key={`${selected.id}-${selected.activity.length}`} session={selected} /> : <div className="admin-waitlist-empty admin-waitlist-placeholder" data-testid="admin-checkout-placeholder"><ShoppingBag size={25} /><p>Select a checkout to review its recovery status.</p></div>}</section>
    </div>
  </AdminShell>;
}