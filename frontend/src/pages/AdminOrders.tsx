import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, ExternalLink, FileText, LogOut, PackageCheck, PackageOpen, Search, ShieldCheck, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "@/components/AuthProvider";
import SafeProductImage from "@/components/SafeProductImage";
import { apiGet, apiPatch, apiPost, ApiError } from "@/lib/api";
import type { AdminOrderRequest, AdminOrderRequestUpdate, FulfilmentStatus, OrderConversionResponse, PaymentStatus, RefundStatus } from "@/lib/checkout";
import { endSession } from "@/lib/session";
import { formatPrice } from "@/lib/shop";
import { openOrderPrintView } from "@/lib/orderPrint";

const paymentStatuses: PaymentStatus[] = ["Unpaid", "Payment pending", "Paid"];
const fulfilmentStatuses: FulfilmentStatus[] = ["Request received", "Confirmed", "Processing", "Ready to ship", "Shipped", "Delivered"];
const refundStatuses: RefundStatus[] = ["Not initiated", "Processing", "Refunded", "Failed"];

interface ManagementForm {
  payment_status: PaymentStatus;
  fulfilment_status: FulfilmentStatus;
  courier_name: string;
  shipping_details: string;
  tracking_number: string;
  tracking_link: string;
  internal_notes: string;
  refund_status: RefundStatus;
  refund_reason: string;
  refund_amount: string;
  refund_reference: string;
}

const formFromRequest = (request: AdminOrderRequest): ManagementForm => ({
  payment_status: request.payment_status,
  fulfilment_status: request.fulfilment_status,
  courier_name: request.courier_name,
  shipping_details: request.shipping_details,
  tracking_number: request.tracking_number,
  tracking_link: request.tracking_link,
  internal_notes: request.internal_notes,
  refund_status: request.refund_status,
  refund_reason: request.refund_reason,
  refund_amount: request.refund_amount ? String(request.refund_amount) : "",
  refund_reference: request.refund_reference,
});

const errorMessage = (reason: unknown) => reason instanceof ApiError ? reason.message : "The order request could not be updated.";

function whatsappMessage(request: AdminOrderRequest) {
  if (request.cancelled) return `Hi ${request.name}, SAFYRA order ${request.request_number} has been cancelled. Reason: ${request.cancellation_reason}. Please contact us if you need assistance.`;
  if (request.refund_status === "Refunded") return `Hi ${request.name}, your refund for SAFYRA order ${request.request_number} has been confirmed for ${formatPrice(request.refund_amount)}.${request.refund_reference ? ` Refund reference: ${request.refund_reference}.` : ""}`;
  if (request.refund_status === "Processing") return `Hi ${request.name}, the refund for SAFYRA order ${request.request_number} is being processed. We will confirm once it is complete.`;
  if (request.tracking_number) return `Hi ${request.name}, SAFYRA order ${request.request_number} is ${request.fulfilment_status.toLowerCase()}. Courier: ${request.courier_name || "to be confirmed"}. Tracking: ${request.tracking_number}.${request.tracking_link ? ` ${request.tracking_link}` : ""}`;
  return `Hi ${request.name}, an update for SAFYRA order ${request.request_number}: payment is ${request.payment_status.toLowerCase()} and fulfilment is ${request.fulfilment_status.toLowerCase()}.`;
}

function OrderEditor({ request }: { request: AdminOrderRequest }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ManagementForm>(() => formFromRequest(request));
  const [paymentVerified, setPaymentVerified] = useState(false);
  const [refundConfirmed, setRefundConfirmed] = useState(false);
  const [cancellationReason, setCancellationReason] = useState("");
  const [error, setError] = useState("");

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin-order-requests"] }),
      queryClient.invalidateQueries({ queryKey: ["admin-order-request", request.id] }),
    ]);
  };
  const updateMutation = useMutation({
    mutationFn: (payload: AdminOrderRequestUpdate) => apiPatch<AdminOrderRequest>(`/order-requests/${request.id}`, payload),
    onSuccess: async () => { setError(""); setPaymentVerified(false); setRefundConfirmed(false); await refresh(); toast.success("Order request updated"); },
    onError: (reason) => setError(errorMessage(reason)),
  });
  const cancelMutation = useMutation({
    mutationFn: () => apiPost<AdminOrderRequest>(`/order-requests/${request.id}/cancel`, { reason: cancellationReason }),
    onSuccess: async () => { setError(""); setCancellationReason(""); await refresh(); toast.success("Order cancelled internally"); },
    onError: (reason) => setError(errorMessage(reason)),
  });
  const convertMutation = useMutation({
    mutationFn: () => apiPost<OrderConversionResponse>(`/order-requests/${request.id}/convert`, {}),
    onSuccess: async () => { setError(""); await refresh(); toast.success("Order created without duplication"); },
    onError: (reason) => setError(errorMessage(reason)),
  });

  const save = (event: FormEvent) => {
    event.preventDefault();
    updateMutation.mutate({
      ...form,
      refund_amount: form.refund_amount ? Number(form.refund_amount) : 0,
      payment_verified: paymentVerified,
      refund_confirmed: refundConfirmed,
    });
  };
  const notification = whatsappMessage(request);
  const whatsapp = `https://wa.me/${request.phone.replace(/\D/g, "")}?text=${encodeURIComponent(notification)}`;
  const canConvert = request.payment_status === "Paid" && request.fulfilment_status !== "Request received" && !request.cancelled;

  return <div className="admin-order-detail" data-testid="admin-order-detail">
    <header className="admin-order-detail-heading">
      <div><span className="eyebrow">Order request</span><h2>{request.request_number}</h2><p>{new Date(request.received_at).toLocaleString("en-IN")}</p></div>
      <div className="admin-order-statuses"><span>{request.payment_status}</span><span>{request.cancelled ? "Cancelled" : request.fulfilment_status}</span>{request.converted_order_id && <span>Order created</span>}</div>
    </header>

    <section className="admin-order-section" data-testid="admin-order-customer">
      <h3>Customer & delivery</h3>
      <p><strong>{request.name}</strong><br />{request.email}<br />{request.phone}</p>
      <p>{request.address}<br />{request.city}, {request.state_region} {request.postal_code}<br />{request.country}</p>
      {request.note && <p><strong>Customer note</strong><br />{request.note}</p>}
    </section>

    <section className="admin-order-section" data-testid="admin-order-items">
      <h3>Selected products</h3>
      {request.items.map((item) => <div className="admin-order-item" key={`${item.product_id}-${item.size}-${item.color}`}><SafeProductImage src={item.image_url} alt={item.title} productName={item.title} /><div><strong>{item.title}</strong><span>{item.size} · {item.color} · Qty {item.quantity}</span></div><strong>{formatPrice(item.line_total)}</strong></div>)}
      <div className="summary-line"><span>Product subtotal</span><strong>{formatPrice(request.subtotal)}</strong></div>
    </section>

    <form className="admin-order-management" onSubmit={save} data-testid="admin-order-management-form">
      <h3>Payment & fulfilment</h3>
      <label>Payment status<select value={form.payment_status} onChange={(event) => setForm({ ...form, payment_status: event.target.value as PaymentStatus })} disabled={request.cancelled} data-testid="admin-order-payment-status">{paymentStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>
      {form.payment_status === "Paid" && request.payment_status !== "Paid" && <label className="admin-confirmation"><input type="checkbox" checked={paymentVerified} onChange={(event) => setPaymentVerified(event.target.checked)} data-testid="admin-order-payment-verified" />I have independently verified that payment was received.</label>}
      <label>Fulfilment status<select value={form.fulfilment_status} onChange={(event) => setForm({ ...form, fulfilment_status: event.target.value as FulfilmentStatus })} disabled={request.cancelled} data-testid="admin-order-fulfilment-status">{fulfilmentStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>

      <h3>Shipping & internal details</h3>
      <label>Courier name<input value={form.courier_name} onChange={(event) => setForm({ ...form, courier_name: event.target.value })} data-testid="admin-order-courier" /></label>
      <label>Tracking number<input value={form.tracking_number} onChange={(event) => setForm({ ...form, tracking_number: event.target.value })} data-testid="admin-order-tracking-number" /></label>
      <label className="form-field-wide">Tracking link<input type="url" value={form.tracking_link} onChange={(event) => setForm({ ...form, tracking_link: event.target.value })} data-testid="admin-order-tracking-link" /></label>
      <label className="form-field-wide">Shipping details<textarea value={form.shipping_details} onChange={(event) => setForm({ ...form, shipping_details: event.target.value })} data-testid="admin-order-shipping-details" /></label>
      <label className="form-field-wide">Internal Admin notes<textarea value={form.internal_notes} onChange={(event) => setForm({ ...form, internal_notes: event.target.value })} data-testid="admin-order-internal-notes" /></label>

      <h3>Exceptional refund tracking</h3>
      <label>Refund status<select value={form.refund_status} onChange={(event) => setForm({ ...form, refund_status: event.target.value as RefundStatus })} data-testid="admin-order-refund-status">{refundStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>
      <label>Refund amount (₹)<input type="number" min="0" value={form.refund_amount} onChange={(event) => setForm({ ...form, refund_amount: event.target.value })} data-testid="admin-order-refund-amount" /></label>
      <label className="form-field-wide">Refund reason<textarea value={form.refund_reason} onChange={(event) => setForm({ ...form, refund_reason: event.target.value })} data-testid="admin-order-refund-reason" /></label>
      <label className="form-field-wide">Refund reference<input value={form.refund_reference} onChange={(event) => setForm({ ...form, refund_reference: event.target.value })} data-testid="admin-order-refund-reference" /></label>
      {form.refund_status === "Refunded" && request.refund_status !== "Refunded" && <label className="admin-confirmation form-field-wide"><input type="checkbox" checked={refundConfirmed} onChange={(event) => setRefundConfirmed(event.target.checked)} data-testid="admin-order-refund-confirmed" />I have confirmation that the refund completed.</label>}
      <button className="button button-dark form-field-wide" disabled={updateMutation.isPending || request.cancelled} data-testid="admin-order-save">Save order management details</button>
    </form>

    {error && <div className="form-error" data-testid="admin-order-error">{error}</div>}

    <section className="admin-order-section admin-order-actions-section">
      <h3>Order actions</h3>
      <div className="admin-print-actions" data-testid="admin-order-print-actions"><button className="button button-outline" onClick={() => { try { openOrderPrintView(request, "invoice"); } catch { toast.error("Allow pop-ups to open the print preview"); } }} data-testid="admin-order-print-invoice"><FileText size={15} /> Print invoice</button><button className="button button-outline" onClick={() => { try { openOrderPrintView(request, "packing-slip"); } catch { toast.error("Allow pop-ups to open the print preview"); } }} data-testid="admin-order-print-packing-slip"><PackageOpen size={15} /> Print packing slip</button></div>
      <button className="button button-outline" onClick={() => convertMutation.mutate()} disabled={!canConvert || Boolean(request.converted_order_id) || convertMutation.isPending} data-testid="admin-order-convert">{request.converted_order_id ? "Order already created" : "Convert request to order"}</button>
      {!request.cancelled && <div className="admin-cancel-order"><label>Cancellation reason<textarea value={cancellationReason} onChange={(event) => setCancellationReason(event.target.value)} data-testid="admin-order-cancellation-reason" /></label><button className="button danger-button" onClick={() => cancelMutation.mutate()} disabled={cancellationReason.trim().length < 5 || cancelMutation.isPending} data-testid="admin-order-cancel">Cancel order</button></div>}
      {request.cancelled && <p data-testid="admin-order-cancelled-reason"><strong>Cancellation reason:</strong> {request.cancellation_reason}</p>}
    </section>

    <section className="admin-order-section">
      <h3>Manual customer notification</h3>
      <p>No message is sent automatically. Review the text before opening WhatsApp.</p>
      <textarea value={notification} readOnly data-testid="admin-order-whatsapp-preview" />
      <a className="button button-outline" href={whatsapp} target="_blank" rel="noreferrer" data-testid="admin-order-whatsapp-link">Review in WhatsApp <ExternalLink size={15} /></a>
    </section>

    <section className="admin-order-section admin-order-history" data-testid="admin-order-history">
      <h3>Internal order history</h3>
      {[...request.history].reverse().map((event) => <div key={event.id}><span>{new Date(event.created_at).toLocaleString("en-IN")}</span><p>{event.message}</p></div>)}
    </section>
  </div>;
}

export default function AdminOrders() {
  const { user } = useAuth();
  const [searchDraft, setSearchDraft] = useState("");
  const [filters, setFilters] = useState({ q: "", payment: "", fulfilment: "", cancelled: "" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.payment) params.set("payment_status", filters.payment);
  if (filters.fulfilment) params.set("fulfilment_status", filters.fulfilment);
  if (filters.cancelled) params.set("cancelled", filters.cancelled);
  const query = params.toString();
  const { data: requests = [], isLoading, isError } = useQuery({ queryKey: ["admin-order-requests", filters], queryFn: () => apiGet<AdminOrderRequest[]>(`/order-requests${query ? `?${query}` : ""}`), retry: false });
  const activeId = selectedId ?? requests[0]?.id ?? null;
  const { data: selected } = useQuery({ queryKey: ["admin-order-request", activeId], queryFn: () => apiGet<AdminOrderRequest>(`/order-requests/${activeId}`), enabled: Boolean(activeId), retry: false });
  const search = (event: FormEvent) => { event.preventDefault(); setFilters({ ...filters, q: searchDraft.trim() }); setSelectedId(null); };

  return <div className="admin-shell">
    <header className="admin-secure-header"><div><ShieldCheck size={18} /><span>SAFYRA ORDER OPERATIONS</span></div><div><span data-testid="admin-order-user-name">{user?.name}</span><button onClick={() => endSession("/admin-login")} data-testid="admin-orders-logout"><LogOut size={15} /> Sign out</button></div></header>
    <main className="admin-orders-page">
      <div className="admin-heading"><div><span className="eyebrow">Restricted order workspace</span><h1>Order management</h1><p>Unpaid requests, verified payments, fulfilment and internal history.</p></div><Link to="/admin" className="button button-outline" data-testid="admin-back-to-catalog"><ArrowLeft size={15} /> Admin overview</Link></div>
      <form className="admin-order-filters" onSubmit={search} data-testid="admin-order-search-form">
        <label>Search<input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Reference, customer, phone, tracking or product" data-testid="admin-order-search" /></label>
        <label>Payment<select value={filters.payment} onChange={(event) => { setFilters({ ...filters, payment: event.target.value }); setSelectedId(null); }} data-testid="admin-order-filter-payment"><option value="">All</option>{paymentStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>
        <label>Fulfilment<select value={filters.fulfilment} onChange={(event) => { setFilters({ ...filters, fulfilment: event.target.value }); setSelectedId(null); }} data-testid="admin-order-filter-fulfilment"><option value="">All</option>{fulfilmentStatuses.map((status) => <option key={status}>{status}</option>)}</select></label>
        <label>Cancellation<select value={filters.cancelled} onChange={(event) => { setFilters({ ...filters, cancelled: event.target.value }); setSelectedId(null); }} data-testid="admin-order-filter-cancelled"><option value="">All</option><option value="false">Active</option><option value="true">Cancelled</option></select></label>
        <button className="button button-dark" data-testid="admin-order-search-submit"><Search size={15} /> Search</button>
      </form>
      <div className="admin-orders-layout">
        <aside className="admin-order-list" data-testid="admin-order-list">
          <div className="form-heading"><div><span className="eyebrow">Requests</span><h2>{requests.length} results</h2></div></div>
          {isLoading && <p>Loading order requests…</p>}
          {isError && <div className="form-error">Order requests could not be loaded.</div>}
          {!isLoading && !requests.length && <div className="account-empty"><PackageCheck size={25} /><p>No matching order requests.</p></div>}
          {requests.map((request) => <button key={request.id} className={activeId === request.id ? "admin-order-row is-active" : "admin-order-row"} onClick={() => setSelectedId(request.id)} data-testid={`admin-order-row-${request.id}`}><span><strong>{request.request_number}</strong><small>{request.name} · {request.items.length} item{request.items.length === 1 ? "" : "s"}</small></span><span><b>{request.payment_status}</b><small>{request.cancelled ? "Cancelled" : request.fulfilment_status}</small></span></button>)}
        </aside>
        <section>{selected ? <OrderEditor key={`${selected.id}-${selected.history.length}`} request={selected} /> : <div className="admin-list admin-order-placeholder"><Truck size={26} /><p>Select an order request to manage it.</p></div>}</section>
      </div>
    </main>
  </div>;
}