import { useEffect, useMemo, useRef, useState, type TouchEvent as ReactTouchEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, BellRing, ChevronDown, ChevronLeft, ChevronRight, Heart, Maximize2, MessageCircle, Ruler, Share2, X } from "lucide-react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import BrandHeader from "@/components/BrandHeader";
import ProductImageViewer from "@/components/ProductImageViewer";
import ProductCard from "@/components/ProductCard";
import SafeProductImage from "@/components/SafeProductImage";
import Seo from "@/components/Seo";
import { useShop } from "@/components/ShopProvider";
import { apiGet } from "@/lib/api";
import WaitlistModal from "@/components/WaitlistModal";
import { availabilityLabel, availableQuantity, colorOption, colorSwatch, defaultSetTypeId, findVariant, formatPrice, galleryFor, hasVariants, isMadeToOrder, isProductUnavailable, isVariantSellable, productWhatsappUrl, selectionPrice, whatsappUrl, type Product } from "@/lib/shop";

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
  const [searchParams] = useSearchParams();
  // A shade can be deep-linked from a shop card: /product/slug?color=Blush%20petal
  const [selectedColor, setSelectedColor] = useState(searchParams.get("color") ?? "");
  const [selectedSetTypeId, setSelectedSetTypeId] = useState("");
  const [notifyOpen, setNotifyOpen] = useState(false);
  const [showSizeGuide, setShowSizeGuide] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  const [zoomOpen, setZoomOpen] = useState(false);
  const [recentIds, setRecentIds] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem("safyra-recent-products") ?? "[]") as string[]; } catch { return []; } });
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

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
  const color = selectedColor || product.colors[0] || "";
  // Each colour shows only the photos assigned to it in the admin; colours without photos fall back to the full gallery.
  const images = galleryFor(product, color);
  const showPrevImage = () => setSelectedImage((current) => (current - 1 + images.length) % images.length);
  const showNextImage = () => setSelectedImage((current) => (current + 1) % images.length);
  const handleGalleryTouchStart = (event: ReactTouchEvent) => { const touch = event.touches[0]; touchStartRef.current = { x: touch.clientX, y: touch.clientY }; };
  const handleGalleryTouchEnd = (event: ReactTouchEvent) => {
    const start = touchStartRef.current;
    touchStartRef.current = null;
    if (!start || images.length < 2) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < 40 || Math.abs(dx) < Math.abs(dy)) return;
    if (dx < 0) showNextImage(); else showPrevImage();
  };
  const hasColorGallery = Boolean(colorOption(product, color)?.image_urls.length);
  const supportsCustomDyeing = /\bdye(?:d|ing)?\b/i.test(product.customisation);
  const customDyeingUrl = whatsappUrl(`Hi SAFYRA, I’d like to enquire about custom dyeing for ${product.title}.`);
  // Unstitched / no-size products never ask for a size — their stock lives under size "".
  const requiresSize = product.sizes.length > 0;
  const variantInventory = hasVariants(product) && product.availability !== "Currently unavailable";
  const setTypeId = selectedSetTypeId || defaultSetTypeId(product);
  const sizeQuantity = (size: string) => availableQuantity(product, size, color, setTypeId);
  const colorHasStock = (item: string) => !variantInventory || (requiresSize ? product.sizes.some((size) => isVariantSellable(findVariant(product, setTypeId, size, item))) : isVariantSellable(findVariant(product, setTypeId, "", item)));
  const selectedSizeUnavailable = requiresSize ? (selectedSize ? sizeQuantity(selectedSize) < 1 : false) : sizeQuantity("") < 1;
  // Variant products stay selectable when sold out so customers can ask to be notified for that exact variant.
  const canNotify = variantInventory && (!requiresSize || Boolean(selectedSize)) && selectedSizeUnavailable;
  const canPurchase = (variantInventory || !unavailable) && (!requiresSize || Boolean(selectedSize)) && !selectedSizeUnavailable;
  const { price: displayPrice, mrp: displayMrp } = selectionPrice(product, setTypeId, requiresSize ? selectedSize : "", color);
  const soldOutLabel = isMadeToOrder(product) ? "Notify me" : "Sold out";
  const chooseColor = (next: string) => { setSelectedColor(next); setSelectedImage(0); };
  const addProduct = (destination?: "/checkout") => {
    if (requiresSize && !selectedSize) { toast.error("Please select a size first"); return; }
    if (canNotify) { setNotifyOpen(true); return; }
    if (selectedSizeUnavailable) { toast.error("That item is currently unavailable"); return; }
    addToCart(product, requiresSize ? selectedSize : "Free size", color || "As shown", setTypeId);
    if (destination) { closeDrawer(); navigate(destination); }
  };
  const detailGroups = [
    { title: "Product details", rows: [["Fabric", product.fabric], ["Embroidery / work", product.craft], ["Fit & silhouette", product.fit], ["Origin", product.origin]] },
    { title: "Measurements & construction", rows: [["Measurements", product.measurements], ["Transparency", product.transparency], ["Lining", product.lining]] },
    { title: "Care & making", rows: [["Care", product.care], ["Customisation", product.customisation], ["Availability", availabilityLabel(product.availability)], ["Dispatch", product.dispatch_days]] },
  ].map((group) => ({ ...group, rows: group.rows.filter(([, value]) => Boolean(value)) })).filter((group) => group.rows.length);
  const productStructuredData = {
    "@context": "https://schema.org", "@type": "Product", name: product.title, image: images,
    description: product.description || `${product.title} by SAFYRA CHIKANKARI`,
    brand: { "@type": "Brand", name: "SAFYRA CHIKANKARI" }, category: product.category,
    ...(product.fabric ? { material: product.fabric } : {}),
    offers: { "@type": "Offer", priceCurrency: "INR", price: product.price, url: `https://safyra.co/product/${product.slug}`, availability: unavailable ? "https://schema.org/OutOfStock" : product.availability === "Made to order" ? "https://schema.org/PreOrder" : "https://schema.org/InStock" },
  };

  return <div className="page-shell"><Seo title={`${product.title} | SAFYRA CHIKANKARI`} description={product.description || `${product.title} by SAFYRA CHIKANKARI. View verified fabric, work, sizes, availability and dispatch information.`} canonicalPath={`/product/${product.slug}`} image={product.image_url} structuredData={productStructuredData} /><BrandHeader /><main className="product-page"><nav className="product-breadcrumb" aria-label="Breadcrumb" data-testid="product-breadcrumb"><Link to="/">Home</Link><span>/</span><Link to="/shop">Shop</Link><span>/</span><Link to={`/shop?category=${encodeURIComponent(product.category)}`}>{product.category}</Link><span>/</span><span>{product.title}</span></nav><div className="product-detail-grid"><div className="product-gallery"><div className="gallery-main" onTouchStart={handleGalleryTouchStart} onTouchEnd={handleGalleryTouchEnd}><button onClick={() => setZoomOpen(true)} aria-label="Zoom product image" data-testid="product-image-zoom"><SafeProductImage src={images[selectedImage]} fallbackSrcs={images} alt={product.title} productName={product.title} /><Maximize2 size={18} /></button>{images.length > 1 && <><button type="button" className="gallery-nav-arrow gallery-nav-prev" onClick={(event) => { event.stopPropagation(); showPrevImage(); }} aria-label="Show previous image" data-testid="gallery-arrow-prev"><ChevronLeft size={20} /></button><button type="button" className="gallery-nav-arrow gallery-nav-next" onClick={(event) => { event.stopPropagation(); showNextImage(); }} aria-label="Show next image" data-testid="gallery-arrow-next"><ChevronRight size={20} /></button></>}</div><div className="mobile-gallery-scroll" data-testid="mobile-product-gallery" onTouchStart={handleGalleryTouchStart} onTouchEnd={handleGalleryTouchEnd}>{images.map((image, index) => <button type="button" key={image} className="mobile-gallery-item" onClick={() => { setSelectedImage(index); setZoomOpen(true); }} aria-label={`Open photo ${index + 1} of ${images.length} full screen`} data-testid={`mobile-gallery-image-${index + 1}`}><SafeProductImage src={image} alt={`${product.title} view ${index + 1}`} productName={product.title} hideWhenUnavailable loading={index ? "lazy" : "eager"} decoding="async" />{images.length > 1 && <span className="mobile-gallery-count">{index + 1} / {images.length}</span>}</button>)}</div><div className="gallery-thumbs">{images.map((image, index) => <button key={image} className={selectedImage === index ? "thumb is-active" : "thumb"} onClick={() => setSelectedImage(index)} aria-label={`Show image ${index + 1}`} data-testid={`product-thumbnail-${index + 1}`}><SafeProductImage src={image} alt="" productName={product.title} /></button>)}</div></div><div className="product-detail-copy"><div className="product-meta"><span>{product.collection}</span><span>{product.category}</span></div><h1 data-testid="product-title">{product.title}</h1>{unavailable && <div className="product-missed-label" data-testid="product-missed-label">You just missed it</div>}{(product.fabric || product.craft) && <div className="product-key-details" data-testid="product-key-details">{product.fabric && <span>{product.fabric}</span>}{product.craft && <span>{product.craft}</span>}</div>}{product.description && <div className="product-lede-wrap"><p className={product.description.length > 180 && !descExpanded ? "product-lede is-clamped" : "product-lede"} data-testid="product-description">{product.description}</p>{product.description.length > 180 && <button type="button" className="product-lede-toggle" onClick={() => setDescExpanded((value) => !value)} data-testid="product-description-toggle">{descExpanded ? "Read less" : "Read more"}</button>}</div>}<div className="detail-price" data-testid="product-price"><span>{formatPrice(displayPrice)}</span>{displayMrp && displayMrp > displayPrice && <del>{formatPrice(displayMrp)}</del>}</div><p className="tax-note">Shipping confirmed during checkout preparation</p><div className="availability-line" data-testid="product-availability"><span className={unavailable ? "availability-dot is-unavailable" : "availability-dot"} />{availabilityLabel(product.availability)}</div>{product.dispatch_days && <div className="dispatch-line" data-testid="product-dispatch">Making / dispatch: {product.dispatch_days}</div>}<div className="selection-group">{product.set_types.length > 0 && <div data-testid="product-combination-selector"><div className="selection-label"><span>Choose your set: <strong>{product.set_types.find((item) => item.id === setTypeId)?.name}</strong></span></div><div className="set-type-grid">{product.set_types.map((item) => { const offered = !variantInventory || product.variants.some((variant) => variant.set_type_id === item.id && isVariantSellable(variant)); return <button key={item.id} className={["set-type-option", setTypeId === item.id ? "is-selected" : "", offered ? "" : "is-sold-out"].filter(Boolean).join(" ")} onClick={() => setSelectedSetTypeId(item.id)} aria-pressed={setTypeId === item.id} data-testid={`set-type-option-${item.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}><strong>{item.name}</strong><small>{formatPrice(item.price)}{offered ? "" : ` · ${soldOutLabel}`}</small></button>; })}</div></div>}{product.colors.length > 0 && <div><div className="selection-label"><span>Colour: <strong>{color}</strong></span></div><div className="swatches" data-testid="product-color-swatches">{product.colors.map((item) => { const thumb = colorOption(product, item)?.image_urls[0]; return <button type="button" key={item} className={[color === item ? "swatch is-selected" : "swatch", colorHasStock(item) ? "" : "is-sold-out"].filter(Boolean).join(" ")} onClick={() => chooseColor(item)} aria-pressed={color === item} aria-label={`Select ${item}${colorHasStock(item) ? "" : " (sold out)"}`} title={colorHasStock(item) ? item : `${item} · ${soldOutLabel}`} data-testid={`color-option-${item.toLowerCase().replaceAll(" ", "-")}`}>{thumb ? <SafeProductImage src={thumb} alt={item} productName={`${product.title} ${item}`} loading="lazy" decoding="async" /> : <span style={{ backgroundColor: colorSwatch(product, item) }} />}</button>; })}</div>{hasColorGallery && <p className="selection-help" data-testid="color-gallery-note">Showing the {color} photos of this piece.</p>}{supportsCustomDyeing && <div className="custom-dyeing-option" data-testid="custom-dyeing-option"><span>Prefer another colour?</span><a href={customDyeingUrl} target="_blank" rel="noreferrer" className="underlined-link" data-testid="custom-dyeing-link">Ask about custom dyeing →</a></div>}</div>}{product.sizes.length > 0 && <div><div className="selection-label size-label-row"><span>Choose size {selectedSize && <strong>· {selectedSize}</strong>}</span>{requiresSize && product.size_guide_image && <button type="button" className="size-guide-link" onClick={() => setShowSizeGuide(true)} data-testid="size-guide-button"><Ruler size={13} /> Size guide <ChevronRight size={13} /></button>}</div><div className="size-grid">{product.sizes.map((item) => { const soldOut = sizeQuantity(item) < 1; return <button key={item} disabled={soldOut && !variantInventory} className={["size-option", selectedSize === item ? "is-selected" : "", soldOut && variantInventory ? "is-sold-out" : ""].filter(Boolean).join(" ")} onClick={() => setSelectedSize(item)} aria-label={soldOut ? `${item}, ${soldOutLabel.toLowerCase()}` : item} data-testid={`size-option-${item.toLowerCase()}`}><span className="size-option-name">{item}</span><small>{soldOut ? (variantInventory ? soldOutLabel : "Just missed") : availabilityLabel(product.availability)}</small></button>; })}</div>{!selectedSize && (variantInventory || !unavailable) && <p className="selection-help" data-testid="size-selection-help">Select a size to continue.</p>}{canNotify && <p className="selection-help variant-sold-out-note" data-testid="variant-sold-out-note">{isMadeToOrder(product) ? "This variant is fully booked right now. Leave your details and SAFYRA will contact you as soon as it can be made." : "This colour and size is sold out. Leave your details and we’ll let you know when it’s back."}</p>}</div>}</div><div className="product-actions">{canNotify ? <button className="button button-dark button-large" onClick={() => setNotifyOpen(true)} data-testid="variant-notify-button"><BellRing size={17} /> Notify me when available</button> : <button className="button button-dark button-large" disabled={!canPurchase} onClick={() => addProduct()} data-testid="add-to-cart-button">{unavailable && !variantInventory ? "You just missed it" : (!requiresSize || selectedSize) ? "Add to bag" : "Select a size"}</button>}{!canNotify && <button className="button button-outline button-large" disabled={!canPurchase} onClick={() => addProduct("/checkout")} data-testid="buy-now-button">Buy now</button>}<button className={`wishlist-product-button ${saved ? "is-saved" : ""}`} onClick={() => toggleWishlist(product.id)} aria-label={saved ? "Remove from wishlist" : "Add to wishlist"} data-testid="wishlist-toggle-button"><Heart size={19} fill={saved ? "currentColor" : "none"} /></button></div><a href={productWhatsappUrl(product)} target="_blank" rel="noreferrer" className="product-whatsapp" data-testid="whatsapp-inquiry-button"><MessageCircle size={17} /> Need help with size or customisation?</a>{detailGroups.length > 0 && <div className="detail-accordions">{detailGroups.map((group, index) => <details key={group.title} open={index === 0} data-testid={`product-accordion-${group.title.toLowerCase().replaceAll(" ", "-")}`}><summary>{group.title}<ChevronDown size={17} /></summary><div className="accordion-content">{group.rows.map(([label, value]) => <p key={label}><strong>{label}</strong>{value}</p>)}</div></details>)}</div>}<div className="product-share"><button className="text-button" onClick={() => { navigator.clipboard?.writeText(window.location.href); toast.success("Product link copied"); }} data-testid="product-share-button"><Share2 size={15} /> Share this piece</button></div></div></div>{images.length > 1 && <section className="product-detail-visual" data-testid="product-detail-visual"><div><span className="eyebrow">A closer look</span><h2>Details of {product.title}</h2><p>{[product.fabric, product.craft].filter(Boolean).join(" · ")}</p></div><div className="detail-image-grid">{images.slice(1, 3).map((image, index) => <button key={image} onClick={() => { setSelectedImage(index + 1); setZoomOpen(true); }} aria-label={`Open product detail image ${index + 1}`} data-testid={`product-detail-image-${index + 1}`}><SafeProductImage src={image} alt={`${product.title} detail ${index + 1}`} productName={product.title} loading="lazy" decoding="async" /></button>)}</div></section>}{product.video_urls?.length > 0 && <section className="product-films" data-testid="product-films"><div><span className="eyebrow">In motion</span><h2>See the piece move</h2></div><div className="product-film-grid">{product.video_urls.slice(0, 2).map((url, index) => <video key={url} src={url} poster={product.video_posters?.[index] || images[0] || product.image_url} controls preload="metadata" playsInline data-testid={`product-video-${index + 1}`} />)}</div></section>}{recommendations.complete.length > 0 && <RecommendationSection eyebrow="Approved pairings" title="Complete the Look" products={recommendations.complete} offset={30} />}<RecommendationSection eyebrow="More from this collection" title={product.collection} products={recommendations.collection} offset={40} link={`/shop?collection=${encodeURIComponent(product.collection)}`} /><RecommendationSection eyebrow="More from this fabric" title={product.fabric} products={recommendations.fabric} offset={50} link={`/shop?fabric=${encodeURIComponent(product.fabric)}`} /><RecommendationSection eyebrow="Similar silhouettes" title={`More ${product.category}`} products={recommendations.silhouette} offset={60} link={`/shop?category=${encodeURIComponent(product.category)}`} /><RecommendationSection eyebrow="Recently viewed" title="Continue discovering" products={recommendations.recent} offset={70} /></main>{(variantInventory || !unavailable) && <div className="mobile-sticky-add" data-testid="sticky-mobile-add-to-cart"><div><small>{requiresSize ? (selectedSize ? `Size ${selectedSize}${color ? ` · ${color}` : ""}` : "Choose a size") : color || "Ready to ship"}</small><strong>{formatPrice(displayPrice)}</strong></div><button className="button button-dark" disabled={!canPurchase && !canNotify} onClick={() => addProduct()} data-testid="sticky-mobile-add-button">{canNotify ? "Notify me" : (!requiresSize || selectedSize) ? "Add to bag" : "Select size"}</button></div>}{notifyOpen && createPortal(<WaitlistModal product={product} initial={{ setTypeId, size: selectedSize, color }} onClose={() => setNotifyOpen(false)} />, document.body)}{showSizeGuide && product.size_guide_image && <div className="modal-layer" data-testid="size-guide-modal"><button className="drawer-scrim" onClick={() => setShowSizeGuide(false)} aria-label="Close size guide" data-testid="size-guide-scrim" /><div className="modal-card size-guide-card"><div className="drawer-heading"><div><span className="eyebrow">Find your fit</span><h2>SAFYRA size guide</h2></div><button className="icon-button" onClick={() => setShowSizeGuide(false)} aria-label="Close size guide" data-testid="size-guide-close"><X size={20} /></button></div><SafeProductImage src={product.size_guide_image} alt="SAFYRA size guide" productName="SAFYRA size guide" /><a href={productWhatsappUrl(product)} target="_blank" rel="noreferrer" className="button button-outline button-full" data-testid="size-guide-whatsapp">Need help choosing your size?</a></div></div>}{zoomOpen && <ProductImageViewer images={images} initialIndex={selectedImage} title={product.title} onClose={() => setZoomOpen(false)} onIndexChange={setSelectedImage} />}</div>;
}