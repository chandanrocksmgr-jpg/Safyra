import { Palette, Plus, RefreshCw, Trash2 } from "lucide-react";
import SafeProductImage from "@/components/SafeProductImage";
import { swatchFor, type ProductColorOption } from "@/lib/shop";

interface ColorManagerProps {
  colors: ProductColorOption[];
  onChange: (next: ProductColorOption[]) => void;
  gallery: string[];
  /** Called when a colour is renamed or removed so variant rows keep their stock. */
  onRenameColor: (previous: string, next: string) => void;
  onRemoveColor: (name: string) => void;
}

const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "colour";

export default function ColorManager({ colors, onChange, gallery, onRenameColor, onRemoveColor }: ColorManagerProps) {
  const update = (index: number, patch: Partial<ProductColorOption>) => onChange(colors.map((item, position) => position === index ? { ...item, ...patch } : item));
  const rename = (index: number, name: string) => {
    const previous = colors[index].name;
    update(index, { name, swatch: colors[index].swatch === swatchFor(previous) || !colors[index].swatch ? swatchFor(name) : colors[index].swatch });
    onRenameColor(previous, name);
  };
  const add = () => onChange([...colors, { name: "", swatch: swatchFor(""), image_urls: [] }]);
  const remove = (index: number) => {
    const item = colors[index];
    if (item.name && !window.confirm(`Remove “${item.name}”? Its variant rows and stock are removed too.`)) return;
    onChange(colors.filter((_, position) => position !== index));
    onRemoveColor(item.name);
  };
  const togglePhoto = (index: number, url: string) => {
    const current = colors[index].image_urls;
    update(index, { image_urls: current.includes(url) ? current.filter((item) => item !== url) : [...current, url] });
  };

  return <div className="color-manager" data-testid="admin-color-manager">
    <div className="variant-block-heading"><div><strong><Palette size={15} /> Colours</strong><small>Each colour gets its own swatch, photos, sizes and stock. Customers see only the photos you tick here; a colour with no photos falls back to the full gallery.</small></div><button type="button" className="button button-outline" onClick={add} disabled={colors.length >= 60} data-testid="admin-color-add"><Plus size={14} /> Add colour</button></div>
    {colors.length === 0 && <p className="admin-help-text" data-testid="admin-color-empty">No colours yet. Add one to create colour variants for this product.</p>}
    {colors.map((item, index) => <div className="color-option-card" key={`color-${index}`} data-testid={`admin-color-row-${index}`}>
      <div className="color-option-head">
        <label>Colour name<input value={item.name} onChange={(event) => rename(index, event.target.value)} placeholder="Blush petal" maxLength={80} data-testid={`admin-color-name-${index}`} /></label>
        <label>Swatch<input type="color" value={/^#[0-9a-fA-F]{6}$/.test(item.swatch) ? item.swatch : swatchFor(item.name)} onChange={(event) => update(index, { swatch: event.target.value.toUpperCase() })} aria-label={`Swatch colour for ${item.name || "new colour"}`} data-testid={`admin-color-swatch-${index}`} /></label>
        <button type="button" className="button button-outline" onClick={() => update(index, { swatch: swatchFor(item.name) })} title="Reset to the auto-generated swatch" data-testid={`admin-color-swatch-auto-${index}`}><RefreshCw size={14} /> Auto</button>
        <button type="button" className="icon-button" onClick={() => remove(index)} aria-label={`Remove ${item.name || "colour"}`} data-testid={`admin-color-remove-${index}`}><Trash2 size={15} /></button>
      </div>
      <div><small className="admin-help-text">Photos for {item.name || "this colour"} ({item.image_urls.length} of {gallery.length} selected)</small>
        {gallery.length === 0 ? <p className="admin-help-text" data-testid={`admin-color-no-gallery-${index}`}>Upload product photos above, then tick the ones that show this colour.</p> : <div className="color-option-photos">{gallery.map((url, photoIndex) => { const picked = item.image_urls.includes(url); return <button type="button" key={`${url}-${photoIndex}`} className={picked ? "color-photo-pick is-picked" : "color-photo-pick"} onClick={() => togglePhoto(index, url)} aria-pressed={picked} aria-label={`${picked ? "Unassign" : "Assign"} photo ${photoIndex + 1} to ${item.name || "this colour"}`} data-testid={`admin-color-${slug(item.name)}-photo-${photoIndex}`}><SafeProductImage src={url} alt="" productName={item.name || "Colour"} />{picked && <em>{item.image_urls.indexOf(url) + 1}</em>}</button>; })}</div>}
      </div>
    </div>)}
  </div>;
}
