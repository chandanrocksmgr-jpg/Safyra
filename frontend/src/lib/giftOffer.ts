/** Mirrors backend models/gift_offer.py. */
export interface GiftProductSummary {
  id: string;
  title: string;
  image_url: string;
  value: number;
  stock: number;
}

export interface GiftOfferPublic {
  enabled: boolean;
  threshold: number;
  low_stock_threshold: number;
  headline: string;
  subtext: string;
  terms: string;
  product: GiftProductSummary | null;
}

export interface GiftOfferSettings {
  enabled: boolean;
  threshold: number;
  low_stock_threshold: number;
  product_id: string;
  headline: string;
  subtext: string;
  terms: string;
}

export interface GiftEligibility {
  eligible: boolean;
  reason: string;
  threshold: number;
  shortfall: number;
  product: GiftProductSummary | null;
}
