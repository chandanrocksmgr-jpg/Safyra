import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, Heart, Menu, MessageCircle, Search, ShoppingBag, UserRound, X } from "lucide-react";
import { useShop } from "@/components/ShopProvider";
import { whatsappUrl } from "@/lib/shop";
import { useAuth } from "@/components/AuthProvider";

const menuGroups = [
  { title: "Collections", items: ["Safyra Luxury", "Nazakat", "Vaaya Kota Doria", "Everyday Edit"] },
  { title: "Categories", items: ["Anarkali Sets", "Angrakha Suits", "Straight Kurtis", "Sarees & Dupattas"] },
  { title: "The craft", items: ["Pure Kota Doria", "Mul Chanderi", "Mukaish & Badla", "Zardozi"] },
];

export default function BrandHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { cartCount, wishlistIds, openDrawer } = useShop();
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState(new URLSearchParams(location.search).get("search") ?? "");

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    navigate(`/shop${query.trim() ? `?search=${encodeURIComponent(query.trim())}` : ""}`);
    setSearchOpen(false);
  };

  return (
    <>
      <div className="announcement" data-testid="announcement-bar">Free worldwide shipping on orders above ₹15,000 <span>·</span> 100% authentic handcrafted Lucknowi Chikankari</div>
      <header className="site-header" data-testid="site-header">
        <div className="header-inner">
          <button className="icon-button mobile-only" onClick={() => setMenuOpen((open) => !open)} aria-label="Open menu" data-testid="mobile-menu-toggle"><Menu size={20} /></button>
          <Link to="/" className="wordmark" data-testid="brand-home-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link>
          <nav className="desktop-nav" aria-label="Primary navigation">
            <button className="nav-link nav-menu-trigger" onClick={() => setMenuOpen((open) => !open)} data-testid="header-nav-link-collections">Collections <ChevronDown size={14} /></button>
            <Link to="/shop?category=Anarkali%20Sets" className="nav-link" data-testid="header-nav-link-anarkalis">Anarkalis</Link>
            <Link to="/shop?category=Angrakha%20Suits" className="nav-link" data-testid="header-nav-link-angrakhas">Angrakhas</Link>
            <Link to="/shop?category=Straight%20Kurtis" className="nav-link" data-testid="header-nav-link-everyday">Everyday edit</Link>
          </nav>
          <div className="header-actions">
            <button className="icon-button" onClick={() => setSearchOpen((open) => !open)} aria-label="Search SAFYRA" data-testid="header-search-button"><Search size={19} /></button>
            <Link to={user ? "/account" : "/login"} className="icon-button" aria-label={user ? "My account" : "Sign in"} data-testid="header-account-link"><UserRound size={19} /></Link>
            <Link to="/wishlist" className="icon-button with-count" aria-label="Wishlist" data-testid="header-wishlist-link"><Heart size={19} /><span>{wishlistIds.length}</span></Link>
            <button className="icon-button with-count" onClick={openDrawer} aria-label="Open shopping bag" data-testid="cart-drawer-trigger"><ShoppingBag size={19} /><span>{cartCount}</span></button>
          </div>
        </div>
        {searchOpen && <form className="search-strip" onSubmit={submitSearch} data-testid="global-search-form"><Search size={18} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search handcrafted pieces, fabric or collection" data-testid="global-search-input" /><button className="text-button" type="submit" data-testid="global-search-submit">Search</button></form>}
        {menuOpen && <div className="mega-menu" data-testid="mega-menu"><div className="mega-menu-inner"><div className="mega-menu-heading"><span className="eyebrow">The SAFYRA edit</span><h2>Dress slowly.<br />Wear the story.</h2><p>Discover considered pieces made in Lucknow, one stitch at a time.</p><Link to="/shop" onClick={() => setMenuOpen(false)} className="underlined-link" data-testid="mega-menu-shop-link">Explore all pieces →</Link></div>{menuGroups.map((group) => <div key={group.title} className="mega-group"><span className="eyebrow">{group.title}</span>{group.items.map((item) => <Link key={item} to={`/shop?search=${encodeURIComponent(item)}`} onClick={() => setMenuOpen(false)} data-testid={`mega-menu-link-${item.toLowerCase().replaceAll(" ", "-")}`}>{item}</Link>)}</div>)}<button className="mega-close" onClick={() => setMenuOpen(false)} aria-label="Close menu" data-testid="mega-menu-close"><X size={20} /></button></div></div>}
      </header>
      <a className="whatsapp-float" href={whatsappUrl("Hello SAFYRA, I would love help choosing a handcrafted piece.")} target="_blank" rel="noreferrer" data-testid="floating-whatsapp-link"><MessageCircle size={17} /> Talk to a Lucknow stylist</a>
    </>
  );
}