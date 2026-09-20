import { Heart, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import type { Product } from "@/lib/shop";
import { discountPercent, formatPrice } from "@/lib/shop";
import { useShop } from "@/components/ShopProvider";

export default function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  const { addToCart, wishlistIds, toggleWishlist } = useShop();
  const saved = wishlistIds.includes(product.id);
  const unavailable = product.availability === "Currently unavailable" || product.sizes.length === 0;
  return (
    <article className="product-card" data-testid={`product-card-${index + 1}`}>
      <div className="product-image-wrap">
        <Link to={`/product/${product.id}`} data-testid={`product-card-image-link-${index + 1}`}><img src={product.image_url} alt={product.title} className="product-image" loading="lazy" /></Link>
        <div className="product-badges">{product.new_arrival && <span className="badge badge-ink">New</span>}{product.mrp && product.mrp > product.price && <span className="badge badge-rose">{discountPercent(product)}% off</span>}</div>
        <button className={`wishlist-button ${saved ? "is-saved" : ""}`} onClick={() => toggleWishlist(product.id)} aria-label={saved ? "Remove from wishlist" : "Save to wishlist"} data-testid={`product-card-wishlist-${index + 1}`}><Heart size={18} fill={saved ? "currentColor" : "none"} /></button>
        {!unavailable && <button className="quick-add" onClick={() => addToCart(product)} data-testid={`product-card-quick-add-${index + 1}`}><Plus size={16} /> Quick add</button>}
      </div>
      <div className="product-card-copy"><div className="product-meta"><span>{product.collection}</span><span>{product.fabric}</span></div><Link to={`/product/${product.id}`} className="product-title" data-testid={`product-card-title-${index + 1}`}>{product.title}</Link><div className="price-row"><span className="price">{formatPrice(product.price)}</span>{product.mrp && product.mrp > product.price && <span className="mrp">{formatPrice(product.mrp)}</span>}</div><p className="product-craft">{product.craft}</p>{unavailable && <span className="sold-note" data-testid={`product-card-availability-${index + 1}`}>Enquire for the next making window</span>}</div>
    </article>
  );
}