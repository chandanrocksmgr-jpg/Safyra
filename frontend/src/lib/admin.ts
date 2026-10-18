export type PromotionType = "automatic" | "code";
export type DiscountType = "percentage" | "fixed";
export type DiscountStatus = "draft" | "scheduled" | "active" | "paused" | "expired";

export interface Discount {
  id: string;
  name: string;
  promotion_type: PromotionType;
  code: string | null;
  discount_type: DiscountType;
  value: number;
  minimum_subtotal: number;
  usage_limit: number | null;
  usage_count: number;
  product_ids: string[];
  collections: string[];
  starts_at: string;
  ends_at: string;
  status: DiscountStatus;
  effective_status: DiscountStatus;
  affected_products: number;
  created_at: string;
  updated_at: string;
}

export interface DiscountPayload {
  name: string;
  promotion_type: PromotionType;
  code: string | null;
  discount_type: DiscountType;
  value: number;
  minimum_subtotal: number;
  usage_limit: number | null;
  product_ids: string[];
  collections: string[];
  starts_at: string;
  ends_at: string;
  status: DiscountStatus;
}

export interface SalesMetrics {
  revenue: number;
  paid_orders: number;
  average_order_value: number;
  units_sold: number;
  checkout_sessions: number;
  conversion_rate: number;
  abandoned_checkouts: number;
}

export interface SalesAnalytics {
  days: number;
  current: SalesMetrics;
  previous: SalesMetrics;
  revenue_change: number;
  order_change: number;
  trend: { date: string; revenue: number; orders: number }[];
  top_products: { title: string; units: number; revenue: number }[];
  discounts: { name: string; uses: number; savings: number }[];
}

export interface StoreSettings {
  id: string;
  legal_name: string;
  gstin: string;
  registered_address: string;
  seller_state: string;
  state_code: string;
  gst_rate: number | null;
  hsn_code: string;
  support_email: string | null;
  support_phone: string;
  authorised_signatory: string;
  invoice_prefix: string;
  invoice_next_number: number;
  credit_note_prefix: string;
  credit_note_next_number: number;
  tax_inclusive: boolean;
  invoice_ready: boolean;
  missing_fields: string[];
  updated_at: string;
}

export interface GenerateInvoicesResponse { generated: number; blocked: number }