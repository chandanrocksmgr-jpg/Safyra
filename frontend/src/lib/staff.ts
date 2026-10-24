/** Mirrors backend models/staff.py. */
export interface StaffMember {
  id: string;
  email: string;
  name: string;
  admin_role: "super" | "junior";
  status: "active" | "deactivated";
  created_at: string;
  last_login_at: string | null;
}

export interface StaffCreate {
  name: string;
  email: string;
  password: string;
}

export interface StaffUpdate {
  name?: string;
  status?: "active" | "deactivated";
}
