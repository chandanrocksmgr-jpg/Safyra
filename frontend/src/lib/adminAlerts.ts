/** Mirrors backend routers/admin_alerts.py (AdminOrderAlert / AdminOrderAlertList). */
export interface AdminOrderAlert {
  id: string;
  request_id: string;
  request_number: string;
  customer_name: string;
  customer_mobile: string;
  total: number;
  item_count: number;
  payment_provider: string;
  created_at: string;
  email_status: string;
}

export interface AdminOrderAlertList {
  alerts: AdminOrderAlert[];
  alert_email: string;
}
