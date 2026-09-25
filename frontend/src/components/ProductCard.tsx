import { Heart, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Product } from "@/lib/shop";
import { formatPrice } from "@/lib/shop";
import { useShop } from "@/components/ShopProvider";
import SafeProductImage from "@/components/SafeProductImage";

export default function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  const { addToCart, wishlistIds, toggleWishlist } = useShop();
  const saved = wishlistIds.includes(product.id);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const unavailable = product.availability === "Currently unavailable" || product.sizes.length === 0;
  return (
    <article className="product-card" data-testid={`product-card-${index + 1}`}>
      <div className="product-image-wrap">
        <Link to={`/product/${product.slug}`} data-testid={`product-card-image-link-${index + 1}`}><SafeProductImage src={product.image_url} alt={product.title} productName={product.title} className="product-image product-image-primary" loading="lazy" decoding="async" sizes="(max-width: 767px) 50vw, 25vw" />{product.image_urls[1] && <SafeProductImage src={product.image_urls[1]} alt="" productName={product.title} className="product-image product-image-secondary" loading="lazy" decoding="async" sizes="25vw" />}</Link>
        <div className="product-badges">{product.new_arrival && <span className="badge badge-ink">New</span>}{product.availability === "Made to order" && <span className="badge badge-neutral">Made to order</span>}</div>
        <button className={`wishlist-button ${saved ? "is-saved" : ""}`} onClick={() => toggleWishlist(product.id)} aria-label={saved ? "Remove from wishlist" : "Save to wishlist"} data-testid={`product-card-wishlist-${index + 1}`}><Heart size={18} fill={saved ? "currentColor" : "none"} /></button>
        {!unavailable && <button className="quick-add" onClick={() => setQuickAddOpen((open) => !open)} data-testid={`product-card-quick-add-${index + 1}`}><Plus size={16} /> Choose size</button>}
        {quickAddOpen && <div className="quick-size-panel" data-testid={`product-card-size-panel-${index + 1}`}><span>Select a size</span><div>{product.sizes.map((size) => <button key={size} onClick={() => { addToCart(product, size); setQuickAddOpen(false); }} data-testid={`product-card-size-${index + 1}-${size.toLowerCase()}`}>{size}</button>)}</div></div>}
      </div>
      <div className="product-card-copy"><div className="product-meta">{product.fabric ? <span>{product.fabric}</span> : <span>{product.category}</span>}{product.craft && <span>Chikankari</span>}</div><Link to={`/product/${product.slug}`} className="product-title" data-testid={`product-card-title-${index + 1}`}>{product.title}</Link>{product.craft && <p className="product-craft">{product.craft}</p>}<div className="price-row"><span className="price">{formatPrice(product.price)}</span>{product.mrp && product.mrp > product.price && <span className="mrp">{formatPrice(product.mrp)}</span>}</div>{unavailable && <span className="sold-note" data-testid={`product-card-availability-${index + 1}`}>OOPS, YOU MISSED IT</span>}</div>
    </article>
  );
}