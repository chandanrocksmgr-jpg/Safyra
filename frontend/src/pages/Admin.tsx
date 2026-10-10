import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, BellRing, CheckCircle2, FileEdit, Image, KeyRound, Package, ReceiptText, ShoppingBag, Tags } from "lucide-react";
import { Link } from "react-router-dom";
import { apiGet, apiPut, ApiError } from "@/lib/api";
import type { CatalogGroup, HomepageSettings } from "@/lib/cms";
import type { Product } from "@/lib/shop";
import type { AdminOrderRequest } from "@/lib/checkout";
import AdminShell from "@/components/AdminShell";
import { endSession } from "@/lib/session";
import type { WaitlistRequestAdmin } from "@/lib/waitlist";

const quickLinks = [
  { to: "/admin/products", title: "Products", copy: "Edit products, inventory, images and publishing status.", icon: Package, testId: "admin-dashboard-products" },
  { to: "/admin/collections", title: "Collections", copy: "Organise customer-facing categories and collections.", icon: Tags, testId: "admin-dashboard-collections" },
  { to: "/admin/homepage", title: "Homepage", copy: "Update hero, section copy, imagery and visibility.", icon: Image, testId: "admin-dashboard-homepage" },
  { to: "/admin/orders", title: "Orders", copy: "Manage order requests, payment status and fulfilment.", icon: ReceiptText, testId: "admin-dashboard-orders" },
  { to: "/admin/waitlist", title: "Waitlist", copy: "Track unavailable pieces, customer follow-up and outcomes.", icon: BellRing, testId: "admin-dashboard-waitlist" },
  { to: "/admin/abandoned-checkouts", title: "Abandoned checkouts", copy: "Review incomplete checkouts and one-time recovery email status.", icon: ShoppingBag, testId: "admin-dashboard-abandoned-checkouts" },
];

export default function Admin() {
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [passwordMessage, setPasswordMessage] = useState("");
  const { data: products = [] } = useQuery({ queryKey: ["products", "admin"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { data: groups = [] } = useQuery({ queryKey: ["catalog-groups", "admin"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups?include_all=true"), retry: false });
  const { data: homepage } = useQuery({ queryKey: ["homepage"], queryFn: () => apiGet<HomepageSettings>("/homepage"), retry: false });
  const { data: orders = [] } = useQuery({ queryKey: ["admin-order-requests", "dashboard"], queryFn: () => apiGet<AdminOrderRequest[]>("/order-requests"), retry: false });
  const { data: waitlist = [] } = useQuery({ queryKey: ["admin-waitlist", "dashboard"], queryFn: () => apiGet<WaitlistRequestAdmin[]>("/waitlist?limit=200"), retry: false });
  const passwordMutation = useMutation({
    mutationFn: () => apiPut<void>("/auth/password", { current_password: passwords.current, new_password: passwords.next }),
    onSuccess: async () => { await endSession("/admin-login"); },
    onError: (reason) => setPasswordMessage(reason instanceof ApiError && reason.status === 400 ? "Current password is incorrect." : "Use 10+ characters with uppercase, lowercase, number and symbol."),
  });
  const submitPassword = (event: FormEvent) => { event.preventDefault(); setPasswordMessage(""); passwordMutation.mutate(); };
  const activeProducts = products.filter((product) => product.status === "active").length;

  return <AdminShell eyebrow="Store command centre" title="Good to see you." description="Manage the SAFYRA catalogue and storefront content without touching code.">
    <section className="admin-metrics" data-testid="admin-dashboard-metrics">
      <div data-testid="admin-metric-products"><span>Active products</span><strong>{activeProducts}</strong><small>{products.length - activeProducts} draft or archived</small></div>
      <div data-testid="admin-metric-groups"><span>Collections & categories</span><strong>{groups.length}</strong><small>{groups.filter((group) => group.status === "active").length} customer-facing</small></div>
      <div data-testid="admin-metric-orders"><span>Order requests</span><strong>{orders.length}</strong><small>{orders.filter((order) => order.payment_status === "Unpaid").length} awaiting payment</small></div>
      <div data-testid="admin-metric-waitlist"><span>Waitlist</span><strong>{waitlist.length}</strong><small>{waitlist.filter((request) => request.status === "Waiting").length} awaiting contact</small></div>
      <div data-testid="admin-metric-homepage"><span>Homepage</span><strong>{homepage ? "Live" : "—"}</strong><small>{homepage?.updated_at ? `Updated ${new Date(homepage.updated_at).toLocaleDateString("en-IN")}` : "Loading content"}</small></div>
    </section>
    <section className="admin-dashboard-section" data-testid="admin-dashboard-workspaces">
      <div className="admin-section-heading"><div><span className="eyebrow">Editable workspaces</span><h2>Run your store</h2></div><CheckCircle2 size={22} /></div>
      <div className="admin-quick-grid">{quickLinks.map(({ to, title, copy, icon: Icon, testId }) => <Link to={to} key={to} className="admin-quick-card" data-testid={testId}><Icon size={22} /><div><h3>{title}</h3><p>{copy}</p></div><ArrowRight size={17} /></Link>)}</div>
    </section>
    <section className="admin-dashboard-section admin-security-panel" data-testid="admin-security-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Account security</span><h2>Change password</h2></div><KeyRound size={22} /></div>
      <form onSubmit={submitPassword} data-testid="admin-change-password-form">
        <label>Current password<input type="password" value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} required data-testid="admin-current-password" /></label>
        <label>New secure password<input type="password" value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} required data-testid="admin-new-password" /><small>10+ characters with upper, lower, number and symbol.</small></label>
        <button className="button button-dark" disabled={passwordMutation.isPending} data-testid="admin-change-password-submit"><FileEdit size={15} /> Change password</button>
      </form>
      {passwordMessage && <div className="form-error" data-testid="admin-password-message">{passwordMessage}</div>}
    </section>
  </AdminShell>;
}