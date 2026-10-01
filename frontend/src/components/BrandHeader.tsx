import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Heart, Menu, MessageCircle, Search, ShoppingBag, UserRound, X } from "lucide-react";
import { useShop } from "@/components/ShopProvider";
import { whatsappUrl, type Product } from "@/lib/shop";
import { apiGet } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import SearchExperience from "@/components/SearchExperience";
import { defaultHomepage, type CatalogGroup, type HomepageSettings } from "@/lib/cms";

interface MenuItem { label: string; to: string; type: string; value: string; }
interface MenuGroup { title: string; items: MenuItem[]; }

const fallbackMenuGroups: MenuGroup[] = [
  { title: "Shop by category", items: [
    { label: "Anarkalis", to: "/shop?category=Anarkali%20Sets", type: "category", value: "Anarkali Sets" },
    { label: "Angrakhas", to: "/shop?category=Angrakha%20Suits", type: "category", value: "Angrakha Suits" },
    { label: "Kurtas", to: "/shop?category=Straight%20Kurtis", type: "category", value: "Straight Kurtis" },
    { label: "Stitched Sets", to: "/shop?category=Stitched%20Sets", type: "category", value: "Stitched Sets" },
    { label: "Sarees", to: "/shop?category=Sarees", type: "category", value: "Sarees" },
    { label: "Dupattas", to: "/shop?category=Dupattas", type: "category", value: "Dupattas" },
    { label: "Chikankari Bottoms", to: "/shop?category=Chikankari%20Bottoms", type: "category", value: "Chikankari Bottoms" },
    { label: "Unstitched Sets", to: "/shop?category=Unstitched%20Sets", type: "category", value: "Unstitched Sets" },
  ] },
  { title: "Shop the edit", items: [
    { label: "New Arrivals", to: "/shop?new=true&sort=newest", type: "new", value: "" },
    { label: "Best Sellers", to: "/shop?sort=best-selling", type: "best", value: "" },
    { label: "Safyra Luxury", to: "/shop?collection=Safyra%20Luxury", type: "collection", value: "Safyra Luxury" },
    { label: "Everyday Edit", to: "/shop?collection=Everyday%20Edit", type: "collection", value: "Everyday Edit" },
    { label: "Celebrity Corner", to: "/shop?collection=Celebrity%20Corner", type: "collection", value: "Celebrity Corner" },
    { label: "Extended Sizes", to: "/shop?size=3XL", type: "size", value: "3XL" },
  ] },
  { title: "About SAFYRA", items: [
    { label: "The craft", to: "/information#craft", type: "static", value: "" },
  ] },
];

export default function BrandHeader() {
  const location = useLocation();
  const { cartCount, wishlistIds, openDrawer } = useShop();
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [announcementIndex, setAnnouncementIndex] = useState(0);
  const { data: navigationProducts } = useQuery({ queryKey: ["products", "navigation"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { data: catalogGroups = [], isSuccess: catalogGroupsLoaded, isFetching: catalogGroupsFetching, isError: catalogGroupsUnavailable } = useQuery({ queryKey: ["catalog-groups", "public"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups"), retry: false });
  const { data: homepage } = useQuery({ queryKey: ["homepage"], queryFn: () => apiGet<HomepageSettings>("/homepage"), retry: false });
  const managedCategories: MenuItem[] = catalogGroups.filter((group) => group.group_type === "category").map((group) => ({ label: group.name, to: `/shop?category=${encodeURIComponent(group.name)}`, type: "category", value: group.name }));
  const managedCollections: MenuItem[] = catalogGroups.filter((group) => group.group_type === "collection").map((group) => ({ label: group.name, to: `/shop?collection=${encodeURIComponent(group.name)}`, type: "collection", value: group.name }));
  const catalogGroupsReady = catalogGroupsLoaded && !catalogGroupsFetching;
  const collectionIsActive = (name: string) => catalogGroupsUnavailable || (catalogGroupsReady && managedCollections.some((group) => group.value === name));
  const itemHasProducts = (item: MenuItem) => item.type === "static" || Boolean(navigationProducts?.some((product) => item.type === "category" ? product.category === item.value : item.type === "collection" ? product.collection === item.value && collectionIsActive(item.value) : item.type === "new" ? product.new_arrival : item.type === "best" ? product.best_seller : product.sizes.includes(item.value)));
  const visibleMenuGroups: MenuGroup[] = catalogGroupsReady ? [
    { title: "Shop by category", items: managedCategories },
    { title: "Collections", items: managedCollections },
    { title: "Shop the edit", items: fallbackMenuGroups[1].items.filter(itemHasProducts) },
    { title: "About SAFYRA", items: fallbackMenuGroups[2].items },
  ].filter((group) => group.items.length) : catalogGroupsUnavailable ? fallbackMenuGroups.map((group) => ({ ...group, items: group.items.filter(itemHasProducts) })).filter((group) => group.items.length) : [
    { title: "Shop the edit", items: fallbackMenuGroups[1].items.filter((item) => item.type !== "collection" && itemHasProducts(item)) },
    { title: "About SAFYRA", items: fallbackMenuGroups[2].items },
  ].filter((group) => group.items.length);
  const announcements = homepage?.announcement_messages.length ? homepage.announcement_messages : defaultHomepage.announcement_messages;
  const hasNewArrivals = Boolean(navigationProducts?.some((product) => product.new_arrival));
  const hasLuxury = Boolean(navigationProducts?.some((product) => product.collection === "Safyra Luxury")) && collectionIsActive("Safyra Luxury");
  const hasExtendedSizes = Boolean(navigationProducts?.some((product) => product.sizes.includes("3XL")));
  const currentQuery = new URLSearchParams(location.search).get("search") ?? "";
  const showWhatsapp = !["/login", "/signup", "/account", "/checkout"].includes(location.pathname) && !location.pathname.startsWith("/product/");

  useEffect(() => {
    const timer = window.setInterval(() => setAnnouncementIndex((current) => (current + 1) % announcements.length), 5000);
    return () => window.clearInterval(timer);
  }, [announcements.length]);

  return (
    <>
      <div className="announcement" data-testid="announcement-bar"><span className="announcement-message" data-testid="announcement-message">{announcements[announcementIndex % announcements.length]}</span></div>
      <header className="site-header" data-testid="site-header">
        <div className="header-inner">
          <button className="icon-button mobile-only" onClick={() => setMenuOpen((open) => !open)} aria-label="Open menu" data-testid="mobile-menu-toggle"><Menu size={20} /></button>
          <Link to="/" className="wordmark" data-testid="brand-home-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link>
          <nav className="desktop-nav" aria-label="Primary navigation">
            {hasNewArrivals && <Link to="/shop?new=true&sort=newest" className="nav-link" data-testid="header-nav-new-arrivals">New Arrivals</Link>}
            <button className="nav-link nav-menu-trigger" onClick={() => setMenuOpen((open) => !open)} data-testid="header-nav-shop">Shop <ChevronDown size={14} /></button>
            <button className="nav-link nav-menu-trigger" onClick={() => setMenuOpen((open) => !open)} data-testid="header-nav-collections">Collections</button>
            {hasLuxury && <Link to="/shop?collection=Safyra%20Luxury" className="nav-link" data-testid="header-nav-luxury">SAFYRA Luxury</Link>}
            {hasExtendedSizes && <Link to="/shop?size=3XL" className="nav-link" data-testid="header-nav-extended-sizes">Extended Sizes</Link>}
            <Link to="/information#craft" className="nav-link" data-testid="header-nav-about">About</Link>
          </nav>
          <div className="header-actions">
            <button className="icon-button" onClick={() => setSearchOpen((open) => !open)} aria-label="Search SAFYRA" data-testid="header-search-button"><Search size={19} /></button>
            <Link to={user?.role === "admin" ? "/admin/orders" : user ? "/account" : "/login"} className="icon-button account-action" aria-label={user ? "My account" : "Sign in"} data-testid="header-account-link"><UserRound size={19} /></Link>
            <Link to="/wishlist" className="icon-button with-count" aria-label="Wishlist" data-testid="header-wishlist-link"><Heart size={19} /><span>{wishlistIds.length}</span></Link>
            <button className="icon-button with-count" onClick={openDrawer} aria-label="Open shopping bag" data-testid="cart-drawer-trigger"><ShoppingBag size={19} /><span>{cartCount}</span></button>
          </div>
        </div>
        {searchOpen && <SearchExperience initialQuery={currentQuery} onClose={() => setSearchOpen(false)} />}
        {menuOpen && <div className="mega-menu" data-testid="mega-menu"><div className="mega-menu-inner"><div className="mega-menu-heading"><span className="eyebrow">Shop SAFYRA</span><h2>Silhouette, fabric<br />or Chikankari detail.</h2><p>Start with what matters to you, then refine by colour, size and availability.</p><Link to="/shop" onClick={() => setMenuOpen(false)} className="underlined-link" data-testid="mega-menu-shop-link">Shop all pieces →</Link><Link to={user ? "/account" : "/login"} onClick={() => setMenuOpen(false)} className="mobile-account-link" data-testid="mobile-account-link">{user ? "My account" : "Sign in / Create account"}</Link></div>{visibleMenuGroups.map((group) => <div key={group.title} className="mega-group"><span className="eyebrow">{group.title}</span>{group.items.map((item) => <Link key={item.label} to={item.to} onClick={() => setMenuOpen(false)} data-testid={`mega-menu-link-${item.label.toLowerCase().replaceAll(" ", "-")}`}>{item.label}</Link>)}</div>)}<button className="mega-close" onClick={() => setMenuOpen(false)} aria-label="Close menu" data-testid="mega-menu-close"><X size={20} /></button></div></div>}
      </header>
      {showWhatsapp && <a className="whatsapp-float" href={whatsappUrl("Hello SAFYRA, I would like help choosing a Chikankari piece.")} target="_blank" rel="noreferrer" data-testid="floating-whatsapp-link"><MessageCircle size={16} /><span>Stylist help</span></a>}
    </>
  );
}