export interface OrderRequestItemInput {
  product_id: string;
  set_type?: string | null;
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
  checkout_session_id?: string | null;
  discount_code?: string | null;
  items: OrderRequestItemInput[];
}

export interface OrderRequestResponse {
  request_number: string;
  received_at: string;
}

export type PaymentStatus = "Unpaid" | "Payment pending" | "Paid";
export type FulfilmentStatus = "Request received" | "Confirmed" | "In production" | "Quality check" | "Shipped" | "Delivered";
export type RefundStatus = "Not initiated" | "Processing" | "Refunded" | "Failed";
export type EmailDeliveryStatus = "Not scheduled" | "Scheduled" | "Sending" | "Sent" | "Failed";

export interface OrderRequestStoredItem {
  product_id: string;
  title: string;
  image_url: string;
  hsn_code: string;
  set_type: string | null;
  regular_price: number;
  price: number;
  compare_at_price: number | null;
  discount_name: string | null;
  discount_id: string | null;
  discount_amount: number;
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
  regular_subtotal: number;
  discount_total: number;
  discount_code: string | null;
  discount_ids: string[];
  shipping_amount: number | null;
  tax_amount: number | null;
  total: number | null;
  record_type: "Request" | "Confirmed";
  payment_status: PaymentStatus;
  payment_verified_at: string | null;
  payment_provider: string | null;
  payment_transaction_id: string | null;
  payu_payment_id: string | null;
  payment_gateway_status: string | null;
  payment_error: string;
  payment_created_at: string | null;
  inventory_reservation_status: string | null;
  invoice_id: string | null;
  invoice_number: string;
  invoice_status: string;
  invoice_error: string;
  credit_note_id: string | null;
  credit_note_number: string;
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
  request_received_email_status: EmailDeliveryStatus;
  request_received_email_sent_at: string | null;
  request_received_email_id: string | null;
  paid_email_status: EmailDeliveryStatus;
  paid_email_sent_at: string | null;
  paid_email_id: string | null;
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

export interface PaymentQuoteResponse {
  regular_subtotal: number;
  discount_total: number;
  subtotal: number;
  shipping_amount: number;
  total: number;
  currency: "INR";
}

export interface PayUCheckoutResponse extends PaymentQuoteResponse {
  action: string;
  fields: Record<string, string>;
  request_number: string;
  transaction_id: string;
}

export interface PaymentStatusResponse {
  transaction_id: string;
  request_number: string;
  status: "pending" | "paid" | "failed";
  amount: number;
  currency: "INR";
  updated_at: string;
}