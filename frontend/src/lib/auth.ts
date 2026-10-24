import type { CartItem } from "@/lib/shop";

export interface User {
  id: string;
  email: string;
  name: string;
  role: "customer" | "admin";
  phone: string;
  email_verified: boolean;
  email_verified_at: string | null;
  picture_url: string;
  auth_providers: string[];
  created_at: string;
}

export interface AuthResponse {
  user: User;
}

export interface GoogleAuthResponse extends AuthResponse {
  claimed_orders: number;
}

export interface TrackingStep {
  label: string;
  completed: boolean;
  date: string;
}

export interface OrderItem {
  product_name: string;
  image_url: string;
  set_type: string;
  size: string;
  color: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  order_number: string;
  placed_at: string;
  status: string;
  total: number;
  invoice_number: string;
  invoice_id: string | null;
  invoice_status: string;
  courier_name: string;
  tracking_number: string;
  tracking_link: string;
  is_demo: boolean;
  items: OrderItem[];
  tracking: TrackingStep[];
}

export interface SavedAddressInput {
  label: string;
  name: string;
  phone: string;
  address: string;
  city: string;
  state_region: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export interface SavedAddress extends SavedAddressInput {
  id: string;
}

export interface AccountResponse {
  user: User;
  wishlist_ids: string[];
  cart: CartItem[];
  orders: Order[];
  addresses: SavedAddress[];
}

export interface RecoveryQuestionResponse {
  question: string;
}

export interface VerificationResponse { verified: boolean; claimed_orders: number }
export interface VerificationSendResponse { accepted: boolean }
export interface PasswordResetResponse { accepted: boolean }