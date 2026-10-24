// Mirrors backend/models/store_credit.py
export interface StoreCreditGrant {
  id: string;
  amount: number;
  remaining: number;
  issued_at: string;
  expires_at: string;
  status: "Active" | "Used" | "Expired";
}

export interface StoreCreditActivity {
  id: string;
  type: "issued" | "redeemed" | "restored";
  amount: number;
  request_number: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface StoreCreditSummary {
  balance: number;
  next_expiry: string | null;
  next_expiry_amount: number;
  grants: StoreCreditGrant[];
  activity: StoreCreditActivity[];
}

export interface StoreCreditIssue {
  amount: number;
}

export interface AdminCustomerRow {
  id: string;
  name: string;
  email: string;
  phone: string;
  created_at: string | null;
  credit_balance: number;
}

export interface AdminCustomerOrder {
  request_number: string;
  total: number;
  credit_applied: number;
  payment_status: string;
  fulfilment_status: string;
  created_at: string | null;
}

export interface AdminCustomerDetail extends AdminCustomerRow {
  credits: StoreCreditSummary;
  orders: AdminCustomerOrder[];
}

export const formatCreditDate = (value: string | null) =>
  value ? new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";

export const CREDIT_ACTIVITY_LABEL: Record<StoreCreditActivity["type"], string> = {
  issued: "Credit added",
  redeemed: "Used on order",
  restored: "Returned (payment not completed)",
};
