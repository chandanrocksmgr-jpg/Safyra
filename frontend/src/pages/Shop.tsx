import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Filter, SlidersHorizontal, X } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import ProductCard from "@/components/ProductCard";
import { apiGet } from "@/lib/api";
import type { Product, ProductFacets } from "@/lib/shop";

type FilterKey = "category" | "collection" | "fabric" | "size" | "color" | "craft" | "availability";
const splitParam = (value: string | null) => value ? value.split(",").filter(Boolean) : [];
const testSlug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, "-");

function FilterGroup({ title, filterKey, values, selected, onToggle }: { title: string; filterKey: FilterKey; values: string[]; selected: string[]; onToggle: (key: FilterKey, value: string) => void }) {
  if (!values.length) return null;
  return <details className="filter-block" open={title === "Size"}><summary className="filter-label">{title}<ChevronDown size={15} /></summary>{values.map((item) => <label className="filter-check" key={item} data-testid={`filter-${filterKey}-${testSlug(item)}`}><input type="checkbox" checked={selected.includes(item)} onChange={() => onToggle(filterKey, item)} /><span>{item}</span></label>)}</details>;
}

export default function Shop() {
  const [params, setParams] = useSearchParams();
  const filterOpen = params.get("filters") === "open";
  const search = params.get("search") ?? "";
  const sort = params.get("sort") ?? "featured";
  const minPrice = params.get("min_price") ?? "";
  const maxPrice = params.get("max_price") ?? "";
  const selected = {
    category: splitParam(params.get("category")), collection: splitParam(params.get("collection")),
    fabric: splitParam(params.get("fabric")), size: splitParam(params.get("size")), color: splitParam(params.get("color")),
    craft: splitParam(params.get("craft")), availability: splitParam(params.get("availability")),
  };
  const { data: facets } = useQuery({ queryKey: ["product-facets"], queryFn: () => apiGet<ProductFacets>("/products/facets"), retry: false });
  const query = new URLSearchParams();
  if (search) query.set("q", search);
  if (params.get("new") === "true") query.set("new_arrival", "true");
  Object.entries(selected).forEach(([key, values]) => { if (values.length) query.set(key, values.join(",")); });
  if (minPrice) query.set("min_price", minPrice);
  if (maxPrice) query.set("max_price", maxPrice);
  query.set("sort", sort);
  const { data: products = [], isPending, isError } = useQuery({ queryKey: ["products", query.toString()], queryFn: () => apiGet<Product[]>(`/products?${query}`), placeholderData: (previous) => previous, retry: false });
  const { data: allProducts = [] } = useQuery({ queryKey: ["products", "all-for-zero"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const activeFilters = Object.values(selected).reduce((total, values) => total + values.length, 0) + (search ? 1 : 0) + (minPrice || maxPrice ? 1 : 0);
  const heading = search ? `Results for “${search}”` : params.get("new") === "true" ? "New Arrivals" : selected.collection[0] ?? selected.category[0] ?? "The SAFYRA edit";
  const productCountLabel = isPending ? "Curating pieces…" : `${products.length} ${products.length === 1 ? "piece" : "pieces"}`;

  const updateParams = (change: (next: URLSearchParams) => void) => {
    const next = new URLSearchParams(window.location.search);
    change(next);
    setParams(next);
  };
  const toggleFilter = (key: FilterKey, value: string) => updateParams((nextParams) => {
    const values = splitParam(nextParams.get(key));
    const next = values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
    if (next.length) nextParams.set(key, next.join(",")); else nextParams.delete(key);
  });
  const closeFilters = () => updateParams((next) => next.delete("filters"));
  const clearFilters = () => setParams(new URLSearchParams());

  const sortSelect = (testId: string) => <select value={sort} onChange={(event) => updateParams((next) => next.set("sort", event.target.value))} data-testid={testId}><option value="featured">Featured</option><option value="newest">Newest</option>{facets?.has_best_sellers && <option value="best-selling">Best Selling</option>}<option value="price-low">Price: Low to High</option><option value="price-high">Price: High to Low</option></select>;

  return <div className="page-shell"><BrandHeader /><main className="shop-page">
    <div className="shop-heading"><div><span className="eyebrow">Handcrafted, considered</span><h1>{heading}</h1><p data-testid="shop-product-count">{productCountLabel}</p></div></div>
    <div className="shop-toolbar">
      <button className="filter-trigger" onClick={() => updateParams((next) => next.set("filters", "open"))} data-testid="filter-trigger"><Filter size={16} /> Filters {activeFilters > 0 && <span>{activeFilters}</span>}</button>
      <div className="mobile-shop-controls"><button onClick={() => updateParams((next) => next.set("filters", "open"))} data-testid="mobile-filter-button"><SlidersHorizontal size={16} /> Filter {activeFilters > 0 && `(${activeFilters})`}</button><label>Sort{sortSelect("mobile-sort-select")}</label></div>
      <div className="toolbar-right"><label>Sort by</label>{sortSelect("sort-select")}</div>
    </div>
    {activeFilters > 0 && <div className="active-filter-row" data-testid="active-filters">
      {Object.entries(selected).flatMap(([key, values]) => values.map((value) => <button key={`${key}-${value}`} onClick={() => toggleFilter(key as FilterKey, value)} data-testid={`active-filter-${key}-${testSlug(value)}`}>{value} <X size={12} /></button>))}
      {(minPrice || maxPrice) && <button onClick={() => updateParams((next) => { next.delete("min_price"); next.delete("max_price"); })} data-testid="active-filter-price">₹{minPrice || facets?.price_min}–₹{maxPrice || facets?.price_max} <X size={12} /></button>}
      <button className="clear-filter-chip" onClick={clearFilters} data-testid="clear-filters-button">Clear all</button>
    </div>}
    <div className="shop-layout">
      {filterOpen && <button className="filter-scrim" onClick={closeFilters} aria-label="Close filters" data-testid="filter-scrim" />}
      <aside className={`filter-panel ${filterOpen ? "is-open" : ""}`} data-testid="filter-panel">
        <div className="filter-panel-heading"><span className="eyebrow">Refine the edit</span><button className="icon-button mobile-only" onClick={closeFilters} aria-label="Close filters" data-testid="filter-close"><X size={18} /></button></div>
        <FilterGroup title="Size" filterKey="size" values={facets?.sizes ?? []} selected={selected.size} onToggle={toggleFilter} />
        <FilterGroup title="Fabric" filterKey="fabric" values={facets?.fabrics ?? []} selected={selected.fabric} onToggle={toggleFilter} />
        <FilterGroup title="Colour" filterKey="color" values={facets?.colors ?? []} selected={selected.color} onToggle={toggleFilter} />
        <FilterGroup title="Category" filterKey="category" values={facets?.categories ?? []} selected={selected.category} onToggle={toggleFilter} />
        <FilterGroup title="Collection" filterKey="collection" values={facets?.collections ?? []} selected={selected.collection} onToggle={toggleFilter} />
        <FilterGroup title="Work / Embroidery" filterKey="craft" values={facets?.crafts ?? []} selected={selected.craft} onToggle={toggleFilter} />
        <FilterGroup title="Availability" filterKey="availability" values={facets?.availabilities ?? []} selected={selected.availability} onToggle={toggleFilter} />
        {facets && facets.price_max > facets.price_min && <details className="filter-block"><summary className="filter-label">Price<ChevronDown size={15} /></summary><div className="price-filter"><label>Min ₹<input type="number" min={facets.price_min} max={facets.price_max} value={minPrice} placeholder={String(facets.price_min)} onChange={(event) => updateParams((next) => { if (event.target.value) next.set("min_price", event.target.value); else next.delete("min_price"); })} data-testid="filter-min-price" /></label><label>Max ₹<input type="number" min={facets.price_min} max={facets.price_max} value={maxPrice} placeholder={String(facets.price_max)} onChange={(event) => updateParams((next) => { if (event.target.value) next.set("max_price", event.target.value); else next.delete("max_price"); })} data-testid="filter-max-price" /></label></div></details>}
        {activeFilters > 0 && <button className="button button-outline button-full" onClick={clearFilters} data-testid="filter-panel-clear">Clear all filters</button>}
      </aside>
      <div className="catalog-region">{isPending ? <div className="catalog-loading" data-testid="catalog-loading">Curating your edit…</div> : isError ? <div className="catalog-empty" data-testid="catalog-error"><h2>The edit is taking a moment</h2><p>Our catalogue is reconnecting. Please try again shortly.</p></div> : products.length === 0 ? <div className="catalog-zero" data-testid="catalog-empty"><div><h2>No exact match yet.</h2><p>Remove a filter or explore these available SAFYRA pieces.</p><button className="button button-dark" onClick={clearFilters} data-testid="zero-results-clear">Clear filters</button></div><div className="product-grid">{allProducts.slice(0, 4).map((product, index) => <ProductCard key={product.id} product={product} index={index + 20} />)}</div></div> : <div className="product-grid">{products.map((product, index) => <ProductCard key={product.id} product={product} index={index} />)}</div>}</div>
    </div>
  </main></div>;
}