import type { CartItem } from "@/lib/shop";

export interface User {
  id: string;
  email: string;
  name: string;
  role: "customer" | "admin";
  phone: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
}

export interface TrackingStep {
  label: string;
  completed: boolean;
  date: string;
}

export interface OrderItem {
  product_name: string;
  image_url: string;
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
  is_demo: boolean;
  items: OrderItem[];
  tracking: TrackingStep[];
}

export interface AccountResponse {
  user: User;
  wishlist_ids: string[];
  cart: CartItem[];
  orders: Order[];
}

export interface RecoveryQuestionResponse {
  question: string;
}