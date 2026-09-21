import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, LockKeyhole, LogOut, PackagePlus, Trash2, X } from "lucide-react";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, ApiError } from "@/lib/api";
import type { Product } from "@/lib/shop";
import { useAuth } from "@/components/AuthProvider";
import { endSession } from "@/lib/session";
import SafeProductImage from "@/components/SafeProductImage";

interface ProductForm {
  title: string; slug: string; category: string; collection: string; fabric: string; craft: string;
  price: string; mrp: string; stock: string; size_stock: string; sizes: string; colors: string;
  image_url: string; image_urls: string; description: string; fit: string; measurements: string;
  transparency: string; lining: string; care: string; dispatch_days: string; availability: string;
  customisation: string; origin: string; occasion: string; style_keywords: string; size_guide_image: string;
}

const emptyForm: ProductForm = {
  title: "", slug: "", category: "", collection: "", fabric: "", craft: "", price: "", mrp: "",
  stock: "0", size_stock: "", sizes: "", colors: "", image_url: "", image_urls: "", description: "",
  fit: "", measurements: "", transparency: "", lining: "", care: "", dispatch_days: "", availability: "",
  customisation: "", origin: "", occasion: "", style_keywords: "", size_guide_image: "",
};

const formFields: Array<[keyof ProductForm, string, string]> = [
  ["title", "Product title", "text"], ["slug", "Slug", "text"], ["category", "Category", "text"],
  ["collection", "Collection", "text"], ["fabric", "Fabric", "text"], ["craft", "Craft / work", "text"],
  ["price", "Price (₹)", "number"], ["mrp", "Verified compare-at price (optional)", "number"],
  ["stock", "Total stock", "number"], ["size_stock", "Size stock (example S:2, M:0)", "text"],
  ["sizes", "Approved sizes (comma separated)", "text"], ["colors", "Approved colours (comma separated)", "text"],
  ["image_url", "Primary SAFYRA image URL", "url"], ["image_urls", "All approved image URLs (comma separated)", "text"],
  ["description", "Verified description", "text"], ["fit", "Fit & silhouette", "text"],
  ["measurements", "Measurements", "text"], ["transparency", "Transparency", "text"], ["lining", "Lining", "text"],
  ["care", "Care", "text"], ["dispatch_days", "Dispatch information", "text"], ["availability", "Availability label", "text"],
  ["customisation", "Customisation", "text"], ["origin", "Origin", "text"],
  ["occasion", "Occasions (comma separated)", "text"], ["style_keywords", "Search keywords (comma separated)", "text"],
  ["size_guide_image", "Approved size guide image URL", "url"],
];

const splitList = (value: string) => value.split(",").map((item) => item.trim()).filter(Boolean);

export default function Admin() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { data: products = [] } = useQuery({ queryKey: ["products", "admin"], queryFn: () => apiGet<Product[]>("/products"), retry: false });
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [completeLookIds, setCompleteLookIds] = useState<string[]>([]);
  const [merchandising, setMerchandising] = useState({ featured: false, new_arrival: false, best_seller: false });
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [passwordMessage, setPasswordMessage] = useState("");

  const resetForm = () => {
    setForm(emptyForm); setCompleteLookIds([]); setEditingId(null);
    setMerchandising({ featured: false, new_arrival: false, best_seller: false });
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const { size_stock: sizeStock, image_urls: imageUrls, ...base } = form;
      const stock_by_size = Object.fromEntries(sizeStock.split(",").map((entry) => entry.split(":").map((part) => part.trim())).filter((entry) => entry[0] && entry[1] !== undefined).map(([size, value]) => [size, Number(value)]));
      const approvedImages = splitList(imageUrls);
      const body = {
        ...base, price: Number(form.price), mrp: form.mrp ? Number(form.mrp) : null, stock: Number(form.stock),
        sizes: splitList(form.sizes), colors: splitList(form.colors), occasion: splitList(form.occasion),
        style_keywords: splitList(form.style_keywords), image_urls: approvedImages.length ? approvedImages : form.image_url ? [form.image_url] : [],
        stock_by_size, complete_look_ids: completeLookIds, tags: [], ...merchandising,
      };
      return editingId ? apiPatch<Product>(`/products/${editingId}`, body) : apiPost<Product>("/products", body);
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["products"] }); resetForm(); },
  });
  const deleteMutation = useMutation({ mutationFn: (id: string) => apiDelete<void>(`/products/${id}`), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["products"] }) });
  const passwordMutation = useMutation({ mutationFn: () => apiPut<void>("/auth/password", { current_password: passwords.current, new_password: passwords.next }), onSuccess: async () => { await endSession("/admin-login"); }, onError: (reason) => setPasswordMessage(reason instanceof ApiError && reason.status === 400 ? "Current password is incorrect." : "New password must meet every requirement.") });

  const submit = (event: FormEvent) => { event.preventDefault(); saveMutation.mutate(); };
  const editProduct = (product: Product) => {
    setEditingId(product.id);
    setCompleteLookIds(product.complete_look_ids);
    setMerchandising({ featured: product.featured, new_arrival: product.new_arrival, best_seller: product.best_seller });
    setForm({
      title: product.title, slug: product.slug, category: product.category, collection: product.collection, fabric: product.fabric,
      craft: product.craft, price: String(product.price), mrp: product.mrp ? String(product.mrp) : "", stock: String(product.stock),
      size_stock: Object.entries(product.stock_by_size).map(([size, value]) => `${size}:${value}`).join(", "), sizes: product.sizes.join(", "),
      colors: product.colors.join(", "), image_url: product.image_url, image_urls: product.image_urls.join(", "), description: product.description,
      fit: product.fit, measurements: product.measurements, transparency: product.transparency, lining: product.lining, care: product.care,
      dispatch_days: product.dispatch_days, availability: product.availability, customisation: product.customisation, origin: product.origin,
      occasion: product.occasion.join(", "), style_keywords: product.style_keywords.join(", "), size_guide_image: product.size_guide_image,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return <div className="admin-shell"><header className="admin-secure-header"><div><LockKeyhole size={18} /><span>SAFYRA SECURE OPERATIONS</span></div><div><span data-testid="admin-user-name">{user?.name}</span><button onClick={() => endSession("/admin-login")} data-testid="admin-logout-button"><LogOut size={15} /> Sign out</button></div></header><main className="admin-page"><div className="admin-heading"><div><span className="eyebrow">Restricted catalog workspace</span><h1>Catalog admin</h1><p>Only publish details and relationships approved by SAFYRA.</p></div><span className="admin-status"><span /> Authenticated session</span></div><section className="admin-security-card"><div><LockKeyhole size={20} /><span><strong>Administrator security</strong><small>Change your password here, or use verified recovery from the private sign-in page.</small></span></div><form onSubmit={(event) => { event.preventDefault(); setPasswordMessage(""); passwordMutation.mutate(); }} data-testid="admin-change-password-form"><input type="password" placeholder="Current password" value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} required data-testid="admin-current-password" /><input type="password" placeholder="New secure password" value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} required data-testid="admin-new-password" /><button className="button button-outline" disabled={passwordMutation.isPending} data-testid="admin-change-password-submit">Change password</button></form>{passwordMessage && <div className="form-error" data-testid="admin-password-message">{passwordMessage}</div>}</section><div className="admin-layout"><form className="admin-form" onSubmit={submit} data-testid="admin-product-form"><div className="form-heading"><div><span className="eyebrow">{editingId ? "Edit piece" : "Add a new piece"}</span><h2>{editingId ? "Update product" : "Product details"}</h2></div>{editingId && <button type="button" className="icon-button" onClick={resetForm} aria-label="Cancel edit" data-testid="admin-cancel-edit"><X size={18} /></button>}</div>{formFields.map(([key, label, type]) => <label className={key === "description" ? "form-field form-field-wide" : "form-field"} key={key}>{label}{key === "description" ? <textarea value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} data-testid={`admin-input-${key}`} /> : <input type={type} value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} required={["title", "slug", "category", "collection", "price", "image_url", "availability"].includes(key)} data-testid={`admin-input-${key}`} />}</label>)}<fieldset className="admin-relations form-field-wide"><legend>Approved “Complete the Look” products</legend><p>Leave empty until SAFYRA explicitly approves a pairing.</p>{products.filter((product) => product.id !== editingId).map((product) => <label key={product.id}><input type="checkbox" checked={completeLookIds.includes(product.id)} onChange={() => setCompleteLookIds((current) => current.includes(product.id) ? current.filter((id) => id !== product.id) : [...current, product.id])} data-testid={`admin-complete-look-${product.slug}`} />{product.title}</label>)}</fieldset><fieldset className="admin-relations form-field-wide"><legend>Approved merchandising labels</legend><p>Enable only when SAFYRA has verified the claim.</p><label><input type="checkbox" checked={merchandising.featured} onChange={(event) => setMerchandising({ ...merchandising, featured: event.target.checked })} data-testid="admin-featured-checkbox" />Featured</label><label><input type="checkbox" checked={merchandising.new_arrival} onChange={(event) => setMerchandising({ ...merchandising, new_arrival: event.target.checked })} data-testid="admin-new-arrival-checkbox" />New arrival</label><label><input type="checkbox" checked={merchandising.best_seller} onChange={(event) => setMerchandising({ ...merchandising, best_seller: event.target.checked })} data-testid="admin-best-seller-checkbox" />Best seller</label></fieldset><button className="button button-dark button-full" type="submit" disabled={saveMutation.isPending} data-testid="admin-save-product-button"><PackagePlus size={16} /> {saveMutation.isPending ? "Saving…" : editingId ? "Save product changes" : "Add product"}</button></form><section className="admin-list"><div className="form-heading"><div><span className="eyebrow">Live catalog</span><h2>{products.length} products</h2></div></div><div className="admin-product-list">{products.map((product) => <div className="admin-product-row" key={product.id} data-testid={`admin-product-row-${product.id}`}><SafeProductImage src={product.image_url} alt={product.title} productName={product.title} /><div><strong>{product.title}</strong><span>{product.category}{product.fabric ? ` · ${product.fabric}` : ""}</span><small>{product.availability}{product.dispatch_days ? ` · ${product.dispatch_days}` : ""}</small></div><div className="admin-row-actions"><button className="icon-button" onClick={() => editProduct(product)} aria-label={`Edit ${product.title}`} data-testid={`admin-product-row-edit-${product.id}`}><Edit3 size={16} /></button><button className="icon-button danger-icon" onClick={() => deleteMutation.mutate(product.id)} aria-label={`Delete ${product.title}`} data-testid={`admin-product-row-delete-${product.id}`}><Trash2 size={16} /></button></div></div>)}</div></section></div></main></div>;
}