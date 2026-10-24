import { Heart, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import type { Product } from "@/lib/shop";
import { availableQuantity, defaultSetTypeId, findVariant, formatPrice, hasVariants, isMadeToOrder, isProductUnavailable, isVariantSellable, priceRange } from "@/lib/shop";
import { useShop } from "@/components/ShopProvider";
import SafeProductImage from "@/components/SafeProductImage";

export default function ProductCard({ product, index = 0 }: { product: Product; index?: number }) {
  const { addToCart, wishlistIds, toggleWishlist } = useShop();
  const saved = wishlistIds.includes(product.id);
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const unavailable = isProductUnavailable(product);
  const range = priceRange(product);
  // Quick add uses the first combination; it picks the first colour with stock in that size (null = sold out).
  const quickAddColor = (size: string): string | null => {
    if (!hasVariants(product)) return availableQuantity(product, size) > 0 ? "" : null;
    const setTypeId = defaultSetTypeId(product);
    if (!product.colors.length) return isVariantSellable(findVariant(product, setTypeId, size, "")) ? "" : null;
    return product.colors.find((color) => isVariantSellable(findVariant(product, setTypeId, size, color))) ?? null;
  };
  return (
    <article className="product-card" data-testid={`product-card-${index + 1}`}>
      <div className="product-image-wrap">
        <Link to={`/product/${product.slug}`} data-testid={`product-card-image-link-${index + 1}`}><SafeProductImage src={product.image_url} fallbackSrcs={product.image_urls} alt={product.title} productName={product.title} className="product-image product-image-primary" loading="lazy" decoding="async" sizes="(max-width: 767px) 50vw, 25vw" />{product.image_urls[1] && <SafeProductImage src={product.image_urls[1]} alt="" productName={product.title} hideWhenUnavailable className="product-image product-image-secondary" loading="lazy" decoding="async" sizes="25vw" />}</Link>
        <div className="product-badges">{product.new_arrival && <span className="badge badge-ink">New</span>}{product.availability === "Made to order" && <span className="badge badge-neutral">Made to order</span>}</div>
        <button className={`wishlist-button ${saved ? "is-saved" : ""}`} onClick={() => toggleWishlist(product.id)} aria-label={saved ? "Remove from wishlist" : "Save to wishlist"} data-testid={`product-card-wishlist-${index + 1}`}><Heart size={18} fill={saved ? "currentColor" : "none"} /></button>
        {!unavailable && <button className="quick-add" onClick={() => setQuickAddOpen((open) => !open)} data-testid={`product-card-quick-add-${index + 1}`}><Plus size={16} /> Choose size</button>}
        {quickAddOpen && <div className="quick-size-panel" data-testid={`product-card-size-panel-${index + 1}`}><span>Select a size</span><div>{product.sizes.map((size) => { const color = quickAddColor(size); return <button key={size} disabled={color === null} onClick={() => { if (color === null) return; addToCart(product, size, color || undefined, defaultSetTypeId(product)); setQuickAddOpen(false); }} data-testid={`product-card-size-${index + 1}-${size.toLowerCase()}`}>{size}</button>; })}</div></div>}
      </div>
      <div className="product-card-copy"><div className="product-meta">{product.fabric ? <span>{product.fabric}</span> : <span>{product.category}</span>}{product.craft && <span>Chikankari</span>}</div><Link to={`/product/${product.slug}`} className="product-title" data-testid={`product-card-title-${index + 1}`}>{product.title}</Link>{product.craft && <p className="product-craft">{product.craft}</p>}<div className="price-row"><span className="price" data-testid={`product-card-price-${index + 1}`}>{range.min !== range.max ? `From ${formatPrice(range.min)}` : formatPrice(range.min)}</span>{range.min === range.max && product.mrp && product.mrp > range.min && <span className="mrp">{formatPrice(product.mrp)}</span>}</div>{unavailable && <span className="sold-note" data-testid={`product-card-availability-${index + 1}`}>{hasVariants(product) && isMadeToOrder(product) && product.availability !== "Currently unavailable" ? "Fully booked · Notify me" : "YOU MISSED IT"}</span>}</div>
    </article>
  );
}