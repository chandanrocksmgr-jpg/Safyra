import type { ReactNode } from "react";
import { BadgePercent, BarChart3, BellRing, BookOpen, FileText, Home, Image, LayoutDashboard, LogOut, Package, ReceiptText, Settings, ShieldCheck, ShoppingBag, Tags, UserCog, Users } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import { useAuth } from "@/components/AuthProvider";
import { endSession } from "@/lib/session";

// `junior: true` marks the only screens a Junior Admin may open.
const navItems = [
  { to: "/admin", label: "Overview", icon: LayoutDashboard, end: true, junior: true },
  { to: "/admin/products", label: "Products", icon: Package, junior: true },
  { to: "/admin/collections", label: "Collections", icon: Tags },
  { to: "/admin/homepage", label: "Homepage", icon: Image },
  { to: "/admin/orders", label: "Orders", icon: ReceiptText },
  { to: "/admin/customers", label: "Customers", icon: Users },
  { to: "/admin/offers", label: "Offers", icon: BadgePercent },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/admin/settings", label: "Settings", icon: Settings },
  { to: "/admin/abandoned-checkouts", label: "Abandoned", icon: ShoppingBag },
  { to: "/admin/waitlist", label: "Waitlist", icon: BellRing },
  { to: "/admin/information", label: "Care info", icon: FileText },
  { to: "/admin/about", label: "Brand story", icon: BookOpen },
  { to: "/admin/staff", label: "Staff access", icon: UserCog },
];

interface AdminShellProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}

export default function AdminShell({ eyebrow, title, description, actions, children }: AdminShellProps) {
  const { user } = useAuth();
  const isJunior = user?.admin_role === "junior";
  const visibleNav = navItems.filter((item) => !isJunior || item.junior);
  return <div className="admin-shell admin-workspace" data-testid="admin-workspace">
    <header className="admin-secure-header" data-testid="admin-secure-header">
      <div data-testid="admin-secure-brand"><ShieldCheck size={18} /><span>SAFYRA CONTENT OPERATIONS</span></div>
      <div><span data-testid="admin-shell-user-name">{user?.name}</span><span className="admin-role-tag" data-testid="admin-shell-role">{isJunior ? "Junior Admin" : "Super Admin"}</span><button onClick={() => endSession("/admin-login")} data-testid="admin-shell-logout"><LogOut size={15} /> Sign out</button></div>
    </header>
    <div className="admin-workspace-grid">
      <aside className="admin-sidebar" data-testid="admin-sidebar">
        <Link to="/" className="admin-sidebar-brand" data-testid="admin-view-store-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link>
        <nav aria-label="Admin navigation" data-testid="admin-navigation">
          {visibleNav.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} className={({ isActive }) => isActive ? "is-active" : ""} data-testid={`admin-nav-${label.toLowerCase()}`}><Icon size={17} /> {label}</NavLink>)}
        </nav>
        <Link to="/" className="admin-store-shortcut" data-testid="admin-storefront-shortcut"><Home size={16} /> View storefront</Link>
      </aside>
      <main className="admin-workspace-main">
        <header className="admin-page-header" data-testid="admin-page-header">
          <div><span className="eyebrow" data-testid="admin-page-eyebrow">{eyebrow}</span><h1 data-testid="admin-page-title">{title}</h1><p data-testid="admin-page-description">{description}</p></div>
          {actions && <div className="admin-page-actions" data-testid="admin-page-actions">{actions}</div>}
        </header>
        {children}
      </main>
    </div>
  </div>;
}