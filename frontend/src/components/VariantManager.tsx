import { useMemo, useState } from "react";
import { IndianRupee, Layers, Plus, Trash2 } from "lucide-react";
import type { ProductSetType, ProductVariant } from "@/lib/shop";

const COMBINATION_SUGGESTIONS = ["Kurta only", "Kurta + Dupatta", "Kurta + Bottom", "Kurta + Bottom + Dupatta", "Kurta + Dupatta + Bottom + Inner"];
type StockFilter = "all" | "in-stock" | "sold-out";

const keyOf = (setTypeId: string, color: string, size: string) => `${setTypeId}|${color}|${size}`;
const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "none";

/** Every combination × colour × size the product offers, filled from saved rows (new rows start at 0 stock). */
export function buildVariantRows(sizes: string[], colors: string[], setTypes: ProductSetType[], variants: ProductVariant[]): ProductVariant[] {
  const saved = new Map(variants.map((variant) => [keyOf(variant.set_type_id, variant.color, variant.size), variant]));
  const setIds = setTypes.length ? setTypes.map((item) => item.id) : [""];
  const colorList = colors.length ? colors : [""];
  const sizeList = sizes.length ? sizes : [""];
  return setIds.flatMap((setTypeId) => colorList.flatMap((color) => sizeList.map((size) =>
    saved.get(keyOf(setTypeId, color, size)) ?? { id: "", set_type_id: setTypeId, color, size, price: null, mrp: null, stock: 0, available: true })));
}

interface VariantManagerProps {
  sizes: string[];
  colors: string[];
  setTypes: ProductSetType[];
  onSetTypesChange: (next: ProductSetType[]) => void;
  variants: ProductVariant[];
  onVariantsChange: (next: ProductVariant[]) => void;
  basePrice: number;
}

export default function VariantManager({ sizes, colors, setTypes, onSetTypesChange, variants, onVariantsChange, basePrice }: VariantManagerProps) {
  const [setFilter, setSetFilter] = useState("all");
  const [colorFilter, setColorFilter] = useState("all");
  const [stockFilter, setStockFilter] = useState<StockFilter>("all");
  const [bulkStock, setBulkStock] = useState("");
  const [bulkPrice, setBulkPrice] = useState("");
  const [pricePreview, setPricePreview] = useState<{ price: number; rows: ProductVariant[] } | null>(null);
  const rows = useMemo(() => buildVariantRows(sizes, colors, setTypes, variants), [sizes, colors, setTypes, variants]);
  const isSoldOut = (row: ProductVariant) => !row.available || row.stock < 1;
  const visible = rows.filter((row) => (setFilter === "all" || row.set_type_id === setFilter) && (colorFilter === "all" || row.color === colorFilter)
    && (stockFilter === "all" || (stockFilter === "sold-out" ? isSoldOut(row) : !isSoldOut(row))));
  const totalStock = rows.reduce((sum, row) => sum + (row.available ? row.stock : 0), 0);
  const soldOutCount = rows.filter(isSoldOut).length;
  const setName = (id: string) => setTypes.find((item) => item.id === id)?.name || "Unnamed set";
  const defaultPrice = (row: ProductVariant) => setTypes.find((item) => item.id === row.set_type_id)?.price ?? basePrice;

  const updateRows = (targets: ProductVariant[], patch: Partial<ProductVariant>) => {
    const targetKeys = new Set(targets.map((row) => keyOf(row.set_type_id, row.color, row.size)));
    onVariantsChange(rows.map((row) => targetKeys.has(keyOf(row.set_type_id, row.color, row.size)) ? { ...row, ...patch } : row));
  };
  const updateSetType = (id: string, patch: Partial<ProductSetType>) => onSetTypesChange(setTypes.map((item) => item.id === id ? { ...item, ...patch } : item));
  const addSetType = () => {
    const unused = COMBINATION_SUGGESTIONS.find((name) => !setTypes.some((item) => item.name.toLowerCase() === name.toLowerCase())) ?? "";
    onSetTypesChange([...setTypes, { id: crypto.randomUUID(), name: setTypes.length ? unused : "Kurta only", price: basePrice, mrp: null }]);
  };
  const removeSetType = (id: string) => {
    const stocked = rows.filter((row) => row.set_type_id === id && row.stock > 0).reduce((sum, row) => sum + row.stock, 0);
    if (stocked && !window.confirm(`Remove “${setName(id)}”? Its ${stocked} pieces of variant stock will be removed too.`)) return;
    onSetTypesChange(setTypes.filter((item) => item.id !== id));
    onVariantsChange(rows.filter((row) => row.set_type_id !== id));
    if (setFilter === id) setSetFilter("all");
  };

  return <div className="variant-manager" data-testid="admin-variant-manager">
    <div className="variant-block" data-testid="admin-set-types">
      <div className="variant-block-heading"><div><strong><Layers size={15} /> Combinations</strong><small>Add the sets this product is sold as — Kurta only, Kurta + Dupatta, and so on — each with its own price. “Price all its variants” applies that price to every colour and size of the combination at once, and any single variant can still be overridden below.</small></div><button type="button" className="button button-outline" onClick={addSetType} disabled={setTypes.length >= 20} data-testid="admin-set-type-add"><Plus size={14} /> Add combination</button></div>
      {setTypes.length > 0 && <div className="set-type-rows">
        <datalist id="admin-set-type-suggestions">{COMBINATION_SUGGESTIONS.map((name) => <option key={name} value={name} />)}</datalist>
        {setTypes.map((item, index) => <div className="set-type-row" key={item.id} data-testid={`admin-set-type-row-${index}`}>
          <label>Name<input list="admin-set-type-suggestions" value={item.name} onChange={(event) => updateSetType(item.id, { name: event.target.value })} placeholder="Kurta + Dupatta" required maxLength={100} data-testid={`admin-set-type-name-${index}`} /></label>
          <label>Price (₹)<input type="number" min="0" value={item.price} onChange={(event) => updateSetType(item.id, { price: Math.max(0, Number(event.target.value)) })} required data-testid={`admin-set-type-price-${index}`} /></label>
          <label>Compare-at (₹)<input type="number" min="0" value={item.mrp ?? ""} onChange={(event) => updateSetType(item.id, { mrp: event.target.value ? Math.max(0, Number(event.target.value)) : null })} data-testid={`admin-set-type-mrp-${index}`} /></label>
          <button type="button" className="button button-outline" onClick={() => setPricePreview({ price: Math.max(0, Number(item.price) || 0), rows: rows.filter((row) => row.set_type_id === item.id) })} disabled={!rows.some((row) => row.set_type_id === item.id)} title={`Price every colour and size of ${item.name || "this combination"} at ₹${Number(item.price || 0).toLocaleString("en-IN")}`} data-testid={`admin-set-type-apply-price-${index}`}><IndianRupee size={14} /> Price all its variants</button>
          <button type="button" className="icon-button" onClick={() => removeSetType(item.id)} aria-label={`Remove ${item.name || "combination"}`} data-testid={`admin-set-type-remove-${index}`}><Trash2 size={15} /></button>
        </div>)}
      </div>}
    </div>

    <div className="variant-block" data-testid="admin-variants">
      <div className="variant-block-heading"><div><strong>Variants</strong><small>One row per {setTypes.length ? "combination, " : ""}colour and size. Stock decreases automatically for the exact variant purchased; a variant at 0 or switched off cannot be ordered and shows “Notify me”.</small></div></div>
      <div className="variant-summary" data-testid="admin-variant-summary"><span><b>{rows.length}</b> variants</span><span><b>{totalStock}</b> pieces in stock</span><span className={soldOutCount ? "is-warning" : ""}><b>{soldOutCount}</b> sold out or unavailable</span></div>
      <div className="variant-toolbar">
        {setTypes.length > 0 && <select value={setFilter} onChange={(event) => setSetFilter(event.target.value)} aria-label="Filter by combination" data-testid="admin-variant-filter-set"><option value="all">All combinations</option>{setTypes.map((item) => <option key={item.id} value={item.id}>{item.name || "Unnamed set"}</option>)}</select>}
        {colors.length > 1 && <select value={colorFilter} onChange={(event) => setColorFilter(event.target.value)} aria-label="Filter by colour" data-testid="admin-variant-filter-color"><option value="all">All colours</option>{colors.map((color) => <option key={color} value={color}>{color}</option>)}</select>}
        <select value={stockFilter} onChange={(event) => setStockFilter(event.target.value as StockFilter)} aria-label="Filter by stock" data-testid="admin-variant-filter-stock"><option value="all">Any stock</option><option value="in-stock">In stock</option><option value="sold-out">Sold out / unavailable</option></select>
        <div className="variant-bulk"><input type="number" min="0" value={bulkStock} onChange={(event) => setBulkStock(event.target.value)} placeholder="Stock" aria-label="Stock for all shown variants" data-testid="admin-variant-bulk-stock" /><button type="button" className="button button-outline" disabled={bulkStock === "" || !visible.length} onClick={() => { updateRows(visible, { stock: Math.max(0, Number(bulkStock)) }); setBulkStock(""); }} data-testid="admin-variant-bulk-apply">Set for {visible.length} shown</button></div>
        <div className="variant-bulk"><input type="number" min="0" value={bulkPrice} onChange={(event) => setBulkPrice(event.target.value)} placeholder="Price ₹" aria-label="Price for all shown variants" data-testid="admin-variant-bulk-price" /><button type="button" className="button button-outline" disabled={bulkPrice === "" || !visible.length} onClick={() => setPricePreview({ price: Math.max(0, Number(bulkPrice)), rows: visible })} data-testid="admin-variant-bulk-price-preview"><IndianRupee size={14} /> Price {visible.length} shown</button></div>
        <button type="button" className="button button-outline" disabled={!visible.some((row) => row.price !== null)} onClick={() => updateRows(visible, { price: null })} data-testid="admin-variant-clear-prices">Clear overrides</button>
      </div>
      {pricePreview && <div className="variant-price-preview" data-testid="admin-variant-price-preview">
        <strong>Review this price change</strong>
        <p>{pricePreview.rows.length} variant{pricePreview.rows.length === 1 ? "" : "s"} will be priced at ₹{pricePreview.price.toLocaleString("en-IN")}. Individual variants can still be overridden afterwards.</p>
        <ul>{pricePreview.rows.slice(0, 8).map((row) => { const id = `${slug(setTypes.length ? setName(row.set_type_id) : "")}-${slug(row.color)}-${slug(row.size)}`; return <li key={id} data-testid={`admin-variant-price-preview-row-${id}`}>{[setTypes.length ? setName(row.set_type_id) : "", row.color, row.size].filter(Boolean).join(" · ") || "Single variant"}<span>₹{(row.price ?? defaultPrice(row)).toLocaleString("en-IN")} → <b>₹{pricePreview.price.toLocaleString("en-IN")}</b></span></li>; })}</ul>
        {pricePreview.rows.length > 8 && <p className="admin-help-text">…and {pricePreview.rows.length - 8} more.</p>}
        <div className="variant-price-preview-actions">
          <button type="button" className="button button-dark" onClick={() => { updateRows(pricePreview.rows, { price: pricePreview.price }); setPricePreview(null); setBulkPrice(""); }} data-testid="admin-variant-price-confirm">Apply to {pricePreview.rows.length} variants</button>
          <button type="button" className="button button-outline" onClick={() => setPricePreview(null)} data-testid="admin-variant-price-cancel">Cancel</button>
        </div>
      </div>}
      {sizes.length === 0 && colors.length === 0 && setTypes.length === 0 && <p className="admin-help-text">Add sizes or colours above to create variants. Until then this product has a single stock row.</p>}
      <div className="variant-table-wrap"><table className="variant-table" data-testid="admin-variant-table">
        <thead><tr>{setTypes.length > 0 && <th>Combination</th>}{colors.length > 0 && <th>Colour</th>}{sizes.length > 0 && <th>Size</th>}<th>Price (₹)</th><th>Stock</th><th>Available</th><th>Status</th></tr></thead>
        <tbody>{visible.map((row) => { const id = `${slug(setTypes.length ? setName(row.set_type_id) : "")}-${slug(row.color)}-${slug(row.size)}`; return <tr key={keyOf(row.set_type_id, row.color, row.size)} className={isSoldOut(row) ? "is-sold-out" : ""} data-testid={`admin-variant-row-${id}`}>
          {setTypes.length > 0 && <td>{setName(row.set_type_id)}</td>}{colors.length > 0 && <td>{row.color}</td>}{sizes.length > 0 && <td><strong>{row.size}</strong></td>}
          <td><input type="number" min="0" value={row.price ?? ""} placeholder={String(defaultPrice(row))} onChange={(event) => updateRows([row], { price: event.target.value === "" ? null : Math.max(0, Number(event.target.value)) })} aria-label={`Price for ${id}`} data-testid={`admin-variant-price-${id}`} /></td>
          <td><input type="number" min="0" value={row.stock} onChange={(event) => updateRows([row], { stock: Math.max(0, Math.floor(Number(event.target.value) || 0)) })} aria-label={`Stock for ${id}`} data-testid={`admin-variant-stock-${id}`} /></td>
          <td><label className="variant-switch"><input type="checkbox" checked={row.available} onChange={(event) => updateRows([row], { available: event.target.checked })} data-testid={`admin-variant-available-${id}`} /><span>{row.available ? "On" : "Off"}</span></label></td>
          <td><span className={`variant-status ${!row.available ? "is-off" : row.stock < 1 ? "is-out" : "is-ok"}`} data-testid={`admin-variant-status-${id}`}>{!row.available ? "Unavailable" : row.stock < 1 ? "Sold out" : `${row.stock} in stock`}</span></td>
        </tr>; })}</tbody>
      </table>{!visible.length && <p className="admin-help-text">No variants match these filters.</p>}</div>
      <p className="admin-help-text">Leave a price blank to use the {setTypes.length ? "combination" : "product"} price. Filter by combination above, then use <b>Price shown</b> to price every colour and size of that combination together — any single variant can still be overridden in its own row.</p>
    </div>
  </div>;
}
