import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronDown, Heart, Menu, MessageCircle, Search, ShoppingBag, UserRound, X } from "lucide-react";
import { useShop } from "@/components/ShopProvider";
import { whatsappUrl } from "@/lib/shop";
import { useAuth } from "@/components/AuthProvider";
import SearchExperience from "@/components/SearchExperience";

const menuGroups = [
  { title: "Collections", items: ["Safyra Luxury", "Vaaya Kota Doria", "Everyday Edit"] },
  { title: "Categories", items: ["Anarkali Sets", "Angrakha Suits", "Straight Kurtis", "Sarees", "Kurta & Pant Sets", "Dupattas", "Unstitched Suits"] },
  { title: "The craft", items: ["Pure Kota Doria", "Mukaish", "Badla", "French Knot"] },
];

export default function BrandHeader() {
  const location = useLocation();
  const { cartCount, wishlistIds, openDrawer } = useShop();
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const currentQuery = new URLSearchParams(location.search).get("search") ?? "";
  const showWhatsapp = !["/login", "/signup", "/account", "/checkout"].includes(location.pathname) && !location.pathname.startsWith("/product/");

  return (
    <>
      <div className="announcement" data-testid="announcement-bar">FREE SHIPPING ON ORDERS ABOVE ₹1,299</div>
      <header className="site-header" data-testid="site-header">
        <div className="header-inner">
          <button className="icon-button mobile-only" onClick={() => setMenuOpen((open) => !open)} aria-label="Open menu" data-testid="mobile-menu-toggle"><Menu size={20} /></button>
          <Link to="/" className="wordmark" data-testid="brand-home-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link>
          <nav className="desktop-nav" aria-label="Primary navigation">
            <Link to="/shop?new=true&sort=newest" className="nav-link" data-testid="header-nav-new-arrivals">New Arrivals</Link>
            <button className="nav-link nav-menu-trigger" onClick={() => setMenuOpen((open) => !open)} data-testid="header-nav-shop">Shop <ChevronDown size={14} /></button>
            <button className="nav-link nav-menu-trigger" onClick={() => setMenuOpen((open) => !open)} data-testid="header-nav-collections">Collections</button>
            <Link to="/shop?collection=Safyra%20Luxury" className="nav-link" data-testid="header-nav-luxury">SAFYRA Luxury</Link>
            <Link to="/shop?size=3XL" className="nav-link" data-testid="header-nav-extended-sizes">Extended Sizes</Link>
            <Link to="/#craft-story" className="nav-link" data-testid="header-nav-about">About</Link>
          </nav>
          <div className="header-actions">
            <button className="icon-button" onClick={() => setSearchOpen((open) => !open)} aria-label="Search SAFYRA" data-testid="header-search-button"><Search size={19} /></button>
            <Link to={user?.role === "admin" ? "/admin" : user ? "/account" : "/login"} className="icon-button account-action" aria-label={user ? "My account" : "Sign in"} data-testid="header-account-link"><UserRound size={19} /></Link>
            <Link to="/wishlist" className="icon-button with-count" aria-label="Wishlist" data-testid="header-wishlist-link"><Heart size={19} /><span>{wishlistIds.length}</span></Link>
            <button className="icon-button with-count" onClick={openDrawer} aria-label="Open shopping bag" data-testid="cart-drawer-trigger"><ShoppingBag size={19} /><span>{cartCount}</span></button>
          </div>
        </div>
        {searchOpen && <SearchExperience initialQuery={currentQuery} onClose={() => setSearchOpen(false)} />}
        {menuOpen && <div className="mega-menu" data-testid="mega-menu"><div className="mega-menu-inner"><div className="mega-menu-heading"><span className="eyebrow">Shop SAFYRA</span><h2>Silhouette, fabric<br />or Chikankari detail.</h2><p>Start with what matters to you, then refine by colour, size and availability.</p><Link to="/shop" onClick={() => setMenuOpen(false)} className="underlined-link" data-testid="mega-menu-shop-link">Shop all pieces →</Link><Link to={user ? "/account" : "/login"} onClick={() => setMenuOpen(false)} className="mobile-account-link" data-testid="mobile-account-link">{user ? "My account" : "Sign in / Create account"}</Link></div>{menuGroups.map((group) => <div key={group.title} className="mega-group"><span className="eyebrow">{group.title}</span>{group.items.map((item) => <Link key={item} to={`/shop?search=${encodeURIComponent(item)}`} onClick={() => setMenuOpen(false)} data-testid={`mega-menu-link-${item.toLowerCase().replaceAll(" ", "-")}`}>{item}</Link>)}</div>)}<button className="mega-close" onClick={() => setMenuOpen(false)} aria-label="Close menu" data-testid="mega-menu-close"><X size={20} /></button></div></div>}
      </header>
      {showWhatsapp && <a className="whatsapp-float" href={whatsappUrl("Hello SAFYRA, I would like help choosing a Chikankari piece.")} target="_blank" rel="noreferrer" data-testid="floating-whatsapp-link"><MessageCircle size={16} /><span>Stylist help</span></a>}
    </>
  );
}