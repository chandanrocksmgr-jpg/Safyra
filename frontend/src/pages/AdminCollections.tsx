import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Edit3, Layers3, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import ImageManager from "@/components/ImageManager";
import SafeProductImage from "@/components/SafeProductImage";
import { apiDelete, apiGet, apiPatch, apiPost, ApiError } from "@/lib/api";
import type { CatalogGroup, CatalogGroupType, PublishingStatus } from "@/lib/cms";

interface GroupForm { name: string; slug: string; group_type: CatalogGroupType; description: string; status: PublishingStatus; sort_order: string; show_on_home: boolean; }
const emptyForm: GroupForm = { name: "", slug: "", group_type: "collection", description: "", status: "draft", sort_order: "0", show_on_home: true };
const slugify = (value: string) => value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export default function AdminCollections() {
  const queryClient = useQueryClient();
  const { data: groups = [], isError } = useQuery({ queryKey: ["catalog-groups", "admin"], queryFn: () => apiGet<CatalogGroup[]>("/catalog-groups?include_all=true"), retry: false });
  const [form, setForm] = useState<GroupForm>(emptyForm);
  const [images, setImages] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const reset = () => { setForm(emptyForm); setImages([]); setEditingId(null); setEditorOpen(false); };
  const saveMutation = useMutation({
    mutationFn: () => {
      const body = { ...form, image_url: images[0] ?? "", sort_order: Number(form.sort_order) };
      return editingId ? apiPatch<CatalogGroup>(`/catalog-groups/${editingId}`, body) : apiPost<CatalogGroup>("/catalog-groups", body);
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["catalog-groups"] }); toast.success(editingId ? "Group updated" : "Group created"); reset(); },
    onError: (reason) => toast.error(reason instanceof ApiError && reason.status === 409 ? "That slug is already used for this type" : "Collection could not be saved"),
  });
  const deleteMutation = useMutation({ mutationFn: (id: string) => apiDelete<void>(`/catalog-groups/${id}`), onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["catalog-groups"] }); toast.success("Group removed"); } });
  const edit = (group: CatalogGroup) => { setForm({ name: group.name, slug: group.slug, group_type: group.group_type, description: group.description, status: group.status, sort_order: String(group.sort_order), show_on_home: group.show_on_home }); setImages(group.image_url ? [group.image_url] : []); setEditingId(group.id); setEditorOpen(true); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const submit = (event: FormEvent) => { event.preventDefault(); saveMutation.mutate(); };
  const collections = groups.filter((group) => group.group_type === "collection");
  const categories = groups.filter((group) => group.group_type === "category");

  return <AdminShell eyebrow="Store organisation" title="Collections & categories" description="Create the shopping destinations that appear in navigation and on the homepage." actions={<button className="button button-dark" onClick={() => { reset(); setEditorOpen(true); }} data-testid="admin-new-group-button"><Plus size={16} /> Add group</button>}>
    {editorOpen && <form className="admin-editor admin-compact-editor" onSubmit={submit} data-testid="admin-group-editor"><div className="admin-editor-heading"><div><span className="eyebrow">{editingId ? "Editing group" : "New group"}</span><h2 data-testid="admin-group-editor-title">{editingId ? form.name : "Create a shopping group"}</h2></div><button type="button" onClick={reset} aria-label="Close group editor" data-testid="admin-group-editor-close"><X size={19} /></button></div><div className="admin-editor-columns"><div className="admin-editor-stack"><section className="admin-editor-card admin-fields-grid"><h3>Details</h3><label>Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value, slug: form.slug || slugify(event.target.value) })} required data-testid="admin-group-name" /></label><label>URL slug<input value={form.slug} onChange={(event) => setForm({ ...form, slug: slugify(event.target.value) })} required data-testid="admin-group-slug" /></label><label className="admin-field-wide">Description<textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} data-testid="admin-group-description" /></label></section><section className="admin-editor-card"><ImageManager images={images} onChange={setImages} label="Collection cover" testId="admin-group-image" limit={1} /></section></div><aside className="admin-editor-stack"><section className="admin-editor-card"><h3>Organisation</h3><label>Type<select value={form.group_type} onChange={(event) => setForm({ ...form, group_type: event.target.value as CatalogGroupType })} data-testid="admin-group-type"><option value="collection">Collection</option><option value="category">Category</option></select></label><label>Status<select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as PublishingStatus })} data-testid="admin-group-status"><option value="draft">Draft</option><option value="active">Active</option><option value="archived">Archived</option></select></label><label>Display order<input type="number" min="0" value={form.sort_order} onChange={(event) => setForm({ ...form, sort_order: event.target.value })} data-testid="admin-group-sort-order" /></label><label className="admin-check"><input type="checkbox" checked={form.show_on_home} onChange={(event) => setForm({ ...form, show_on_home: event.target.checked })} data-testid="admin-group-show-home" /> Show on homepage</label></section><button className="button button-dark button-full" disabled={saveMutation.isPending} data-testid="admin-group-save"><Layers3 size={16} /> {saveMutation.isPending ? "Saving…" : "Save group"}</button></aside></div></form>}
    {isError && <div className="form-error" data-testid="admin-groups-error">Collections and categories could not be loaded.</div>}
    {[{ title: "Collections", items: collections, type: "collections" }, { title: "Categories", items: categories, type: "categories" }].map((section) => <section className="admin-resource-list" key={section.type} data-testid={`admin-${section.type}-list`}><div className="admin-list-toolbar"><div><span className="eyebrow">Customer discovery</span><h2>{section.title} · {section.items.length}</h2></div></div><div className="admin-group-grid">{section.items.map((group) => <article className="admin-group-card" key={group.id} data-testid={`admin-group-${group.id}`}><div className="admin-group-image"><SafeProductImage src={group.image_url} alt={group.name} productName={group.name} /></div><div><span className={`admin-status-pill status-${group.status}`}>{group.status}</span><h3>{group.name}</h3><p>{group.description || "No customer-facing description yet."}</p><small>Order {group.sort_order} · {group.show_on_home ? "Homepage visible" : "Hidden from homepage"}</small></div><div className="admin-row-actions"><button onClick={() => edit(group)} aria-label={`Edit ${group.name}`} data-testid={`admin-group-edit-${group.id}`}><Edit3 size={16} /></button><button className="danger-icon" onClick={() => window.confirm(`Delete ${group.name}? Products will keep their current assignment.`) && deleteMutation.mutate(group.id)} aria-label={`Delete ${group.name}`} data-testid={`admin-group-delete-${group.id}`}><Trash2 size={16} /></button></div></article>)}</div></section>)}
  </AdminShell>;
}