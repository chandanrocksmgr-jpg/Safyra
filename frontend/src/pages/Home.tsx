import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, Instagram, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import CustomerLove from "@/components/CustomerLove";
import ProductCard from "@/components/ProductCard";
import Seo from "@/components/Seo";
import { apiGet } from "@/lib/api";
import type { Product } from "@/lib/shop";
import { productWhatsappUrl, whatsappUrl } from "@/lib/shop";

const categories = [
  { name: "Anarkali Sets", image: "https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=900", query: "Anarkali Sets" },
  { name: "Angrakha Suits", image: "https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=900", query: "Angrakha Suits" },
  { name: "Straight Kurtis", image: "https://safyra.co/cdn/shop/files/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg?v=1772205935&width=900", query: "Straight Kurtis" },
  { name: "Kurta & Pant Sets", query: "Kurta & Pant Sets" },
  { name: "Sarees", query: "Sarees" },
];

export default function Home() {
  const { data: products = [], isError } = useQuery({ queryKey: ["products", "home"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const newArrivals = products.filter((product) => product.new_arrival).slice(0, 4);
  const bestSellers = products.filter((product) => product.best_seller).slice(0, 4);
  const luxury = products.find((product) => product.collection === "Safyra Luxury");
  const collections = [...new Map(products.filter((product) => product.collection).map((product) => [product.collection, product])).values()];
  const homeStructuredData = {
    "@context": "https://schema.org", "@type": "WebSite", name: "SAFYRA CHIKANKARI", url: "https://safyra.co",
    potentialAction: { "@type": "SearchAction", target: "https://safyra.co/shop?search={search_term_string}", "query-input": "required name=search_term_string" },
  };

  return <div className="page-shell home-page"><Seo title="SAFYRA CHIKANKARI | Lucknowi Chikankari Anarkalis, Angrakhas & Kurtis" description="Shop SAFYRA Lucknowi Chikankari in Kota Doria, viscose and verified fabrics. Discover Anarkalis, Angrakhas, kurtis and SAFYRA Luxury." image="https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1800" structuredData={homeStructuredData} /><BrandHeader /><main>
    <section className="hero-section"><img src="https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1800" alt="SAFYRA Vaaya Pure Kota Doria Chikankari Anarkali" className="hero-image" fetchPriority="high" /><div className="hero-overlay" /><div className="hero-copy"><span className="eyebrow hero-eyebrow">Lucknowi Chikankari</span><h1>Chikankari,<br /><em>made to be remembered.</em></h1><p>Handcrafted Chikankari, created by skilled artisans in Lucknow.</p><div className="hero-actions"><Link to="/shop?new=true&sort=newest" className="button button-light" data-testid="hero-shop-button">Shop new arrivals <ArrowRight size={16} /></Link>{bestSellers.length ? <Link to="/shop?sort=best-selling" className="hero-text-link" data-testid="hero-bestsellers-link">Shop bestsellers <ArrowRight size={15} /></Link> : <Link to="/shop?collection=Safyra%20Luxury" className="hero-text-link" data-testid="hero-luxury-link">Shop SAFYRA Luxury <ArrowRight size={15} /></Link>}</div></div><div className="hero-note"><span>Lucknow</span><span>Chikankari · Kota Doria · Mukaish</span></div></section>

    {newArrivals.length > 0 && <section className="section product-section home-product-section"><div className="section-heading"><div><span className="eyebrow">Just added</span><h2>Shop new arrivals</h2></div><Link to="/shop?new=true&sort=newest" className="underlined-link" data-testid="new-arrivals-link">View new arrivals <ArrowRight size={15} /></Link></div>{isError ? <div className="data-note" data-testid="catalog-error-note">The catalogue is reconnecting. Please try again shortly.</div> : <div className={`product-grid ${newArrivals.length < 4 ? "product-grid-compact" : ""}`}>{newArrivals.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div>}</section>}

    <section className="section category-section home-category-section"><div className="section-heading"><div><span className="eyebrow">Choose a silhouette</span><h2>Shop by category</h2></div><Link to="/shop" className="underlined-link" data-testid="shop-by-category-link">Shop all <ArrowRight size={15} /></Link></div><div className="category-grid">{categories.map((category, index) => { const image = category.image ?? products.find((product) => product.category === category.query)?.image_url; return <Link to={`/shop?category=${encodeURIComponent(category.query)}`} className={`category-tile category-tile-${index + 1}`} key={category.name} data-testid={`category-tile-${index + 1}`}>{image && <img src={image} alt={`Shop SAFYRA ${category.name}`} loading="lazy" />}<div className="category-tile-copy"><h3>{category.name}</h3><ArrowRight size={18} /></div></Link>; })}</div></section>

    {bestSellers.length > 0 && <section className="section product-section home-product-section"><div className="section-heading"><div><span className="eyebrow">Customer favourites</span><h2>Bestsellers</h2></div><Link to="/shop?sort=best-selling" className="underlined-link" data-testid="best-sellers-link">Shop bestsellers <ArrowRight size={15} /></Link></div><div className="product-grid">{bestSellers.map((product, index) => <ProductCard key={product.id} product={product} index={index + 10} />)}</div></section>}

    {luxury && <section className="luxury-feature"><div className="luxury-image"><img src={luxury.image_url} alt={luxury.title} loading="lazy" /></div><div className="luxury-copy"><span className="eyebrow">SAFYRA Luxury</span><h2>{luxury.title}</h2>{luxury.fabric && <p>{luxury.fabric} · {luxury.craft}</p>}<div className="luxury-details">{luxury.dispatch_days && <span><Check size={16} /> {luxury.availability} · {luxury.dispatch_days}</span>}<span>{luxury.price.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })}</span></div><Link to={`/product/${luxury.slug}`} className="button button-light" data-testid="luxury-feature-button">View the piece <ArrowRight size={16} /></Link></div></section>}

    {collections.length > 0 && <section className="section collection-section"><div className="section-heading"><div><span className="eyebrow">Current collections</span><h2>Shop by collection</h2></div><Link to="/shop" className="underlined-link" data-testid="collection-shop-all">View all pieces <ArrowRight size={15} /></Link></div><div className="collection-grid">{collections.map((product, index) => <Link to={`/shop?collection=${encodeURIComponent(product.collection)}`} className="collection-card" key={product.collection} data-testid={`collection-card-${index + 1}`}><img src={product.image_url} alt={`${product.collection} collection by SAFYRA`} loading="lazy" /><div><h3>{product.collection}</h3><small>Shop collection <ArrowRight size={13} /></small></div></Link>)}</div></section>}

    <CustomerLove />

    <section className="fit-service"><div><span className="eyebrow">Extended sizes</span><h2>Find your SAFYRA size.</h2><p>Selected SAFYRA silhouettes are available from XS to 3XL. Each product page shows the available sizes and size guide.</p><Link to="/shop?size=3XL" className="underlined-link" data-testid="extended-sizes-shop-link">Shop extended sizes <ArrowRight size={15} /></Link></div><img src="https://safyra.co/cdn/shop/files/rn-image_picker_lib_temp_b45b8222-b248-4367-890e-33fce779156b.png?v=1768253915&width=1200" alt="SAFYRA Aira Pure Kota Doria Angrakha" loading="lazy" /></section>

    <section className="story-section compact-story"><div className="story-images"><img src="https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=1200" alt="SAFYRA Aira Angrakha styled in Lucknowi Chikankari" loading="lazy" /></div><div className="story-copy"><span className="eyebrow">SAFYRA, Lucknow</span><h2>A focused Chikankari wardrobe.</h2><p>SAFYRA works with Lucknowi Chikankari across Indian silhouettes and verified fabrics. Each product page brings the textile, embroidery description, fit and making information together in one place.</p><Link to="/information#craft" className="button button-dark" data-testid="craft-story-shop-button">About the craft <ArrowRight size={16} /></Link></div></section>

    <section className="whatsapp-section"><div><span className="eyebrow">Customer care</span><h2>Personal help,<br /><em>before you order.</em></h2></div><a href={luxury ? productWhatsappUrl(luxury) : whatsappUrl("Hello SAFYRA, I would like help choosing a Chikankari piece.")} className="button button-light" target="_blank" rel="noreferrer" data-testid="home-whatsapp-button"><MessageCircle size={17} /> Chat on WhatsApp</a></section>
  </main><footer className="site-footer"><div><Link to="/" className="wordmark footer-mark" data-testid="footer-brand-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link><p>Lucknowi Chikankari across considered Indian silhouettes.</p></div><div className="footer-links"><Link to="/shop" data-testid="footer-shop-link">Shop all</Link><Link to="/wishlist" data-testid="footer-wishlist-link">Wishlist</Link><Link to="/login" data-testid="footer-account-link">Customer account</Link><Link to="/information#delivery" data-testid="footer-delivery-link">Dispatch & delivery</Link><Link to="/information#exchange" data-testid="footer-exchange-link">Exchange / store credit</Link><Link to="/information#faq" data-testid="footer-faq-link">FAQ</Link><a href={whatsappUrl("Hello SAFYRA, I need help with an order.")} target="_blank" rel="noreferrer" data-testid="footer-whatsapp-link">WhatsApp care</a></div><div className="footer-social"><Instagram size={17} /><span>@safyrachikankari</span></div></footer></div>;
}