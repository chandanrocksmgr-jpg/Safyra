import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, BellRing, Search, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import SafeProductImage from "@/components/SafeProductImage";
import { apiGet, apiPatch, ApiError } from "@/lib/api";
import type { WaitlistAdminUpdate, WaitlistRequestAdmin, WaitlistStatus } from "@/lib/waitlist";

const statuses: WaitlistStatus[] = ["Waiting", "Contacted", "Converted", "Closed"];

function errorDetail(reason: unknown) {
  if (reason instanceof ApiError && reason.body && typeof reason.body === "object" && "detail" in reason.body) {
    const detail = (reason.body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return "The waitlist request could not be updated.";
}

function WaitlistEditor({ request }: { request: WaitlistRequestAdmin }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<WaitlistStatus>(request.status);
  const [notes, setNotes] = useState(request.admin_notes);
  const [error, setError] = useState("");
  const mutation = useMutation({
    mutationFn: (payload: WaitlistAdminUpdate) => apiPatch<WaitlistRequestAdmin>(`/waitlist/${request.id}`, payload),
    onSuccess: async () => { setError(""); await queryClient.invalidateQueries({ queryKey: ["admin-waitlist"] }); toast.success("Waitlist request updated"); },
    onError: (reason) => setError(errorDetail(reason)),
  });
  const save = (event: FormEvent) => { event.preventDefault(); mutation.mutate({ status, admin_notes: notes }); };
  const variant = [request.set_type, request.size && `Size ${request.size}`, request.color].filter(Boolean).join(" · ") || "No size or colour variant";

  return <article className="admin-waitlist-detail" data-testid="admin-waitlist-detail">
    <header className="admin-waitlist-detail-header" data-testid="admin-waitlist-detail-header">
      <SafeProductImage src={request.product_image_url} alt={request.product_title} productName={request.product_title} />
      <div><span className="eyebrow" data-testid="admin-waitlist-detail-eyebrow">Availability request</span><h2 data-testid="admin-waitlist-product-title">{request.product_title}</h2><p data-testid="admin-waitlist-variant">{variant}</p></div>
      <span className={`admin-status-pill status-${request.status.toLowerCase()}`} data-testid="admin-waitlist-current-status">{request.status}</span>
    </header>
    <section className="admin-waitlist-contact" data-testid="admin-waitlist-contact">
      <div><UserRound size={19} /><span><small>Customer</small><strong data-testid="admin-waitlist-customer-name">{request.customer_name}</strong></span></div>
      <a href={`tel:${request.mobile}`} data-testid="admin-waitlist-customer-mobile"><small>Mobile</small><strong>{request.mobile}</strong></a>
      {request.email ? <a href={`mailto:${request.email}`} data-testid="admin-waitlist-customer-email"><small>Email</small><strong>{request.email}</strong></a> : <div data-testid="admin-waitlist-no-email"><small>Email</small><strong>Not provided</strong></div>}
    </section>
    <form className="admin-editor-card admin-waitlist-form" onSubmit={save} data-testid="admin-waitlist-management-form">
      <h3 data-testid="admin-waitlist-management-heading">Request management</h3>
      <label>Status<select value={status} onChange={(event) => setStatus(event.target.value as WaitlistStatus)} data-testid="admin-waitlist-status-select">{statuses.map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>Internal notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Record contact attempts, preferences or outcomes." data-testid="admin-waitlist-notes" /></label>
      {error && <div className="form-error" data-testid="admin-waitlist-update-error">{error}</div>}
      <button className="button button-dark" disabled={mutation.isPending} data-testid="admin-waitlist-save">{mutation.isPending ? "Saving…" : "Save status and notes"}</button>
    </form>
    <footer className="admin-waitlist-footer" data-testid="admin-waitlist-timestamps"><span>Joined {new Date(request.created_at).toLocaleString("en-IN")}</span><Link to={`/product/${request.product_slug}`} target="_blank" data-testid="admin-waitlist-view-product">View product <ArrowUpRight size={14} /></Link></footer>
  </article>;
}

export default function AdminWaitlist() {
  const [searchDraft, setSearchDraft] = useState("");
  const [filters, setFilters] = useState({ q: "", status: "" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.status) params.set("status", filters.status);
  params.set("limit", "200");
  const { data: requests = [], isLoading, isError } = useQuery({ queryKey: ["admin-waitlist", "list", filters], queryFn: () => apiGet<WaitlistRequestAdmin[]>(`/waitlist?${params}`), retry: false });
  const activeId = selectedId ?? requests[0]?.id ?? null;
  const { data: selected } = useQuery({ queryKey: ["admin-waitlist", "detail", activeId], queryFn: () => apiGet<WaitlistRequestAdmin>(`/waitlist/${activeId}`), enabled: Boolean(activeId), retry: false });
  const search = (event: FormEvent) => { event.preventDefault(); setFilters({ ...filters, q: searchDraft.trim() }); setSelectedId(null); };
  const waitingCount = requests.filter((request) => request.status === "Waiting").length;

  return <AdminShell eyebrow="Customer demand" title="Waitlist" description="Track unavailable-piece requests, customer follow-up and outcomes without inventing stock." actions={<div className="admin-waitlist-summary" data-testid="admin-waitlist-waiting-count"><BellRing size={16} /> {waitingCount} waiting</div>}>
    <form className="admin-waitlist-toolbar" onSubmit={search} data-testid="admin-waitlist-search-form">
      <label className="admin-search-field"><Search size={15} /><input value={searchDraft} onChange={(event) => setSearchDraft(event.target.value)} placeholder="Customer, mobile, email or product" data-testid="admin-waitlist-search-input" /></label>
      <select value={filters.status} onChange={(event) => { setFilters({ ...filters, status: event.target.value }); setSelectedId(null); }} data-testid="admin-waitlist-status-filter"><option value="">All statuses</option>{statuses.map((status) => <option value={status} key={status}>{status}</option>)}</select>
      <button className="button button-dark" data-testid="admin-waitlist-search-submit">Search</button>
    </form>
    <div className="admin-waitlist-layout">
      <aside className="admin-waitlist-list" data-testid="admin-waitlist-list">
        <div className="admin-waitlist-list-heading"><span className="eyebrow">Requests</span><strong data-testid="admin-waitlist-result-count">{requests.length} results</strong></div>
        {isLoading && <p data-testid="admin-waitlist-loading">Loading waitlist requests…</p>}
        {isError && <div className="form-error" data-testid="admin-waitlist-load-error">Waitlist requests could not be loaded.</div>}
        {!isLoading && !requests.length && <div className="admin-waitlist-empty" data-testid="admin-waitlist-empty"><BellRing size={23} /><p>No matching waitlist requests.</p></div>}
        {requests.map((request) => <button key={request.id} className={activeId === request.id ? "admin-waitlist-row is-active" : "admin-waitlist-row"} onClick={() => setSelectedId(request.id)} data-testid={`admin-waitlist-row-${request.id}`}><span><strong>{request.customer_name}</strong><small>{request.product_title}</small><small>{[request.size, request.color].filter(Boolean).join(" · ") || "No variant"}</small></span><span><b>{request.status}</b><small>{new Date(request.created_at).toLocaleDateString("en-IN")}</small></span></button>)}
      </aside>
      <section>{selected ? <WaitlistEditor key={`${selected.id}-${selected.updated_at}`} request={selected} /> : <div className="admin-waitlist-empty admin-waitlist-placeholder" data-testid="admin-waitlist-placeholder"><UserRound size={25} /><p>Select a request to view customer details.</p></div>}</section>
    </div>
  </AdminShell>;
}