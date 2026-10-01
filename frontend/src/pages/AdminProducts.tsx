import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Edit3, PackagePlus, Plus, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import ImageManager from "@/components/ImageManager";
import SafeProductImage from "@/components/SafeProductImage";
import { apiDelete, apiGet, apiPatch, apiPost, ApiError } from "@/lib/api";
import type { CatalogGroup, PublishingStatus } from "@/lib/cms";
import type { Product } from "@/lib/shop";

interface ProductForm {
  title: string; slug: string; status: PublishingStatus; category: string; collection: string; fabric: string; craft: string;
  price: string; mrp: string; stock: string; sizes: string; colors: string; description: string; fit: string;
  measurements: string; transparency: string; lining: string; care: string; dispatch_days: string; availability: string;
  customisation: string; origin: string; occasion: string; style_keywords: string; size_guide_image: string;
}

const emptyForm: ProductForm = {
  title: "", slug: "", status: "draft", category: "", collection: "", fabric: "", craft: "", price: "", mrp: "", stock: "0", sizes: "", colors: "", description: "", fit: "", measurements: "", transparency: "", lining: "", care: "", dispatch_days: "", availability: "Made to order", customisation: "", origin: "", occasion: "", style_keywords: "", size_guide_image: "",
};
const splitList = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
const slugify = (value: string) => value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const statusLabels: Record<PublishingStatus, string> = { draft: "Draft", active: "Active", archived: "Archived" };

export default function AdminProducts() {
  const queryClient = useQueryClient();
  const { data: products = [], isError } = useQuery({ queryKey: ["products", "admin"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { data: groups = [] } = useQuery({ queryKey: ["catalog-groups", "admin"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups?include_all=true"), retry: false });
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [images, setImages] = useState<string[]>([]);
  const [stockBySize, setStockBySize] = useState<Record<string, number>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [completeLookIds, setCompleteLookIds] = useState<string[]>([]);
  const [merchandising, setMerchandising] = useState({ featured: false, new_arrival: false, best_seller: false });
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | PublishingStatus>("all");
  const sizes = splitList(form.sizes);
  const visibleProducts = useMemo(() => products.filter((product) => (statusFilter === "all" || product.status === statusFilter) && `${product.title} ${product.category} ${product.collection}`.toLowerCase().includes(query.toLowerCase())), [products, query, statusFilter]);
  const categories = groups.filter((group) => group.group_type === "category");
  const collections = groups.filter((group) => group.group_type === "collection");

  const reset = () => { setForm(emptyForm); setImages([]); setStockBySize({}); setCompleteLookIds([]); setMerchandising({ featured: false, new_arrival: false, best_seller: false }); setEditingId(null); setEditorOpen(false); };
  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        ...form,
        price: Number(form.price), mrp: form.mrp ? Number(form.mrp) : null, stock: Number(form.stock),
        sizes, colors: splitList(form.colors), image_url: images[0] ?? "", image_urls: images,
        stock_by_size: Object.fromEntries(sizes.map((size) => [size, Math.max(0, stockBySize[size] ?? 0)])),
        occasion: splitList(form.occasion), style_keywords: splitList(form.style_keywords), complete_look_ids: completeLookIds, tags: [], ...merchandising,
      };
      return editingId ? apiPatch<Product>(`/products/${editingId}`, body) : apiPost<Product>("/products", body);
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success(editingId ? "Product updated" : "Product created"); reset(); },
    onError: (reason) => toast.error(reason instanceof ApiError && reason.status === 409 ? "That product slug is already in use" : "Product could not be saved"),
  });
  const deleteMutation = useMutation({ mutationFn: (id: string) => apiDelete<void>(`/products/${id}`), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success("Product deleted"); }, onError: () => toast.error("Product could not be deleted") });
  const archiveMutation = useMutation({ mutationFn: (id: string) => apiPatch<Product>(`/products/${id}`, { status: "archived" }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success("Product archived and hidden from the storefront"); } });
  const edit = (product: Product) => {
    setForm({ title: product.title, slug: product.slug, status: product.status, category: product.category, collection: product.collection, fabric: product.fabric, craft: product.craft, price: String(product.price), mrp: product.mrp ? String(product.mrp) : "", stock: String(product.stock), sizes: product.sizes.join(", "), colors: product.colors.join(", "), description: product.description, fit: product.fit, measurements: product.measurements, transparency: product.transparency, lining: product.lining, care: product.care, dispatch_days: product.dispatch_days, availability: product.availability, customisation: product.customisation, origin: product.origin, occasion: product.occasion.join(", "), style_keywords: product.style_keywords.join(", "), size_guide_image: product.size_guide_image });
    setImages(product.image_urls.length ? product.image_urls : product.image_url ? [product.image_url] : []); setStockBySize(product.stock_by_size); setCompleteLookIds(product.complete_look_ids); setMerchandising({ featured: product.featured, new_arrival: product.new_arrival, best_seller: product.best_seller }); setEditingId(product.id); setEditorOpen(true); window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const submit = (event: FormEvent) => { event.preventDefault(); if (!images.length) { toast.error("Add at least one product image"); return; } saveMutation.mutate(); };

  return <AdminShell eyebrow="Catalog" title="Products" description="Create complete product stories, control inventory, and decide what customers can see." actions={<button className="button button-dark" onClick={() => { reset(); setEditorOpen(true); }} data-testid="admin-new-product-button"><Plus size={16} /> Add product</button>}>
    {editorOpen && <form className="admin-editor" onSubmit={submit} data-testid="admin-product-editor">
      <div className="admin-editor-heading"><div><span className="eyebrow">{editingId ? "Editing product" : "New product"}</span><h2 data-testid="admin-product-editor-title">{editingId ? form.title : "Create a product"}</h2></div><button type="button" onClick={reset} aria-label="Close product editor" data-testid="admin-product-editor-close"><X size={19} /></button></div>
      <div className="admin-editor-columns">
        <div className="admin-editor-stack">
          <section className="admin-editor-card" data-testid="admin-product-basics"><h3>Product information</h3><label>Title<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value, slug: form.slug || slugify(event.target.value) })} required data-testid="admin-product-title" /></label><label>URL slug<input value={form.slug} onChange={(event) => setForm({ ...form, slug: slugify(event.target.value) })} required data-testid="admin-product-slug" /></label><label>Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} data-testid="admin-product-description" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-media"><ImageManager images={images} onChange={setImages} label="Product gallery" testId="admin-product-images" /></section>
          <section className="admin-editor-card admin-fields-grid" data-testid="admin-product-details"><h3>Craft & product details</h3><label>Fabric<input value={form.fabric} onChange={(event) => setForm({ ...form, fabric: event.target.value })} data-testid="admin-product-fabric" /></label><label>Embroidery / work<input value={form.craft} onChange={(event) => setForm({ ...form, craft: event.target.value })} data-testid="admin-product-craft" /></label><label>Fit & silhouette<input value={form.fit} onChange={(event) => setForm({ ...form, fit: event.target.value })} data-testid="admin-product-fit" /></label><label>Measurements<input value={form.measurements} onChange={(event) => setForm({ ...form, measurements: event.target.value })} data-testid="admin-product-measurements" /></label><label>Transparency<input value={form.transparency} onChange={(event) => setForm({ ...form, transparency: event.target.value })} data-testid="admin-product-transparency" /></label><label>Lining<input value={form.lining} onChange={(event) => setForm({ ...form, lining: event.target.value })} data-testid="admin-product-lining" /></label><label>Care<input value={form.care} onChange={(event) => setForm({ ...form, care: event.target.value })} data-testid="admin-product-care" /></label><label>Origin<input value={form.origin} onChange={(event) => setForm({ ...form, origin: event.target.value })} data-testid="admin-product-origin" /></label><label className="admin-field-wide">Customisation<input value={form.customisation} onChange={(event) => setForm({ ...form, customisation: event.target.value })} data-testid="admin-product-customisation" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-inventory"><h3>Options & inventory</h3><label>Sizes <small>Comma separated, for example: S, M, L</small><input value={form.sizes} onChange={(event) => setForm({ ...form, sizes: event.target.value })} data-testid="admin-product-sizes" /></label>{sizes.length > 0 && <div className="admin-variant-stock" data-testid="admin-product-size-stock"><div><span>Size</span><span>Available quantity</span></div>{sizes.map((size) => <label key={size}><strong>{size}</strong><input type="number" min="0" value={stockBySize[size] ?? 0} onChange={(event) => setStockBySize({ ...stockBySize, [size]: Number(event.target.value) })} data-testid={`admin-product-stock-${slugify(size)}`} /></label>)}</div>}<label>Colours <small>Comma separated</small><input value={form.colors} onChange={(event) => setForm({ ...form, colors: event.target.value })} data-testid="admin-product-colors" /></label><label>Total stock <small>Used when a size-specific quantity is not set.</small><input type="number" min="0" value={form.stock} onChange={(event) => setForm({ ...form, stock: event.target.value })} data-testid="admin-product-stock" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-relations"><h3>Complete the Look</h3><p>Select only combinations approved by SAFYRA.</p><div className="admin-checkbox-list">{products.filter((product) => product.id !== editingId && product.status !== "archived").map((product) => <label key={product.id}><input type="checkbox" checked={completeLookIds.includes(product.id)} onChange={() => setCompleteLookIds((current) => current.includes(product.id) ? current.filter((id) => id !== product.id) : [...current, product.id])} data-testid={`admin-complete-look-${product.slug}`} />{product.title}</label>)}</div></section>
        </div>
        <aside className="admin-editor-stack">
          <section className="admin-editor-card" data-testid="admin-product-publishing"><h3>Publishing</h3><label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as PublishingStatus })} data-testid="admin-product-status"><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option></select></label><p className="admin-help-text">Only Active products appear on the customer storefront.</p></section>
          <section className="admin-editor-card admin-fields-grid" data-testid="admin-product-pricing"><h3>Pricing</h3><label>Price (₹)<input type="number" min="0" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required data-testid="admin-product-price" /></label><label>Compare-at price (₹)<input type="number" min="0" value={form.mrp} onChange={(event) => setForm({ ...form, mrp: event.target.value })} data-testid="admin-product-mrp" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-organisation"><h3>Organisation</h3><label>Category<input list="admin-category-options" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} required data-testid="admin-product-category" /><datalist id="admin-category-options">{categories.map((group) => <option value={group.name} key={group.id} />)}</datalist></label><label>Collection<input list="admin-collection-options" value={form.collection} onChange={(event) => setForm({ ...form, collection: event.target.value })} required data-testid="admin-product-collection" /><datalist id="admin-collection-options">{collections.map((group) => <option value={group.name} key={group.id} />)}</datalist></label><label>Occasions<input value={form.occasion} onChange={(event) => setForm({ ...form, occasion: event.target.value })} data-testid="admin-product-occasion" /></label><label>Search keywords<input value={form.style_keywords} onChange={(event) => setForm({ ...form, style_keywords: event.target.value })} data-testid="admin-product-keywords" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-availability"><h3>Availability</h3><label>Availability label<select value={form.availability} onChange={(event) => setForm({ ...form, availability: event.target.value })} data-testid="admin-product-availability-select"><option>Made to order</option><option>In stock</option><option>Currently unavailable</option></select></label><label>Making / dispatch time<input value={form.dispatch_days} onChange={(event) => setForm({ ...form, dispatch_days: event.target.value })} placeholder="12–15 business days" data-testid="admin-product-dispatch" /></label><label>Size guide image URL<input type="url" value={form.size_guide_image} onChange={(event) => setForm({ ...form, size_guide_image: event.target.value })} data-testid="admin-product-size-guide" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-merchandising"><h3>Merchandising</h3><label className="admin-check"><input type="checkbox" checked={merchandising.featured} onChange={(event) => setMerchandising({ ...merchandising, featured: event.target.checked })} data-testid="admin-product-featured" /> Featured product</label><label className="admin-check"><input type="checkbox" checked={merchandising.new_arrival} onChange={(event) => setMerchandising({ ...merchandising, new_arrival: event.target.checked })} data-testid="admin-product-new-arrival" /> New arrival</label><label className="admin-check"><input type="checkbox" checked={merchandising.best_seller} onChange={(event) => setMerchandising({ ...merchandising, best_seller: event.target.checked })} data-testid="admin-product-best-seller" /> Best seller</label></section>
          <button className="button button-dark button-full" disabled={saveMutation.isPending} data-testid="admin-product-save"><PackagePlus size={16} /> {saveMutation.isPending ? "Saving…" : editingId ? "Save product" : "Create product"}</button>
        </aside>
      </div>
    </form>}
    <section className="admin-resource-list" data-testid="admin-product-list-section">
      <div className="admin-list-toolbar"><div><span className="eyebrow">All products</span><h2 data-testid="admin-product-count">{visibleProducts.length} products</h2></div><div><label className="admin-search-field"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search products" data-testid="admin-product-search" /></label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | PublishingStatus)} data-testid="admin-product-status-filter"><option value="all">All statuses</option><option value="active">Active</option><option value="draft">Draft</option><option value="archived">Archived</option></select></div></div>
      {isError && <div className="form-error" data-testid="admin-products-error">Products could not be loaded.</div>}
      <div className="admin-table-list" data-testid="admin-product-list">{visibleProducts.map((product) => <article className="admin-table-row admin-product-table-row" key={product.id} data-testid={`admin-product-row-${product.id}`}><SafeProductImage src={product.image_url} alt={product.title} productName={product.title} /><div><strong>{product.title}</strong><span>{product.category} · {product.collection}</span><small>{product.availability}{product.dispatch_days ? ` · ${product.dispatch_days}` : ""}</small></div><span className={`admin-status-pill status-${product.status}`} data-testid={`admin-product-status-${product.id}`}>{statusLabels[product.status]}</span><strong>{product.price.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })}</strong><div className="admin-row-actions"><button onClick={() => edit(product)} aria-label={`Edit ${product.title}`} data-testid={`admin-product-edit-${product.id}`}><Edit3 size={16} /></button>{product.status !== "archived" && <button onClick={() => archiveMutation.mutate(product.id)} aria-label={`Archive ${product.title}`} data-testid={`admin-product-archive-${product.id}`}><Archive size={16} /></button>}<button className="danger-icon" onClick={() => window.confirm(`Permanently delete ${product.title}?`) && deleteMutation.mutate(product.id)} aria-label={`Delete ${product.title}`} data-testid={`admin-product-delete-${product.id}`}><Trash2 size={16} /></button></div></article>)}</div>
    </section>
  </AdminShell>;
}