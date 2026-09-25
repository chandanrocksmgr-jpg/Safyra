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