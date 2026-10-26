import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Gift, Save } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import SafeProductImage from "@/components/SafeProductImage";
import { apiGet, apiPut, ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/shop";
import type { GiftOfferSettings, GiftProductSummary } from "@/lib/giftOffer";

/** Super Admin control room for the first-order gift: which gift is live, the cart threshold, and the copy shoppers see. */
export default function AdminGiftOffer() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<GiftOfferSettings | null>(null);

  const { data } = useQuery({ queryKey: ["gift-offer-settings"], queryFn: () => apiGet<GiftOfferSettings>("/gift-offer/settings") });
  const { data: products = [] } = useQuery({ queryKey: ["gift-products"], queryFn: () => apiGet<GiftProductSummary[]>("/gift-offer/products") });

  useEffect(() => { if (data && !draft) setDraft(data); }, [data, draft]);

  const save = useMutation({
    mutationFn: (payload: GiftOfferSettings) => apiPut<GiftOfferSettings>("/gift-offer/settings", payload),
    onSuccess: (saved) => {
      setDraft(saved);
      queryClient.invalidateQueries({ queryKey: ["gift-offer-settings"] });
      queryClient.invalidateQueries({ queryKey: ["gift-offer"] });
      toast.success(saved.enabled ? "Gift offer is running" : "Gift offer is paused");
    },
    onError: (reason) => toast.error(reason instanceof ApiError ? String((reason.body as { detail?: string } | null)?.detail || "Could not save the offer") : "Could not save the offer"),
  });

  const activeGift = products.find((product) => product.id === draft?.product_id);
  const lowStock = Boolean(activeGift && draft && activeGift.stock <= draft.low_stock_threshold);

  if (!draft) return <AdminShell eyebrow="Offers" title="First-order gift" description="Loading the gift offer…"><p>Loading…</p></AdminShell>;

  const update = (changes: Partial<GiftOfferSettings>) => setDraft({ ...draft, ...changes });

  return <AdminShell
    eyebrow="Offers"
    title="First-order gift"
    description="One gift product can be live at a time. It is added automatically to a registered customer's first qualifying order."
    actions={<button type="button" className="button button-dark" onClick={() => save.mutate(draft)} disabled={save.isPending} data-testid="admin-gift-save"><Save size={15} /> {save.isPending ? "Saving…" : "Save offer"}</button>}
  >
    {draft?.enabled && !draft.product_id && <div className="gift-stock-warning" data-testid="admin-gift-no-product">
      <AlertTriangle size={16} />
      <div>
        <strong>No gift is chosen yet</strong>
        <span>The announcement is showing to shoppers, but no gift will be added to orders until you pick one below.</span>
      </div>
    </div>}
    {lowStock && activeGift && <div className="gift-stock-warning" data-testid="admin-gift-low-stock">
      <AlertTriangle size={16} />
      <div>
        <strong>{activeGift.stock === 0 ? `${activeGift.title} is out of stock` : `Only ${activeGift.stock} left of ${activeGift.title}`}</strong>
        <span>{activeGift.stock === 0 ? "No order will receive a gift until you restock it or choose another gift." : "Restock it in Products, or switch the active gift, before the offer runs dry."}</span>
      </div>
    </div>}

    <section className="admin-editor-card" data-testid="admin-gift-status">
      <h3><Gift size={16} /> Offer status</h3>
      <label className="admin-toggle-row">
        <input type="checkbox" checked={draft.enabled} onChange={(event) => update({ enabled: event.target.checked })} data-testid="admin-gift-enabled" />
        <span>{draft.enabled ? "Running — qualifying first orders receive the gift" : "Paused — no gift is added to any order"}</span>
      </label>
      <div className="admin-form-grid">
        <label>Cart value needed (₹)<input type="number" min="0" value={draft.threshold} onChange={(event) => update({ threshold: Math.max(0, Number(event.target.value)) })} data-testid="admin-gift-threshold" /><small>The gift is added when the bag reaches this value, before shipping.</small></label>
        <label>Warn me when stock reaches<input type="number" min="0" value={draft.low_stock_threshold} onChange={(event) => update({ low_stock_threshold: Math.max(0, Number(event.target.value)) })} data-testid="admin-gift-low-stock-threshold" /><small>You get an email alert when the live gift drops to this many pieces.</small></label>
      </div>
    </section>

    <section className="admin-editor-card" data-testid="admin-gift-products">
      <h3>Active gift product</h3>
      {products.length === 0
        ? <p className="admin-help-text" data-testid="admin-gift-empty">No gift products yet. Add a product in Products, tick <b>Gift product</b> on it, and it will appear here.</p>
        : <div className="gift-product-grid">
          {products.map((product) => <button type="button" key={product.id} className={draft.product_id === product.id ? "gift-product-card is-active" : "gift-product-card"} onClick={() => update({ product_id: draft.product_id === product.id ? "" : product.id })} data-testid={`admin-gift-product-${product.id}`}>
            <SafeProductImage src={product.image_url} alt={product.title} productName={product.title} />
            <strong>{product.title}</strong>
            <span>{product.value > 0 ? `Worth ${formatPrice(product.value)}` : "No stated value"} · <b data-testid={`admin-gift-stock-${product.id}`}>{product.stock} in stock</b></span>
            {draft.product_id === product.id && <em data-testid={`admin-gift-product-active-${product.id}`}>Active gift</em>}
          </button>)}
        </div>}
    </section>

    <section className="admin-editor-card" data-testid="admin-gift-copy">
      <h3>What shoppers see</h3>
      <div className="admin-form-grid">
        <label className="is-wide">Headline<input value={draft.headline} onChange={(event) => update({ headline: event.target.value })} data-testid="admin-gift-headline" /></label>
        <label className="is-wide">Supporting line<textarea value={draft.subtext} onChange={(event) => update({ subtext: event.target.value })} data-testid="admin-gift-subtext" /></label>
        <label className="is-wide">Terms & conditions<textarea value={draft.terms} onChange={(event) => update({ terms: event.target.value })} rows={5} data-testid="admin-gift-terms" /></label>
      </div>
    </section>
  </AdminShell>;
}
