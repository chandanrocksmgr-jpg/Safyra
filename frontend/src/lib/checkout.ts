export interface OrderRequestItemInput {
  product_id: string;
  size: string;
  color: string;
  quantity: number;
}

export interface OrderRequestCreate {
  name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state_region: string;
  postal_code: string;
  country: string;
  country_code: string;
  shipping: "india" | "international";
  note: string;
  items: OrderRequestItemInput[];
}

export interface OrderRequestResponse {
  request_number: string;
  received_at: string;
}

export type PaymentStatus = "Unpaid" | "Payment pending" | "Paid";
export type FulfilmentStatus = "Request received" | "Confirmed" | "Processing" | "Ready to ship" | "Shipped" | "Delivered";
export type RefundStatus = "Not initiated" | "Processing" | "Refunded" | "Failed";

export interface OrderRequestStoredItem {
  product_id: string;
  title: string;
  image_url: string;
  price: number;
  size: string;
  color: string;
  quantity: number;
  line_total: number;
}

export interface OrderHistoryEvent {
  id: string;
  event: string;
  message: string;
  created_at: string;
  admin_id: string | null;
}

export interface AdminOrderRequest {
  id: string;
  request_number: string;
  received_at: string;
  customer_id: string | null;
  name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state_region: string;
  postal_code: string;
  country: string;
  country_code: string;
  shipping: "india" | "international";
  note: string;
  items: OrderRequestStoredItem[];
  subtotal: number;
  payment_status: PaymentStatus;
  payment_verified_at: string | null;
  fulfilment_status: FulfilmentStatus;
  courier_name: string;
  shipping_details: string;
  tracking_number: string;
  tracking_link: string;
  internal_notes: string;
  cancelled: boolean;
  cancellation_reason: string;
  cancelled_at: string | null;
  refund_status: RefundStatus;
  refund_reason: string;
  refund_amount: number;
  refund_reference: string;
  refund_confirmed_at: string | null;
  converted_order_id: string | null;
  history: OrderHistoryEvent[];
}

export interface AdminOrderRequestUpdate {
  payment_status?: PaymentStatus;
  payment_verified?: boolean;
  fulfilment_status?: FulfilmentStatus;
  courier_name?: string;
  shipping_details?: string;
  tracking_number?: string;
  tracking_link?: string;
  internal_notes?: string;
  refund_status?: RefundStatus;
  refund_reason?: string;
  refund_amount?: number;
  refund_reference?: string;
  refund_confirmed?: boolean;
}

export interface OrderConversionResponse {
  order_id: string;
  order_number: string;
  converted_at: string;
}