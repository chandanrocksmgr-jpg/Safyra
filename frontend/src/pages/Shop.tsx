import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Filter, SlidersHorizontal, X } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import ProductCard from "@/components/ProductCard";
import { apiGet } from "@/lib/api";
import type { Product } from "@/lib/shop";

const categories = ["All pieces", "Anarkali Sets", "Angrakha Suits", "Straight Kurtis", "Kurti Sets"];
const fabrics = ["All fabrics", "Pure Kota Doria", "Mul Chanderi", "Pure Muslin", "Pure Viscose"];

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const [filterOpen, setFilterOpen] = useState(false);
  const search = params.get("search") ?? "";
  const category = params.get("category") ?? "All pieces";
  const fabric = params.get("fabric") ?? "All fabrics";
  const sort = params.get("sort") ?? "featured";
  const { data: products = [], isPending, isError } = useQuery({ queryKey: ["products", search, category, fabric, sort], queryFn: () => apiGet<Product[]>(`/products?${new URLSearchParams({ ...(search ? { q: search } : {}), ...(category !== "All pieces" ? { category } : {}), ...(fabric !== "All fabrics" ? { fabric } : {}), sort })}`), retry: false });
  const activeFilters = [category !== "All pieces", fabric !== "All fabrics", Boolean(search)].filter(Boolean).length;
  const clearFilters = () => setParams({});
  const heading = search ? `Search results for “${search}”` : category !== "All pieces" ? category : "The SAFYRA edit";
  const curated = useMemo(() => products, [products]);

  return <div className="page-shell"><BrandHeader /><main className="shop-page"><div className="shop-heading"><div><span className="eyebrow">Handcrafted, considered</span><h1>{heading}</h1><p>{curated.length} pieces, made with attention.</p></div><button className="mobile-filter-button" onClick={() => setFilterOpen(true)} data-testid="mobile-filter-button"><SlidersHorizontal size={16} /> Filter {activeFilters > 0 && `(${activeFilters})`}</button></div><div className="shop-toolbar"><button className="filter-trigger" onClick={() => setFilterOpen((open) => !open)} data-testid="filter-trigger"><Filter size={16} /> Filters {activeFilters > 0 && <span>{activeFilters}</span>}</button><div className="toolbar-right"><label htmlFor="sort-select">Sort by</label><select id="sort-select" value={sort} onChange={(event) => setParams((current) => { current.set("sort", event.target.value); return current; })} data-testid="sort-select"><option value="featured">Featured</option><option value="newest">Newest arrivals</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></div></div><div className="shop-layout"><aside className={`filter-panel ${filterOpen ? "is-open" : ""}`}><div className="filter-panel-heading"><span className="eyebrow">Refine the edit</span><button className="icon-button mobile-only" onClick={() => setFilterOpen(false)} aria-label="Close filters" data-testid="filter-close"><X size={18} /></button></div><div className="filter-block"><span className="filter-label">Category</span>{categories.map((item) => <button key={item} className={category === item ? "filter-option is-active" : "filter-option"} onClick={() => { setParams((current) => { if (item === "All pieces") current.delete("category"); else current.set("category", item); return current; }); setFilterOpen(false); }} data-testid={`filter-category-${item.toLowerCase().replaceAll(" ", "-")}`}>{item}</button>)}</div><div className="filter-block"><span className="filter-label">Fabric</span>{fabrics.map((item) => <button key={item} className={fabric === item ? "filter-option is-active" : "filter-option"} onClick={() => { setParams((current) => { if (item === "All fabrics") current.delete("fabric"); else current.set("fabric", item); return current; }); setFilterOpen(false); }} data-testid={`filter-fabric-${item.toLowerCase().replaceAll(" ", "-")}`}>{item}</button>)}</div>{activeFilters > 0 && <button className="underlined-link" onClick={clearFilters} data-testid="clear-filters-button">Clear all filters</button>}</aside><div className="catalog-region">{isPending ? <div className="catalog-loading" data-testid="catalog-loading">Curating your edit…</div> : isError ? <div className="catalog-empty" data-testid="catalog-error"><h2>The edit is taking a moment</h2><p>Our catalogue is reconnecting. Please try again shortly.</p></div> : curated.length === 0 ? <div className="catalog-empty" data-testid="catalog-empty"><h2>No exact match yet.</h2><p>Try another fabric, silhouette or speak with our stylist.</p></div> : <div className="product-grid">{curated.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div>}</div></div></main></div>;
}