import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, UserPlus, Power, Trash2, KeyRound } from "lucide-react";
import { toast } from "sonner";
import AdminShell from "@/components/AdminShell";
import { apiDelete, apiGet, apiPatch, apiPost, apiPut, ApiError } from "@/lib/api";
import type { StaffMember } from "@/lib/staff";

const emptyForm = { name: "", email: "", password: "" };

export default function AdminStaff() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyForm);
  const [resetFor, setResetFor] = useState("");
  const [resetPassword, setResetPassword] = useState("");
  const { data: staff = [], isLoading } = useQuery({ queryKey: ["admin-staff"], queryFn: () => apiGet<StaffMember[]>("/admin/staff") });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
  const fail = (reason: unknown, fallback: string) => toast.error(reason instanceof ApiError ? String((reason.body as { detail?: string } | null)?.detail || fallback) : fallback);

  const create = useMutation({
    mutationFn: () => apiPost<StaffMember>("/admin/staff", { name: form.name, email: form.email, password: form.password }),
    onSuccess: () => { toast.success("Junior Admin created"); setForm(emptyForm); void refresh(); },
    onError: (reason) => fail(reason, "Could not create this account"),
  });
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "active" | "deactivated" }) => apiPatch<StaffMember>(`/admin/staff/${id}`, { status }),
    onSuccess: (member) => { toast.success(member.status === "active" ? "Account activated" : "Account deactivated"); void refresh(); },
    onError: (reason) => fail(reason, "Could not update this account"),
  });
  const remove = useMutation({
    mutationFn: (id: string) => apiDelete<void>(`/admin/staff/${id}`),
    onSuccess: () => { toast.success("Account deleted"); void refresh(); },
    onError: (reason) => fail(reason, "Could not delete this account"),
  });
  const resetPasswordMutation = useMutation({
    mutationFn: () => apiPut<void>(`/admin/staff/${resetFor}/password`, { new_password: resetPassword }),
    onSuccess: () => { toast.success("Password replaced and the account signed out"); setResetFor(""); setResetPassword(""); },
    onError: (reason) => fail(reason, "Use 10+ characters with upper, lower, number and symbol"),
  });

  const submit = (event: FormEvent) => { event.preventDefault(); create.mutate(); };

  return <AdminShell eyebrow="Restricted staff workspace" title="Staff & access." description="Create Junior Admins who can manage the catalogue only. Orders, customers, payments and settings stay with you.">
    <section className="admin-dashboard-section" data-testid="admin-staff-create-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">New access</span><h2>Add a Junior Admin</h2></div><UserPlus size={22} /></div>
      <form onSubmit={submit} className="admin-staff-form" data-testid="admin-staff-form">
        <label>Full name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required minLength={2} data-testid="admin-staff-name" /></label>
        <label>Work email<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required data-testid="admin-staff-email" /></label>
        <label>Temporary password<input type="text" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required data-testid="admin-staff-password" /><small>10+ characters with upper, lower, number and symbol. Share it privately.</small></label>
        <button className="button button-dark" disabled={create.isPending} data-testid="admin-staff-submit"><UserPlus size={15} /> Create Junior Admin</button>
      </form>
      <p className="admin-staff-note">Junior Admins can create and edit products, images, colours, sizes, prices and stock. They cannot open orders, customers, payments, store settings or staff access.</p>
    </section>

    <section className="admin-dashboard-section" data-testid="admin-staff-list-panel">
      <div className="admin-section-heading"><div><span className="eyebrow">Accounts</span><h2>{staff.length} staff {staff.length === 1 ? "account" : "accounts"}</h2></div><ShieldCheck size={22} /></div>
      {isLoading ? <p>Loading staff…</p> : <ul className="admin-staff-list" data-testid="admin-staff-list">
        {staff.map((member) => <li key={member.id} data-testid={`admin-staff-row-${member.email}`}>
          <div className="admin-staff-identity">
            <strong>{member.name}</strong>
            <span>{member.email}</span>
            <span className={member.admin_role === "super" ? "staff-tag staff-tag-super" : "staff-tag"} data-testid={`admin-staff-role-${member.email}`}>{member.admin_role === "super" ? "Super Admin" : "Junior Admin"}</span>
            <span className={member.status === "active" ? "staff-tag staff-tag-active" : "staff-tag staff-tag-off"} data-testid={`admin-staff-status-${member.email}`}>{member.status === "active" ? "Active" : "Deactivated"}</span>
          </div>
          {member.admin_role === "junior" ? <div className="admin-staff-actions">
            <button type="button" onClick={() => setStatus.mutate({ id: member.id, status: member.status === "active" ? "deactivated" : "active" })} data-testid={`admin-staff-toggle-${member.email}`}><Power size={14} /> {member.status === "active" ? "Deactivate" : "Activate"}</button>
            <button type="button" onClick={() => { setResetFor(member.id); setResetPassword(""); }} data-testid={`admin-staff-reset-${member.email}`}><KeyRound size={14} /> Reset password</button>
            <button type="button" className="is-danger" onClick={() => { if (window.confirm(`Delete ${member.email}? This cannot be undone.`)) remove.mutate(member.id); }} data-testid={`admin-staff-delete-${member.email}`}><Trash2 size={14} /> Delete</button>
          </div> : <span className="admin-staff-locked" data-testid={`admin-staff-locked-${member.email}`}>Full control · not editable here</span>}
          {resetFor === member.id && <form className="admin-staff-reset" onSubmit={(event) => { event.preventDefault(); resetPasswordMutation.mutate(); }} data-testid={`admin-staff-reset-form-${member.email}`}>
            <input value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} placeholder="New password" required data-testid={`admin-staff-reset-input-${member.email}`} />
            <button className="button button-dark" disabled={resetPasswordMutation.isPending} data-testid={`admin-staff-reset-submit-${member.email}`}>Replace password</button>
            <button type="button" onClick={() => setResetFor("")} data-testid={`admin-staff-reset-cancel-${member.email}`}>Cancel</button>
          </form>}
        </li>)}
      </ul>}
    </section>
  </AdminShell>;
}
