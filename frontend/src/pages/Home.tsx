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
import { defaultHomepage, type CatalogGroup, type HomepageSettings } from "@/lib/cms";
import SafeProductImage from "@/components/SafeProductImage";

const categories = [
  { name: "Anarkali Sets", image: "https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=900", query: "Anarkali Sets" },
  { name: "Angrakha Suits", image: "https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=900", query: "Angrakha Suits" },
  { name: "Straight Kurtis", image: "https://safyra.co/cdn/shop/files/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg?v=1772205935&width=900", query: "Straight Kurtis" },
  { name: "Kurta & Pant Sets", query: "Kurta & Pant Sets" },
  { name: "Sarees", query: "Sarees" },
];

export default function Home() {
  const { data: products = [], isError } = useQuery({ queryKey: ["products", "home"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { data: groups = [] } = useQuery({ queryKey: ["catalog-groups", "public"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups"), retry: false });
  const { data: homepage } = useQuery({ queryKey: ["homepage"], queryFn: () => apiGet<HomepageSettings>("/homepage"), retry: false });
  const content = homepage ?? defaultHomepage;
  const newArrivals = products.filter((product) => product.new_arrival).slice(0, 4);
  const bestSellers = products.filter((product) => product.best_seller).slice(0, 4);
  const luxury = products.find((product) => product.collection === "Safyra Luxury");
  const managedCategories = groups.filter((group) => group.group_type === "category" && group.show_on_home);
  const visibleCategories = managedCategories.length ? managedCategories.map((group) => ({ name: group.name, image: group.image_url || products.find((product) => product.category === group.name)?.image_url, query: group.name })) : categories.filter((category) => products.some((product) => product.category === category.query));
  const managedCollections = groups.filter((group) => group.group_type === "collection" && group.show_on_home);
  const collections = managedCollections.length ? managedCollections.map((group) => ({ name: group.name, image: group.image_url || products.find((product) => product.collection === group.name)?.image_url || "" })) : [...new Map(products.filter((product) => product.collection).map((product) => [product.collection, { name: product.collection, image: product.image_url }])).values()];
  const homeStructuredData = {
    "@context": "https://schema.org", "@type": "WebSite", name: "SAFYRA CHIKANKARI", url: "https://safyra.co",
    potentialAction: { "@type": "SearchAction", target: "https://safyra.co/shop?search={search_term_string}", "query-input": "required name=search_term_string" },
  };

  return <div className="page-shell home-page"><Seo title="SAFYRA CHIKANKARI | Lucknowi Chikankari Anarkalis, Angrakhas & Kurtis" description="Shop SAFYRA Lucknowi Chikankari in Kota Doria, viscose and verified fabrics. Discover Anarkalis, Angrakhas, kurtis and SAFYRA Luxury." image="https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1800" structuredData={homeStructuredData} /><BrandHeader /><main>
    <section className="hero-section" data-testid="homepage-hero"><img src={content.hero.image_url} alt="SAFYRA handcrafted Lucknowi Chikankari" className="hero-image" fetchPriority="high" /><div className="hero-overlay" /><div className="hero-copy"><span className="eyebrow hero-eyebrow" data-testid="homepage-hero-eyebrow">{content.hero.eyebrow}</span><h1 data-testid="homepage-hero-title">{content.hero.title}<br /><em>{content.hero.emphasis}</em></h1><p data-testid="homepage-hero-body">{content.hero.body}</p><div className="hero-actions"><Link to={content.hero.primary_url} className="button button-light" data-testid="hero-shop-button">{content.hero.primary_label} <ArrowRight size={16} /></Link><Link to={content.hero.secondary_url} className="hero-text-link" data-testid="hero-secondary-link">{content.hero.secondary_label} <ArrowRight size={15} /></Link></div></div><div className="hero-note"><span>Lucknow</span><span>Chikankari · Kota Doria · Mukaish</span></div></section>

    {content.sections.show_new_arrivals && newArrivals.length > 0 && <section className="section product-section home-product-section" data-testid="homepage-new-arrivals"><div className="section-heading"><div><span className="eyebrow">{content.new_arrivals_eyebrow}</span><h2>{content.new_arrivals_title}</h2></div><Link to="/shop?new=true&sort=newest" className="underlined-link" data-testid="new-arrivals-link">View new arrivals <ArrowRight size={15} /></Link></div>{isError ? <div className="data-note" data-testid="catalog-error-note">The catalogue is reconnecting. Please try again shortly.</div> : <div className={`product-grid ${newArrivals.length < 4 ? "product-grid-compact" : ""}`}>{newArrivals.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div>}</section>}

    {content.sections.show_categories && visibleCategories.length > 0 && <section className="section category-section home-category-section" data-testid="homepage-categories"><div className="section-heading"><div><span className="eyebrow">{content.categories_eyebrow}</span><h2>{content.categories_title}</h2></div><Link to="/shop" className="underlined-link" data-testid="shop-by-category-link">Shop all <ArrowRight size={15} /></Link></div><div className="category-grid">{visibleCategories.map((category, index) => <Link to={`/shop?category=${encodeURIComponent(category.query)}`} className={`category-tile category-tile-${index + 1}`} key={category.name} data-testid={`category-tile-${index + 1}`}><SafeProductImage src={category.image} alt={`Shop SAFYRA ${category.name}`} productName={category.name} loading="lazy" /><div className="category-tile-copy"><h3>{category.name}</h3><ArrowRight size={18} /></div></Link>)}</div></section>}

    {content.sections.show_best_sellers && bestSellers.length > 0 && <section className="section product-section home-product-section" data-testid="homepage-bestsellers"><div className="section-heading"><div><span className="eyebrow">{content.best_sellers_eyebrow}</span><h2>{content.best_sellers_title}</h2></div><Link to="/shop?sort=best-selling" className="underlined-link" data-testid="best-sellers-link">Shop bestsellers <ArrowRight size={15} /></Link></div><div className="product-grid">{bestSellers.map((product, index) => <ProductCard key={product.id} product={product} index={index + 10} />)}</div></section>}

    {content.sections.show_luxury && luxury && <section className="luxury-feature" data-testid="homepage-luxury"><div className="luxury-image"><img src={luxury.image_url} alt={luxury.title} loading="lazy" /></div><div className="luxury-copy"><span className="eyebrow">{content.luxury_eyebrow}</span><h2>{luxury.title}</h2>{luxury.fabric && <p>{luxury.fabric} · {luxury.craft}</p>}<div className="luxury-details">{luxury.dispatch_days && <span><Check size={16} /> {luxury.availability} · {luxury.dispatch_days}</span>}<span>{luxury.price.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })}</span></div><Link to={`/product/${luxury.slug}`} className="button button-light" data-testid="luxury-feature-button">View the piece <ArrowRight size={16} /></Link></div></section>}

    {content.sections.show_collections && collections.length > 0 && <section className="section collection-section" data-testid="homepage-collections"><div className="section-heading"><div><span className="eyebrow">{content.collections_eyebrow}</span><h2>{content.collections_title}</h2></div><Link to="/shop" className="underlined-link" data-testid="collection-shop-all">View all pieces <ArrowRight size={15} /></Link></div><div className="collection-grid">{collections.map((collection, index) => <Link to={`/shop?collection=${encodeURIComponent(collection.name)}`} className="collection-card" key={collection.name} data-testid={`collection-card-${index + 1}`}><SafeProductImage src={collection.image} alt={`${collection.name} collection by SAFYRA`} productName={collection.name} loading="lazy" /><div><h3>{collection.name}</h3><small>Shop collection <ArrowRight size={13} /></small></div></Link>)}</div></section>}

    {content.sections.show_customer_love && <CustomerLove />}

    {content.sections.show_story && <section className="story-section compact-story" data-testid="homepage-story"><div className="story-images"><SafeProductImage src={content.story.image_url} alt="SAFYRA Lucknowi Chikankari craft story" productName="SAFYRA craft story" loading="lazy" /></div><div className="story-copy"><span className="eyebrow">{content.story.eyebrow}</span><h2>{content.story.title}</h2><p>{content.story.body}</p><Link to={content.story.link_url} className="button button-dark" data-testid="craft-story-shop-button">{content.story.link_label} <ArrowRight size={16} /></Link></div></section>}

    {content.sections.show_whatsapp && <section className="whatsapp-section" data-testid="homepage-whatsapp"><div><span className="eyebrow">{content.whatsapp_eyebrow}</span><h2>{content.whatsapp_title}</h2></div><a href={luxury ? productWhatsappUrl(luxury) : whatsappUrl("Hello SAFYRA, I would like help choosing a Chikankari piece.")} className="button button-light" target="_blank" rel="noreferrer" data-testid="home-whatsapp-button"><MessageCircle size={17} /> Chat on WhatsApp</a></section>}
  </main><footer className="site-footer"><div><Link to="/" className="wordmark footer-mark" data-testid="footer-brand-link"><span>SAFYRA</span><small>CHIKANKARI</small></Link><p>Lucknowi Chikankari across considered Indian silhouettes.</p></div><div className="footer-links"><Link to="/shop" data-testid="footer-shop-link">Shop all</Link><Link to="/wishlist" data-testid="footer-wishlist-link">Wishlist</Link><Link to="/login" data-testid="footer-account-link">Customer account</Link><Link to="/information#delivery" data-testid="footer-delivery-link">Dispatch & delivery</Link><Link to="/information#exchange" data-testid="footer-exchange-link">Exchange / store credit</Link><Link to="/information#faq" data-testid="footer-faq-link">FAQ</Link><a href={whatsappUrl("Hello SAFYRA, I need help with an order.")} target="_blank" rel="noreferrer" data-testid="footer-whatsapp-link">WhatsApp care</a></div><div className="footer-social"><Instagram size={17} /><span>@safyrachikankari</span></div></footer></div>;
}