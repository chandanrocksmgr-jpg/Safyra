import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Gift, X } from "lucide-react";
import { apiGet } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import SafeProductImage from "@/components/SafeProductImage";
import { formatPrice } from "@/lib/shop";
import type { GiftOfferPublic } from "@/lib/giftOffer";

const SEEN_KEY = "safyra-gift-offer-seen";

/** First-visit welcome: the running first-order gift offer, with its terms. Shown once per device. */
export default function GiftOfferPopup() {
  const location = useLocation();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const onAdminScreen = location.pathname.startsWith("/admin");

  const { data } = useQuery({
    queryKey: ["gift-offer"],
    queryFn: () => apiGet<GiftOfferPublic>("/gift-offer"),
    enabled: !onAdminScreen,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (onAdminScreen || !data?.enabled) return;
    if (user?.role === "admin") return;
    // Remembered per gift, so a new gift announces itself again.
    if (window.localStorage.getItem(SEEN_KEY) === (data.product?.id ?? "surprise")) return;
    const timer = setTimeout(() => setOpen(true), 1200);
    return () => clearTimeout(timer);
  }, [data, onAdminScreen, user]);

  const dismiss = () => {
    if (data?.enabled) window.localStorage.setItem(SEEN_KEY, data.product?.id ?? "surprise");
    setOpen(false);
  };

  if (!open || !data?.enabled) return null;

  return <div className="gift-popup-backdrop" role="dialog" aria-modal="true" aria-label={data.headline} data-testid="gift-offer-popup">
    <div className="gift-popup">
      <button type="button" className="gift-popup-close" onClick={dismiss} aria-label="Close" data-testid="gift-offer-close"><X size={18} /></button>
      {data.product ? <div className="gift-popup-art"><SafeProductImage src={data.product.image_url} alt={data.product.title} productName={data.product.title} /></div>
        : <div className="gift-popup-art is-placeholder" aria-hidden="true"><Gift size={64} strokeWidth={1} /></div>}
      <div className="gift-popup-copy">
        <span className="eyebrow"><Gift size={14} /> With our compliments</span>
        <h2 data-testid="gift-offer-headline">{data.headline}</h2>
        <p>{data.subtext}</p>
        {data.product && <p className="gift-popup-product" data-testid="gift-offer-product">{data.product.title}{data.product.value > 0 && <span> · worth {formatPrice(data.product.value)}</span>}</p>}
        <div className="gift-popup-actions">
          <Link to="/shop" className="button button-dark" onClick={dismiss} data-testid="gift-offer-shop-link">Start shopping</Link>
          {!user && <Link to="/signup" className="button button-outline" onClick={dismiss} data-testid="gift-offer-signup-link">Create an account</Link>}
        </div>
        <button type="button" className="link-button" onClick={() => setShowTerms((shown) => !shown)} data-testid="gift-offer-terms-toggle">{showTerms ? "Hide terms & conditions" : "Terms & conditions"}</button>
        {showTerms && <p className="gift-popup-terms" data-testid="gift-offer-terms">{data.terms}</p>}
      </div>
    </div>
  </div>;
}
