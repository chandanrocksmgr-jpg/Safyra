import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clock3, Search } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { apiGet } from "@/lib/api";
import type { Product } from "@/lib/shop";
import { formatPrice } from "@/lib/shop";
import SafeProductImage from "@/components/SafeProductImage";

const loadRecent = () => {
  try { return JSON.parse(localStorage.getItem("safyra-recent-searches") ?? "[]") as string[]; }
  catch { return []; }
};

export default function SearchExperience({ initialQuery, onClose }: { initialQuery: string; onClose: () => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState(initialQuery);
  const [recent, setRecent] = useState<string[]>(loadRecent);
  const trimmed = query.trim();
  const { data: suggestions = [], isFetching } = useQuery({ queryKey: ["search-suggestions", trimmed], queryFn: () => apiGet<Product[]>(`/products?q=${encodeURIComponent(trimmed)}`), enabled: trimmed.length >= 2, retry: false });
  const remember = (term: string) => {
    const next = [term, ...recent.filter((item) => item.toLowerCase() !== term.toLowerCase())].slice(0, 5);
    setRecent(next);
    localStorage.setItem("safyra-recent-searches", JSON.stringify(next));
  };
  const searchFor = (term: string) => { if (term.trim()) remember(term.trim()); navigate(`/shop?search=${encodeURIComponent(term.trim())}`); onClose(); };
  const submit = (event: FormEvent) => { event.preventDefault(); searchFor(trimmed); };
  const categories = [...new Set(suggestions.map((product) => product.category).filter(Boolean))].slice(0, 3);
  const collections = [...new Set(suggestions.map((product) => product.collection).filter(Boolean))].slice(0, 3);
  return <div className="search-experience" data-testid="search-experience"><form className="search-strip" onSubmit={submit} data-testid="global-search-form"><Search size={18} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by product, fabric, colour or craft" data-testid="global-search-input" /><button className="text-button" type="submit" data-testid="global-search-submit">Search</button></form><div className="search-results-panel">{trimmed.length < 2 ? <div className="recent-searches"><span className="eyebrow">Recent searches</span>{recent.length ? recent.map((term, index) => <button key={term} onClick={() => searchFor(term)} data-testid={`recent-search-${index + 1}`}><Clock3 size={14} /> {term}</button>) : <p>No recent searches yet. Try “Kota Doria” or “Anarkali”.</p>}</div> : isFetching ? <p className="search-status" data-testid="search-suggestions-loading">Finding considered pieces…</p> : suggestions.length ? <div className="suggestion-layout"><div className="product-suggestions"><span className="eyebrow">Products</span>{suggestions.slice(0, 4).map((product, index) => <Link to={`/product/${product.slug}`} onClick={() => { remember(trimmed); onClose(); }} key={product.id} data-testid={`search-product-suggestion-${index + 1}`}><SafeProductImage src={product.image_url} alt={product.title} productName={product.title} /><span><strong>{product.title}</strong><small>{product.fabric || product.category}</small><b>{formatPrice(product.price)}</b></span></Link>)}</div><div className="search-taxonomy"><span className="eyebrow">Explore</span>{categories.map((item, index) => <button key={item} onClick={() => searchFor(item)} data-testid={`search-category-suggestion-${index + 1}`}>Category · {item}</button>)}{collections.map((item, index) => <button key={item} onClick={() => searchFor(item)} data-testid={`search-collection-suggestion-${index + 1}`}>Collection · {item}</button>)}</div></div> : <div className="search-zero" data-testid="search-zero-suggestions"><h3>No exact match yet.</h3><p>Try a broader fabric, silhouette or colour.</p><div><button onClick={() => searchFor("Kota Doria")} data-testid="search-zero-kota">Kota Doria</button><button onClick={() => searchFor("Anarkali")} data-testid="search-zero-anarkali">Anarkali</button><button onClick={() => searchFor("Chikankari")} data-testid="search-zero-chikankari">Chikankari</button></div></div>}</div></div>;
}