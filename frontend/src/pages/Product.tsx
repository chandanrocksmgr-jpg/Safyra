import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, Heart, Maximize2, MessageCircle, Ruler, Share2, X } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import BrandHeader from "@/components/BrandHeader";
import ProductCard from "@/components/ProductCard";
import SafeProductImage from "@/components/SafeProductImage";
import Seo from "@/components/Seo";
import { useShop } from "@/components/ShopProvider";
import { apiGet } from "@/lib/api";
import { availableQuantity, formatPrice, isProductUnavailable, productWhatsappUrl, whatsappUrl, type Product } from "@/lib/shop";

function RecommendationSection({ eyebrow, title, products, offset, link }: { eyebrow: string; title: string; products: Product[]; offset: number; link?: string }) {
  if (!products.length) return null;
  return <section className="section product-section related-section" data-testid={`recommendation-${eyebrow.toLowerCase().replaceAll(" ", "-")}`}><div className="section-heading"><div><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div>{link && <Link to={link} className="underlined-link" data-testid={`recommendation-link-${offset}`}>Explore all</Link>}</div><div className="product-grid">{products.slice(0, 4).map((item, index) => <ProductCard key={item.id} product={item} index={index + offset} />)}</div></section>;
}

export default function ProductPage() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { data: product, isPending, isError } = useQuery({ queryKey: ["product", productId], queryFn: () => apiGet<Product>(`/products/${productId}`), enabled: Boolean(productId), retry: false });
  const { data: allProducts = [] } = useQuery({ queryKey: ["products", "recommendations"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { addToCart, closeDrawer, wishlistIds, toggleWishlist } = useShop();
  const [selectedImage, setSelectedImage] = useState(0);
  const [selectedSize, setSelectedSize] = useState("");
  const [selectedColor, setSelectedColor] = useState("");
  const [showSizeGuide, setShowSizeGuide] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [recentIds, setRecentIds] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem("safyra-recent-products") ?? "[]") as string[]; } catch { return []; } });

  useEffect(() => {
    if (!product) return;
    const next = [product.id, ...recentIds.filter((id) => id !== product.id)].slice(0, 6);
    localStorage.setItem("safyra-recent-products", JSON.stringify(next));
    if (!recentIds.includes(product.id)) setRecentIds(next);
  }, [product, recentIds]);

  const recommendations = useMemo(() => {
    if (!product) return { complete: [], collection: [], fabric: [], silhouette: [], recent: [] };
    const withoutCurrent = allProducts.filter((item) => item.id !== product.id);
    const collection = withoutCurrent.filter((item) => item.collection === product.collection);
    const fabric = withoutCurrent.filter((item) => item.fabric && item.fabric === product.fabric && !collection.some((match) => match.id === item.id));
    const silhouette = withoutCurrent.filter((item) => item.category === product.category && !collection.some((match) => match.id === item.id) && !fabric.some((match) => match.id === item.id));
    return {
      complete: product.complete_look_ids.map((id) => allProducts.find((item) => item.id === id)).filter((item): item is Product => Boolean(item)),
      collection,
      fabric,
      silhouette,
      recent: recentIds.flatMap((id) => { const item = allProducts.find((candidate) => candidate.id === id); return item && item.id !== product.id ? [item] : []; }),
    };
  }, [allProducts, product, recentIds]);

  if (isPending) return <div className="page-shell"><BrandHeader /><div className="product-loading" data-testid="product-loading">Preparing the details…</div></div>;
  if (isError || !product) return <div className="page-shell"><BrandHeader /><div className="catalog-empty"><h1>We couldn’t find that piece.</h1><Link to="/shop" className="button button-dark" data-testid="product-not-found-shop-link">Return to the edit</Link></div></div>;

  const saved = wishlistIds.includes(product.id);
  const unavailable = isProductUnavailable(product);
  const images = product.image_urls.length ? product.image_urls : [product.image_url];
  const color = selectedColor || product.colors[0] || "";
  const supportsCustomDyeing = /\bdye(?:d|ing)?\b/i.test(product.customisation);
  const customDyeingUrl = whatsappUrl(`Hi SAFYRA, I’d like to enquire about custom dyeing for ${product.title}.`);
  const selectedSizeUnavailable = selectedSize ? availableQuantity(product, selectedSize) < 1 : false;
  const canPurchase = !unavailable && Boolean(selectedSize) && !selectedSizeUnavailable;
  const addProduct = (destination?: "/checkout") => {
    if (!selectedSize) { toast.error("Please select a size first"); return; }
    if (selectedSizeUnavailable) { toast.error("That size is currently unavailable"); return; }
    addToCart(product, selectedSize, color || "As shown");
    if (destination) { closeDrawer(); navigate(destination); }
  };
  const detailGroups = [
    { title: "Product details", rows: [["Fabric", product.fabric], ["Embroidery / work", product.craft], ["Fit & silhouette", product.fit], ["Origin", product.origin]] },
    { title: "Measurements & construction", rows: [["Measurements", product.measurements], ["Transparency", product.transparency], ["Lining", product.lining]] },
    { title: "Care & making", rows: [["Care", product.care], ["Customisation", product.customisation], ["Availability", product.availability], ["Dispatch", product.dispatch_days]] },
  ].map((group) => ({ ...group, rows: group.rows.filter(([, value]) => Boolean(value)) })).filter((group) => group.rows.length);
  const productStructuredData = {
    "@context": "https://schema.org", "@type": "Product", name: product.title, image: images,
    description: product.description || `${product.title} by SAFYRA CHIKANKARI`,
    brand: { "@type": "Brand", name: "SAFYRA CHIKANKARI" }, category: product.category,
    ...(product.fabric ? { material: product.fabric } : {}),
    offers: { "@type": "Offer", priceCurrency: "INR", price: product.price, url: `https://safyra.co/product/${product.slug}`, availability: unavailable ? "https://schema.org/OutOfStock" : product.availability === "Made to order" ? "https://schema.org/PreOrder" : "https://schema.org/InStock" },
  };

  return <div className="page-shell"><Seo title={`${product.title} | SAFYRA CHIKANKARI`} description={product.description || `${product.title} by SAFYRA CHIKANKARI. View verified fabric, work, sizes, availability and dispatch information.`} canonicalPath={`/product/${product.slug}`} image={product.image_url} structuredData={productStructuredData} /><BrandHeader /><main className="product-page"><nav className="product-breadcrumb" aria-label="Breadcrumb" data-testid="product-breadcrumb"><Link to="/">Home</Link><span>/</span><Link to="/shop">Shop</Link><span>/</span><Link to={`/shop?category=${encodeURIComponent(product.category)}`}>{product.category}</Link><span>/</span><span>{product.title}</span></nav><div className="product-detail-grid"><div className="product-gallery"><div className="gallery-main"><button onClick={() => setZoomOpen(true)} aria-label="Zoom product image" data-testid="product-image-zoom"><SafeProductImage src={images[selectedImage]} alt={product.title} productName={product.title} /><Maximize2 size={18} /></button></div><div className="mobile-gallery-scroll" data-testid="mobile-product-gallery">{images.map((image, index) => <SafeProductImage key={image} src={image} alt={`${product.title} view ${index + 1}`} productName={product.title} loading={index ? "lazy" : "eager"} decoding="async" />)}</div><div className="gallery-thumbs">{images.map((image, index) => <button key={image} className={selectedImage === index ? "thumb is-active" : "thumb"} onClick={() => setSelectedImage(index)} aria-label={`Show image ${index + 1}`} data-testid={`product-thumbnail-${index + 1}`}><SafeProductImage src={image} alt="" productName={product.title} /></button>)}</div></div><div className="product-detail-copy"><div className="product-meta"><span>{product.collection}</span><span>{product.category}</span></div><h1 data-testid="product-title">{product.title}</h1>{(product.fabric || product.craft) && <div className="product-key-details" data-testid="product-key-details">{product.fabric && <span>{product.fabric}</span>}{product.craft && <span>{product.craft}</span>}</div>}{product.description && <p className="product-lede" data-testid="product-description">{product.description}</p>}<div className="detail-price" data-testid="product-price"><span>{formatPrice(product.price)}</span>{product.mrp && product.mrp > product.price && <del>{formatPrice(product.mrp)}</del>}</div><p className="tax-note">Taxes included · Shipping confirmed during checkout preparation</p><div className="availability-line" data-testid="product-availability"><span className={unavailable ? "availability-dot is-unavailable" : "availability-dot"} />{product.availability}</div>{product.dispatch_days && <div className="dispatch-line" data-testid="product-dispatch">Making / dispatch: {product.dispatch_days}</div>}<div className="selection-group">{product.colors.length > 0 && <div><div className="selection-label"><span>Colour: <strong>{color}</strong></span></div><div className="swatches">{product.colors.map((item) => <button key={item} className={color === item ? "swatch is-selected" : "swatch"} onClick={() => setSelectedColor(item)} aria-label={`Select ${item}`} data-testid={`color-option-${item.toLowerCase().replaceAll(" ", "-")}`}><span style={{ backgroundColor: item.toLowerCase().includes("rose") || item.toLowerCase().includes("blush") || item.toLowerCase().includes("red") ? "#ad746f" : item.toLowerCase().includes("green") ? "#66765e" : item.toLowerCase().includes("blue") ? "#91abbc" : "#e9dfc9" }} /></button>)}</div>{supportsCustomDyeing && <div className="custom-dyeing-option" data-testid="custom-dyeing-option"><span>Prefer another colour?</span><a href={customDyeingUrl} target="_blank" rel="noreferrer" className="underlined-link" data-testid="custom-dyeing-link">Ask about custom dyeing →</a></div>}</div>}{product.sizes.length > 0 && <div><div className="selection-label"><span>Choose size {selectedSize && <strong>· {selectedSize}</strong>}</span>{product.size_guide_image && <button className="size-guide-trigger" onClick={() => setShowSizeGuide(true)} data-testid="size-guide-button"><Ruler size={14} /> Size guide</button>}</div><div className="size-grid">{product.sizes.map((item) => { const disabled = Object.hasOwn(product.stock_by_size, item) && product.stock_by_size[item] <= 0; return <button key={item} disabled={disabled} className={selectedSize === item ? "size-option is-selected" : "size-option"} onClick={() => setSelectedSize(item)} data-testid={`size-option-${item.toLowerCase()}`}>{item}<small>{disabled ? "Unavailable" : product.availability}</small></button>; })}</div>{!selectedSize && !unavailable && <p className="selection-help" data-testid="size-selection-help">Select a size to continue.</p>}</div>}</div><div className="product-actions"><button className="button button-dark button-large" disabled={!canPurchase} onClick={() => addProduct()} data-testid="add-to-cart-button">{unavailable ? "Currently unavailable" : selectedSize ? "Add to bag" : "Select a size"}</button><button className="button button-outline button-large" disabled={!canPurchase} onClick={() => addProduct("/checkout")} data-testid="buy-now-button">Buy now</button><button className={`wishlist-product-button ${saved ? "is-saved" : ""}`} onClick={() => toggleWishlist(product.id)} aria-label={saved ? "Remove from wishlist" : "Add to wishlist"} data-testid="wishlist-toggle-button"><Heart size={19} fill={saved ? "currentColor" : "none"} /></button></div><a href={productWhatsappUrl(product)} target="_blank" rel="noreferrer" className="product-whatsapp" data-testid="whatsapp-inquiry-button"><MessageCircle size={17} /> Need help with size or customisation?</a>{detailGroups.length > 0 && <div className="detail-accordions">{detailGroups.map((group, index) => <details key={group.title} open={index === 0} data-testid={`product-accordion-${group.title.toLowerCase().replaceAll(" ", "-")}`}><summary>{group.title}<ChevronDown size={17} /></summary><div className="accordion-content">{group.rows.map(([label, value]) => <p key={label}><strong>{label}</strong>{value}</p>)}</div></details>)}</div>}<div className="product-share"><button className="text-button" onClick={() => { navigator.clipboard?.writeText(window.location.href); toast.success("Product link copied"); }} data-testid="product-share-button"><Share2 size={15} /> Share this piece</button></div></div></div>{images.length > 1 && <section className="product-detail-visual" data-testid="product-detail-visual"><div><span className="eyebrow">A closer look</span><h2>Details of {product.title}</h2><p>{[product.fabric, product.craft].filter(Boolean).join(" · ")}</p></div><div className="detail-image-grid">{images.slice(1, 3).map((image, index) => <button key={image} onClick={() => { setSelectedImage(index + 1); setZoomOpen(true); }} aria-label={`Open product detail image ${index + 1}`} data-testid={`product-detail-image-${index + 1}`}><SafeProductImage src={image} alt={`${product.title} detail ${index + 1}`} productName={product.title} loading="lazy" decoding="async" /></button>)}</div></section>}{recommendations.complete.length > 0 && <RecommendationSection eyebrow="Approved pairings" title="Complete the Look" products={recommendations.complete} offset={30} />}<RecommendationSection eyebrow="More from this collection" title={product.collection} products={recommendations.collection} offset={40} link={`/shop?collection=${encodeURIComponent(product.collection)}`} /><RecommendationSection eyebrow="More from this fabric" title={product.fabric} products={recommendations.fabric} offset={50} link={`/shop?fabric=${encodeURIComponent(product.fabric)}`} /><RecommendationSection eyebrow="Similar silhouettes" title={`More ${product.category}`} products={recommendations.silhouette} offset={60} link={`/shop?category=${encodeURIComponent(product.category)}`} /><RecommendationSection eyebrow="Recently viewed" title="Continue discovering" products={recommendations.recent} offset={70} /></main>{!unavailable && <div className="mobile-sticky-add" data-testid="sticky-mobile-add-to-cart"><div><small>{selectedSize ? `Size ${selectedSize}` : "Choose a size"}</small><strong>{formatPrice(product.price)}</strong></div><button className="button button-dark" disabled={!canPurchase} onClick={() => addProduct()} data-testid="sticky-mobile-add-button">{selectedSize ? "Add to bag" : "Select size"}</button></div>}{showSizeGuide && product.size_guide_image && <div className="modal-layer" data-testid="size-guide-modal"><button className="drawer-scrim" onClick={() => setShowSizeGuide(false)} aria-label="Close size guide" data-testid="size-guide-scrim" /><div className="modal-card size-guide-card"><div className="drawer-heading"><div><span className="eyebrow">Find your fit</span><h2>SAFYRA size guide</h2></div><button className="icon-button" onClick={() => setShowSizeGuide(false)} aria-label="Close size guide" data-testid="size-guide-close"><X size={20} /></button></div><SafeProductImage src={product.size_guide_image} alt="SAFYRA size guide" productName="SAFYRA size guide" /><a href={productWhatsappUrl(product)} target="_blank" rel="noreferrer" className="button button-outline button-full" data-testid="size-guide-whatsapp">Need help choosing your size?</a></div></div>}{zoomOpen && <div className="modal-layer image-zoom-layer" data-testid="product-zoom-modal"><button className="drawer-scrim" onClick={() => setZoomOpen(false)} aria-label="Close image zoom" data-testid="product-zoom-scrim" /><div className="zoom-card"><button className="zoom-close" onClick={() => setZoomOpen(false)} aria-label="Close image zoom" data-testid="product-zoom-close"><X size={20} /></button><SafeProductImage src={images[selectedImage]} alt={product.title} productName={product.title} /></div></div>}</div>;
}