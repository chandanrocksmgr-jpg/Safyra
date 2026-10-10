export type CheckoutSessionStatus = "In progress" | "Abandoned" | "Completed";
export type ReminderStatus = "Not scheduled" | "Scheduled" | "Sending" | "Sent" | "Failed";

export interface CheckoutSessionItemInput {
  product_id: string;
  set_type: string | null;
  size: string;
  color: string;
  quantity: number;
}

export interface CheckoutSessionUpsert {
  session_key: string;
  name: string;
  email: string | null;
  phone: string;
  address: string;
  city: string;
  state_region: string;
  postal_code: string;
  country: string;
  note: string;
  whatsapp_opt_in: boolean;
  marketing_email_opt_in: boolean;
  items: CheckoutSessionItemInput[];
}

export interface CheckoutSessionSummary {
  id: string;
  checkout_number: string;
  status: CheckoutSessionStatus;
  last_activity_at: string;
}

export interface CheckoutSessionStoredItem {
  product_id: string;
  title: string;
  image_url: string;
  set_type: string | null;
  size: string;
  color: string;
  quantity: number;
  regular_price: number;
  price: number;
  discount_name: string | null;
  line_total: number;
}

export interface CheckoutActivity {
  event: string;
  message: string;
  created_at: string;
}

export interface CheckoutSessionAdmin {
  id: string;
  checkout_number: string;
  session_key: string;
  status: CheckoutSessionStatus;
  name: string;
  email: string | null;
  phone: string;
  address: string;
  city: string;
  state_region: string;
  postal_code: string;
  country: string;
  note: string;
  whatsapp_opt_in: boolean;
  marketing_email_opt_in: boolean;
  items: CheckoutSessionStoredItem[];
  regular_subtotal: number;
  subtotal: number;
  discount_total: number;
  reminder_status: ReminderStatus;
  reminder_sent_at: string | null;
  reminder_email_id: string | null;
  completed_order_request_id: string | null;
  completed_request_number: string | null;
  internal_notes: string;
  started_at: string;
  last_activity_at: string;
  activity: CheckoutActivity[];
}

export interface CheckoutSessionList {
  items: CheckoutSessionAdmin[];
  total: number;
  page: number;
  page_size: number;
}