import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Gift } from "lucide-react";
import { apiGet } from "@/lib/api";
import SafeProductImage from "@/components/SafeProductImage";
import { useAuth } from "@/components/AuthProvider";
import type { GiftEligibility } from "@/lib/giftOffer";

/** Shows where the shopper stands on the first-order gift for the current bag value. */
export default function GiftCartNotice({ subtotal }: { subtotal: number }) {
  const { user } = useAuth();
  const { data } = useQuery({
    queryKey: ["gift-eligibility", subtotal, user?.id ?? "guest"],
    queryFn: () => apiGet<GiftEligibility>(`/gift-offer/eligibility?subtotal=${subtotal}`),
    staleTime: 60 * 1000,
  });

  if (!data?.product) return null;

  return <div className="gift-cart-line" data-testid="gift-cart-notice">
    <SafeProductImage src={data.product.image_url} alt={data.product.title} productName={data.product.title} />
    <div>
      <strong data-testid="gift-cart-title">{data.eligible ? `${data.product.title} is on us` : data.product.title}</strong>
      <span data-testid="gift-cart-reason">{data.reason}</span>
      {!user && <> <Link to="/login" className="underlined-link" data-testid="gift-cart-login-link">Sign in</Link></>}
    </div>
    <Gift size={16} />
  </div>;
}
