import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserRound } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import StoreCreditPanel from "@/components/StoreCreditPanel";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/shop";
import { formatCreditDate, type AdminCustomerDetail, type AdminCustomerRow, type StoreCreditIssue } from "@/lib/storeCredit";

function IssueCreditForm({ customer }: { customer: AdminCustomerDetail }) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("");
  const [confirming, setConfirming] = useState(false);
  const value = Math.floor(Number(amount));
  const issue = useMutation({
    mutationFn: (payload: StoreCreditIssue) => apiPost<AdminCustomerDetail>(`/admin/customers/${customer.id}/store-credit`, payload),
    onSuccess: async (detail) => {
      queryClient.setQueryData(["admin-customers", "detail", customer.id], detail);
      await queryClient.invalidateQueries({ queryKey: ["admin-customers", "list"] });
      toast.success(`${formatPrice(value)} SAFYRA Credit issued to ${customer.name}`, { description: "The customer has been emailed." });
      setAmount("");
      setConfirming(false);
    },
    onError: (reason) => toast.error(reason instanceof ApiError && reason.status === 422 ? "Enter a whole rupee amount of at least ₹1" : "Credit could not be issued"),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!Number.isFinite(value) || value < 1) { toast.error("Enter a whole rupee amount of at least ₹1"); return; }
    if (!confirming) { setConfirming(true); return; }
    issue.mutate({ amount: value });
  };
  const expiry = new Date();
  expiry.setFullYear(expiry.getFullYear() + 1);
  return <form className="issue-credit-form" onSubmit={submit} data-testid="admin-issue-credit-form">
    <div><span className="eyebrow">Issue SAFYRA Credit</span><p>Valid for one year from today, until {formatCreditDate(expiry.toISOString())}. The customer is emailed straight away.</p></div>
    <div className="issue-credit-row">
      <label>Amount (₹)<input type="number" min={1} step={1} inputMode="numeric" value={amount} onChange={(event) => { setAmount(event.target.value); setConfirming(false); }} placeholder="e.g. 1000" data-testid="admin-issue-credit-amount" /></label>
      <button className="button button-dark" disabled={issue.isPending || !amount} data-testid="admin-issue-credit-submit">{issue.isPending ? "Issuing…" : confirming ? `Confirm ${formatPrice(value)}` : "Issue credit"}</button>
      {confirming && !issue.isPending && <button type="button" className="button button-outline" onClick={() => setConfirming(false)} data-testid="admin-issue-credit-cancel">Cancel</button>}
    </div>
    {confirming && <p className="issue-credit-confirm" data-testid="admin-issue-credit-confirm-note">You're about to add {formatPrice(value)} to {customer.name}'s account ({customer.email}). Press confirm to continue.</p>}
  </form>;
}

export default function AdminCustomers() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: customers = [], isLoading, isError } = useQuery({
    queryKey: ["admin-customers", "list", query],
    queryFn: () => apiGet<AdminCustomerRow[]>(`/admin/customers?q=${encodeURIComponent(query)}`),
    retry: false,
  });
  const activeId = selectedId ?? customers[0]?.id ?? null;
  const { data: selected } = useQuery({
    queryKey: ["admin-customers", "detail", activeId],
    queryFn: () => apiGet<AdminCustomerDetail>(`/admin/customers/${activeId}`),
    enabled: Boolean(activeId),
    retry: false,
  });
  const search = (event: FormEvent) => { event.preventDefault(); setQuery(draft.trim()); setSelectedId(null); };

  return <AdminShell eyebrow="Customers & returns" title="Customers" description="Find a registered customer by email or mobile, review their orders and issue SAFYRA Credit for returns.">
    <form className="admin-waitlist-toolbar" onSubmit={search} data-testid="admin-customers-search-form">
      <label className="admin-search-field"><Search size={15} /><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Email, mobile number or name" data-testid="admin-customers-search-input" /></label>
      <button className="button button-dark" data-testid="admin-customers-search-submit">Search</button>
    </form>
    <div className="admin-waitlist-layout">
      <aside className="admin-waitlist-list" data-testid="admin-customers-list">
        <div className="admin-waitlist-list-heading"><span className="eyebrow">{query ? "Matches" : "Recent customers"}</span><strong data-testid="admin-customers-result-count">{customers.length} {customers.length === 1 ? "customer" : "customers"}</strong></div>
        {isLoading && <p data-testid="admin-customers-loading">Loading customers…</p>}
        {isError && <div className="form-error" data-testid="admin-customers-load-error">Customers could not be loaded.</div>}
        {!isLoading && !customers.length && <div className="admin-waitlist-empty" data-testid="admin-customers-empty"><UserRound size={23} /><p>No registered customer matches “{query}”.</p></div>}
        {customers.map((customer) => <button key={customer.id} className={activeId === customer.id ? "admin-waitlist-row is-active" : "admin-waitlist-row"} onClick={() => setSelectedId(customer.id)} data-testid={`admin-customer-row-${customer.id}`}>
          <span><strong>{customer.name}</strong><small>{customer.email}</small><small>{customer.phone || "No mobile saved"}</small></span>
          <span><b>{customer.credit_balance > 0 ? formatPrice(customer.credit_balance) : "—"}</b><small>credit</small></span>
        </button>)}
      </aside>
      <section>{selected ? <article className="admin-waitlist-detail admin-customer-detail" data-testid="admin-customer-detail">
        <header className="admin-customer-header">
          <div><span className="eyebrow">Registered customer</span><h2 data-testid="admin-customer-name">{selected.name}</h2><p data-testid="admin-customer-contact">{selected.email}{selected.phone ? ` · ${selected.phone}` : ""}</p>{selected.created_at && <small>Customer since {formatCreditDate(selected.created_at)}</small>}</div>
        </header>
        <IssueCreditForm key={selected.id} customer={selected} />
        <StoreCreditPanel summary={selected.credits} audience="admin" testId="admin-customer-credit" />
        <div className="admin-customer-orders" data-testid="admin-customer-orders">
          <span className="eyebrow">Orders</span>
          {selected.orders.length ? <ul>{selected.orders.map((order) => <li key={order.request_number} data-testid={`admin-customer-order-${order.request_number}`}><span><strong>{order.request_number}</strong><small>{formatCreditDate(order.created_at)} · {order.payment_status}{order.fulfilment_status ? ` · ${order.fulfilment_status}` : ""}</small></span><span>{formatPrice(order.total)}{order.credit_applied > 0 && <small>{formatPrice(order.credit_applied)} paid with credit</small>}</span></li>)}</ul> : <p>No confirmed orders yet.</p>}
        </div>
      </article> : <div className="admin-waitlist-empty admin-waitlist-placeholder" data-testid="admin-customers-placeholder"><UserRound size={25} /><p>Search for a customer to view their account.</p></div>}</section>
    </div>
  </AdminShell>;
}
