import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Edit3, PackagePlus, Plus, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import ColorManager from "@/components/ColorManager";
import ImageManager from "@/components/ImageManager";
import VideoManager from "@/components/VideoManager";
import SafeProductImage from "@/components/SafeProductImage";
import VariantManager, { buildVariantRows } from "@/components/VariantManager";
import { apiDelete, apiGet, apiPatch, apiPost, ApiError } from "@/lib/api";
import type { CatalogGroup, PublishingStatus } from "@/lib/cms";
import { availabilityLabel, swatchFor, type Product, type ProductColorOption, type ProductSetType, type ProductVariant } from "@/lib/shop";

type StitchType = "stitched" | "semi_stitched" | "unstitched" | "other";

interface ProductForm {
  title: string; slug: string; status: PublishingStatus; category: string; collection: string; fabric: string; craft: string; hsn_code: string;
  price: string; mrp: string; stock: string; stitch_type: StitchType; sizes: string; description: string; fit: string;
  measurements: string; transparency: string; lining: string; care: string; dispatch_days: string; availability: string;
  customisation: string; origin: string; occasion: string; style_keywords: string;
}

const emptyForm: ProductForm = {
  title: "", slug: "", status: "draft", category: "", collection: "", fabric: "", craft: "", hsn_code: "62114922", price: "", mrp: "", stock: "0", stitch_type: "stitched", sizes: "", description: "", fit: "", measurements: "", transparency: "", lining: "", care: "Dry clean only", dispatch_days: "", availability: "Made to order", customisation: "", origin: "Lucknow", occasion: "", style_keywords: "",
};
const splitList = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);
const slugify = (value: string) => value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const statusLabels: Record<PublishingStatus, string> = { draft: "Draft", active: "Active", archived: "Archived" };
const stitchTypeLabels: Record<StitchType, string> = { stitched: "Stitched — asks for a size, shows the SAFYRA size chart", semi_stitched: "Semi-stitched — no size needed", unstitched: "Unstitched — no size needed", other: "Other (accessories, etc.) — no size needed" };

// Lets an admin close the editor (or lose the tab) mid-edit without losing progress — resumed next time
// the same product (or a fresh "new product") is opened. Cleared only once the product actually saves.
interface ProductDraft {
  form: ProductForm; images: string[]; isGift: boolean; videos: string[]; videoPosters: string[];
  colorOptions: ProductColorOption[]; setTypes: ProductSetType[]; variants: ProductVariant[]; completeLookIds: string[];
  merchandising: { featured: boolean; new_arrival: boolean; best_seller: boolean }; savedAt: number;
}
const draftKey = (id: string | null) => `safyra-admin-product-draft:${id ?? "new"}`;
const loadDraft = (id: string | null): ProductDraft | null => {
  try {
    const raw = window.localStorage.getItem(draftKey(id));
    return raw ? (JSON.parse(raw) as ProductDraft) : null;
  } catch {
    return null;
  }
};
const clearDraft = (id: string | null) => window.localStorage.removeItem(draftKey(id));

export default function AdminProducts() {
  const queryClient = useQueryClient();
  const { data: products = [], isError } = useQuery({ queryKey: ["products", "admin"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const { data: groups = [] } = useQuery({ queryKey: ["catalog-groups", "admin"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups?include_all=true"), retry: false });
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [images, setImages] = useState<string[]>([]);
  const [isGift, setIsGift] = useState(false);
  const [videos, setVideos] = useState<string[]>([]);
  const [videoPosters, setVideoPosters] = useState<string[]>([]);
  const [colorOptions, setColorOptions] = useState<ProductColorOption[]>([]);
  const [setTypes, setSetTypes] = useState<ProductSetType[]>([]);
  const [variants, setVariants] = useState<ProductVariant[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [completeLookIds, setCompleteLookIds] = useState<string[]>([]);
  const [merchandising, setMerchandising] = useState({ featured: false, new_arrival: false, best_seller: false });
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | PublishingStatus>("all");
  const [resumedDraftAt, setResumedDraftAt] = useState<number | null>(null);

  const applyDraft = (draft: ProductDraft) => {
    setForm(draft.form); setImages(draft.images); setIsGift(draft.isGift); setVideos(draft.videos); setVideoPosters(draft.videoPosters);
    setColorOptions(draft.colorOptions); setSetTypes(draft.setTypes); setVariants(draft.variants); setCompleteLookIds(draft.completeLookIds); setMerchandising(draft.merchandising);
  };
  useEffect(() => {
    if (!editorOpen) return;
    const draft: ProductDraft = { form, images, isGift, videos, videoPosters, colorOptions, setTypes, variants, completeLookIds, merchandising, savedAt: Date.now() };
    window.localStorage.setItem(draftKey(editingId), JSON.stringify(draft));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editorOpen, editingId, form, images, isGift, videos, videoPosters, colorOptions, setTypes, variants, completeLookIds, merchandising]);

  const sizes = form.stitch_type === "stitched" ? splitList(form.sizes) : [];
  const colors = colorOptions.map((item) => item.name.trim()).filter(Boolean);
  const variantRows = buildVariantRows(sizes, colors, setTypes, variants);
  const visibleProducts = useMemo(() => products.filter((product) => (statusFilter === "all" || product.status === statusFilter) && `${product.title} ${product.category} ${product.collection}`.toLowerCase().includes(query.toLowerCase())), [products, query, statusFilter]);
  const categories = groups.filter((group) => group.group_type === "category");
  const collections = groups.filter((group) => group.group_type === "collection");
  const fabrics = groups.filter((group) => group.group_type === "fabric");
  const blankCareOriginProducts = useMemo(() => products.filter((product) => !product.care.trim() || !product.origin.trim()), [products]);
  const fillCareOriginMutation = useMutation({
    mutationFn: () => apiPost<Product[]>("/products/bulk", { product_ids: blankCareOriginProducts.map((product) => product.id), care_value: "Dry clean only", origin_value: "Lucknow" }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success(`Filled Care and/or Origin on ${blankCareOriginProducts.length} product${blankCareOriginProducts.length === 1 ? "" : "s"}`); },
    onError: () => toast.error("Could not fill Care/Origin for these products"),
  });

  const reset = () => { setForm(emptyForm); setImages([]); setVideos([]); setVideoPosters([]); setIsGift(false); setColorOptions([]); setSetTypes([]); setVariants([]); setCompleteLookIds([]); setMerchandising({ featured: false, new_arrival: false, best_seller: false }); setEditingId(null); setEditorOpen(false); setResumedDraftAt(null); };
  const saveMutation = useMutation({
    mutationFn: () => {
      const body = {
        ...form,
        price: Number(form.price), mrp: form.mrp ? Number(form.mrp) : null, stock: variantRows.reduce((sum, row) => sum + (row.available ? row.stock : 0), 0),
        sizes, colors, color_options: colorOptions.filter((item) => item.name.trim()).map((item) => ({ name: item.name.trim(), swatch: item.swatch || swatchFor(item.name), image_urls: item.image_urls.filter((url) => images.includes(url)) })), is_gift: isGift, video_urls: videos.map((url) => url.trim()).filter(Boolean).slice(0, 2), video_posters: videoPosters.slice(0, 2), image_url: images[0] ?? "", image_urls: images, size_guide_image: form.size_required ? form.size_guide_image : "",
        set_types: setTypes.map((item) => ({ ...item, name: item.name.trim() })), variants: variantRows,
        occasion: splitList(form.occasion), style_keywords: splitList(form.style_keywords), complete_look_ids: completeLookIds, tags: [], ...merchandising,
      };
      return editingId ? apiPatch<Product>(`/products/${editingId}`, body) : apiPost<Product>("/products", body);
    },
    onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({ queryKey: ["products"] }), queryClient.invalidateQueries({ queryKey: ["product"] }), queryClient.invalidateQueries({ queryKey: ["product-facets"] })]); toast.success(editingId ? "Product updated" : "Product created"); reset(); },
    onError: (reason) => toast.error(reason instanceof ApiError && reason.status === 409 ? "That product slug is already in use" : reason instanceof ApiError && reason.status === 422 && JSON.stringify(reason.body).includes("Image links") ? "One image link only works on your device — remove it and use Upload images instead" : "Product could not be saved"),
  });
  const deleteMutation = useMutation({ mutationFn: (id: string) => apiDelete<void>(`/products/${id}`), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success("Product deleted"); }, onError: () => toast.error("Product could not be deleted") });
  const archiveMutation = useMutation({ mutationFn: (id: string) => apiPatch<Product>(`/products/${id}`, { status: "archived" }), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["products"] }); toast.success("Product archived and hidden from the storefront"); } });
  const edit = (product: Product) => {
    setForm({ title: product.title, slug: product.slug, status: product.status, category: product.category, collection: product.collection, fabric: product.fabric, craft: product.craft, hsn_code: product.hsn_code || "62114922", price: String(product.price), mrp: product.mrp ? String(product.mrp) : "", stock: String(product.stock), size_required: product.size_required, sizes: product.sizes.join(", "), description: product.description, fit: product.fit, measurements: product.measurements, transparency: product.transparency, lining: product.lining, care: product.care, dispatch_days: product.dispatch_days, availability: product.availability, customisation: product.customisation, origin: product.origin, occasion: product.occasion.join(", "), style_keywords: product.style_keywords.join(", "), size_guide_image: product.size_guide_image });
    setImages(product.image_urls.length ? product.image_urls : product.image_url ? [product.image_url] : []); setIsGift(Boolean(product.is_gift)); setVideos(product.video_urls ?? []); setVideoPosters(product.video_posters ?? []); setColorOptions(product.color_options?.length ? product.color_options.map((item) => ({ ...item, image_urls: [...item.image_urls] })) : product.colors.map((name) => ({ name, swatch: swatchFor(name), image_urls: [] }))); setSetTypes(product.set_types ?? []); setVariants(product.variants ?? []); setCompleteLookIds(product.complete_look_ids); setMerchandising({ featured: product.featured, new_arrival: product.new_arrival, best_seller: product.best_seller }); setEditingId(product.id); setEditorOpen(true); window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const renameColor = (previous: string, next: string) => {
    if (!previous || previous === next) return;
    setVariants((current) => current.map((row) => row.color === previous ? { ...row, color: next } : row));
  };
  const removeColor = (name: string) => setVariants((current) => current.filter((row) => row.color !== name));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!images.length) { toast.error("Add at least one product image"); return; }
    const colorNames = colorOptions.map((item) => item.name.trim().toLowerCase());
    if (colorNames.some((name) => !name)) { toast.error("Give every colour a name, or remove the empty row"); return; }
    if (new Set(colorNames).size !== colorNames.length) { toast.error("Each colour needs a unique name"); return; }
    const names = setTypes.map((item) => item.name.trim().toLowerCase());
    if (names.some((name) => !name)) { toast.error("Give every combination a name"); return; }
    if (new Set(names).size !== names.length) { toast.error("Each combination needs a unique name"); return; }
    saveMutation.mutate();
  };

  return <AdminShell eyebrow="Catalog" title="Products" description="Create complete product stories, control inventory, and decide what customers can see." actions={<button className="button button-dark" onClick={() => { reset(); setEditorOpen(true); }} data-testid="admin-new-product-button"><Plus size={16} /> Add product</button>}>
    {editorOpen && <form className="admin-editor" onSubmit={submit} data-testid="admin-product-editor">
      <div className="admin-editor-heading"><div><span className="eyebrow">{editingId ? "Editing product" : "New product"}</span><h2 data-testid="admin-product-editor-title">{editingId ? form.title : "Create a product"}</h2></div><button type="button" onClick={reset} aria-label="Close product editor" data-testid="admin-product-editor-close"><X size={19} /></button></div>
      <div className="admin-editor-columns">
        <div className="admin-editor-stack">
          <section className="admin-editor-card" data-testid="admin-product-basics"><h3>Product information</h3><label>Title<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value, slug: form.slug || slugify(event.target.value) })} required data-testid="admin-product-title" /></label><label>URL slug<input value={form.slug} onChange={(event) => setForm({ ...form, slug: slugify(event.target.value) })} required data-testid="admin-product-slug" /></label><label>Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} data-testid="admin-product-description" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-media"><ImageManager images={images} onChange={setImages} label="Product gallery" testId="admin-product-images" limit={40} /><VideoManager videos={videos} posters={videoPosters} gallery={images} onChange={(nextVideos, nextPosters) => { setVideos(nextVideos); setVideoPosters(nextPosters); }} /></section>
          <section className="admin-editor-card admin-fields-grid" data-testid="admin-product-details"><h3>Craft & product details</h3><label>Fabric<input value={form.fabric} onChange={(event) => { const fabric = event.target.value; setForm({ ...form, fabric, hsn_code: form.category === "Straight Kurtis" && fabric.toLowerCase().includes("cotton") ? "62063090" : "62114922" }); }} data-testid="admin-product-fabric" /></label><label>Embroidery / work<input value={form.craft} onChange={(event) => setForm({ ...form, craft: event.target.value })} data-testid="admin-product-craft" /></label><label>Product HSN code<select value={form.hsn_code} onChange={(event) => setForm({ ...form, hsn_code: event.target.value })} required data-testid="admin-product-hsn"><option value="62114922">62114922 — other women’s Chikankari garments</option><option value="62063090">62063090 — cotton woven kurtis / tunics</option></select></label><label>Fit & silhouette<input value={form.fit} onChange={(event) => setForm({ ...form, fit: event.target.value })} data-testid="admin-product-fit" /></label><label>Measurements<input value={form.measurements} onChange={(event) => setForm({ ...form, measurements: event.target.value })} data-testid="admin-product-measurements" /></label><label>Transparency<input value={form.transparency} onChange={(event) => setForm({ ...form, transparency: event.target.value })} data-testid="admin-product-transparency" /></label><label>Lining<input value={form.lining} onChange={(event) => setForm({ ...form, lining: event.target.value })} data-testid="admin-product-lining" /></label><label>Care<input value={form.care} onChange={(event) => setForm({ ...form, care: event.target.value })} data-testid="admin-product-care" /></label><label>Origin<input value={form.origin} onChange={(event) => setForm({ ...form, origin: event.target.value })} data-testid="admin-product-origin" /></label><label className="admin-field-wide">Customisation<input value={form.customisation} onChange={(event) => setForm({ ...form, customisation: event.target.value })} data-testid="admin-product-customisation" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-inventory"><h3>Options, variants & inventory</h3><label>Size applicable<select value={form.size_required ? "yes" : "no"} onChange={(event) => { const required = event.target.value === "yes"; setForm({ ...form, size_required: required, sizes: required ? form.sizes : "", size_guide_image: required ? (form.size_guide_image || SAFYRA_SIZE_GUIDE_IMAGE) : form.size_guide_image }); }} data-testid="admin-product-size-required"><option value="yes">Yes — stitched (customer picks a size)</option><option value="no">No — unstitched (no size needed)</option></select></label>{form.size_required && <label>Sizes <small>Comma separated, for example: S, M, L</small><input value={form.sizes} onChange={(event) => setForm({ ...form, sizes: event.target.value })} data-testid="admin-product-sizes" /></label>}<ColorManager colors={colorOptions} onChange={setColorOptions} gallery={images} onRenameColor={renameColor} onRemoveColor={removeColor} /><VariantManager sizes={sizes} colors={colors} setTypes={setTypes} onSetTypesChange={setSetTypes} variants={variantRows} onVariantsChange={setVariants} basePrice={Number(form.price) || 0} /></section>
          <section className="admin-editor-card" data-testid="admin-product-relations"><h3>Complete the Look</h3><p>Select only combinations approved by SAFYRA.</p><div className="admin-checkbox-list">{products.filter((product) => product.id !== editingId && product.status !== "archived").map((product) => <label key={product.id}><input type="checkbox" checked={completeLookIds.includes(product.id)} onChange={() => setCompleteLookIds((current) => current.includes(product.id) ? current.filter((id) => id !== product.id) : [...current, product.id])} data-testid={`admin-complete-look-${product.slug}`} />{product.title}</label>)}</div></section>
        </div>
        <aside className="admin-editor-stack">
          <section className="admin-editor-card" data-testid="admin-product-publishing"><h3>Publishing</h3><label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as PublishingStatus })} data-testid="admin-product-status"><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option></select></label><p className="admin-help-text">Only Active products appear on the customer storefront.</p></section>
          <section className="admin-editor-card admin-fields-grid" data-testid="admin-product-pricing"><h3>Pricing</h3><label>Price (₹)<input type="number" min="0" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required data-testid="admin-product-price" /></label><label>Compare-at price (₹)<input type="number" min="0" value={form.mrp} onChange={(event) => setForm({ ...form, mrp: event.target.value })} data-testid="admin-product-mrp" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-organisation"><h3>Organisation</h3><label>Category<input list="admin-category-options" value={form.category} onChange={(event) => { const category = event.target.value; setForm({ ...form, category, hsn_code: category === "Straight Kurtis" && form.fabric.toLowerCase().includes("cotton") ? "62063090" : "62114922" }); }} required data-testid="admin-product-category" /><datalist id="admin-category-options">{categories.map((group) => <option value={group.name} key={group.id} />)}</datalist></label><label>Collection<input list="admin-collection-options" value={form.collection} onChange={(event) => setForm({ ...form, collection: event.target.value })} required data-testid="admin-product-collection" /><datalist id="admin-collection-options">{collections.map((group) => <option value={group.name} key={group.id} />)}</datalist></label><label>Occasions<input value={form.occasion} onChange={(event) => setForm({ ...form, occasion: event.target.value })} data-testid="admin-product-occasion" /></label><label>Search keywords<input value={form.style_keywords} onChange={(event) => setForm({ ...form, style_keywords: event.target.value })} data-testid="admin-product-keywords" /></label></section>
          <section className="admin-editor-card" data-testid="admin-product-availability"><h3>Availability</h3><label>Availability label<select value={form.availability} onChange={(event) => setForm({ ...form, availability: event.target.value })} data-testid="admin-product-availability-select"><option>Made to order</option><option>In stock</option><option value="Currently unavailable">You just missed it (sold out)</option></select></label><label>Making / dispatch time<input value={form.dispatch_days} onChange={(event) => setForm({ ...form, dispatch_days: event.target.value })} placeholder="12–15 business days" data-testid="admin-product-dispatch" /></label>{form.size_required && <label>Size guide image <small>Shown to customers below the product photos</small><div className="admin-image-inputs"><input type="text" inputMode="url" value={form.size_guide_image} onChange={(event) => setForm({ ...form, size_guide_image: event.target.value })} placeholder="Paste image URL" data-testid="admin-product-size-guide" /><label className="button button-outline admin-upload-button"><Upload size={14} /> {sizeGuideUploading ? "Uploading…" : "Upload"}<input type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" onChange={(event) => uploadSizeGuide(event.target.files)} disabled={sizeGuideUploading} data-testid="admin-product-size-guide-upload" /></label></div>{form.size_guide_image && <div className="admin-image-grid"><div className="admin-image-item"><SafeProductImage src={form.size_guide_image} alt="Size guide preview" productName="Size guide" /><button type="button" onClick={() => setForm({ ...form, size_guide_image: "" })} aria-label="Remove size guide image" data-testid="admin-product-size-guide-remove"><Trash2 size={14} /></button></div></div>}</label>}</section>
          <section className="admin-editor-card" data-testid="admin-product-merchandising"><h3>Merchandising</h3><label className="admin-check"><input type="checkbox" checked={merchandising.featured} onChange={(event) => setMerchandising({ ...merchandising, featured: event.target.checked })} data-testid="admin-product-featured" /> Featured product</label><label className="admin-check"><input type="checkbox" checked={merchandising.new_arrival} onChange={(event) => setMerchandising({ ...merchandising, new_arrival: event.target.checked })} data-testid="admin-product-new-arrival" /> New arrival</label><label className="admin-check"><input type="checkbox" checked={merchandising.best_seller} onChange={(event) => setMerchandising({ ...merchandising, best_seller: event.target.checked })} data-testid="admin-product-best-seller" /> Best seller</label><label className="admin-check"><input type="checkbox" checked={isGift} onChange={(event) => setIsGift(event.target.checked)} data-testid="admin-product-is-gift" /> Gift product <small>(hidden from the shop, used only for the first-order gift)</small></label></section>
          <button className="button button-dark button-full" disabled={saveMutation.isPending} data-testid="admin-product-save"><PackagePlus size={16} /> {saveMutation.isPending ? "Saving…" : editingId ? "Save product" : "Create product"}</button>
        </aside>
      </div>
    </form>}
    <section className="admin-resource-list" data-testid="admin-product-list-section">
      <div className="admin-list-toolbar"><div><span className="eyebrow">All products</span><h2 data-testid="admin-product-count">{visibleProducts.length} products</h2></div><div><label className="admin-search-field"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search products" data-testid="admin-product-search" /></label><select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | PublishingStatus)} data-testid="admin-product-status-filter"><option value="all">All statuses</option><option value="active">Active</option><option value="draft">Draft</option><option value="archived">Archived</option></select>{blankCareOriginProducts.length > 0 && <button type="button" className="button button-outline" disabled={fillCareOriginMutation.isPending} onClick={() => window.confirm(`Fill Care ("Dry clean only") and/or Origin ("Lucknow") on ${blankCareOriginProducts.length} product${blankCareOriginProducts.length === 1 ? "" : "s"} that are currently blank? Products that already have a value keep it.`) && fillCareOriginMutation.mutate()} data-testid="admin-fill-care-origin-button">{fillCareOriginMutation.isPending ? "Filling…" : `Fill blank Care & Origin (${blankCareOriginProducts.length})`}</button>}</div></div>
      {isError && <div className="form-error" data-testid="admin-products-error">Products could not be loaded.</div>}
      <div className="admin-table-list" data-testid="admin-product-list">{visibleProducts.map((product) => <article className="admin-table-row admin-product-table-row" key={product.id} data-testid={`admin-product-row-${product.id}`}><SafeProductImage src={product.image_url} alt={product.title} productName={product.title} /><div><strong>{product.title}</strong><span>{product.category} · {product.collection}</span><small>{availabilityLabel(product.availability)}{product.dispatch_days ? ` · ${product.dispatch_days}` : ""}</small></div><span className={`admin-status-pill status-${product.status}`} data-testid={`admin-product-status-${product.id}`}>{statusLabels[product.status]}</span><strong>{product.price.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 })}</strong><div className="admin-row-actions"><button onClick={() => edit(product)} aria-label={`Edit ${product.title}`} data-testid={`admin-product-edit-${product.id}`}><Edit3 size={16} /></button>{product.status !== "archived" && <button onClick={() => archiveMutation.mutate(product.id)} aria-label={`Archive ${product.title}`} data-testid={`admin-product-archive-${product.id}`}><Archive size={16} /></button>}<button className="danger-icon" onClick={() => window.confirm(`Permanently delete ${product.title}?`) && deleteMutation.mutate(product.id)} aria-label={`Delete ${product.title}`} data-testid={`admin-product-delete-${product.id}`}><Trash2 size={16} /></button></div></article>)}</div>
    </section>
  </AdminShell>;
}