export type WaitlistStatus = "Waiting" | "Contacted" | "Converted" | "Closed";

export interface WaitlistCreate {
  product_id: string;
  customer_name: string;
  mobile: string;
  email: string | null;
  size: string | null;
  color: string | null;
  set_type: string | null;
}

export interface WaitlistSubmission {
  id: string;
  product_title: string;
  set_type: string | null;
  size: string | null;
  color: string | null;
  status: WaitlistStatus;
  created_at: string;
}

export interface WaitlistRequestAdmin {
  id: string;
  product_id: string;
  product_title: string;
  product_slug: string;
  product_image_url: string;
  customer_name: string;
  mobile: string;
  email: string | null;
  set_type: string | null;
  size: string | null;
  color: string | null;
  status: WaitlistStatus;
  admin_notes: string;
  created_at: string;
  updated_at: string;
}

export interface WaitlistAdminUpdate {
  status?: WaitlistStatus;
  admin_notes?: string;
}