import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { apiPost, ApiError } from "@/lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const reset = useMutation({
    mutationFn: () => apiPost<null>("/auth/password-reset/confirm", { token, new_password: password }),
    onSuccess: () => navigate("/login", { replace: true, state: { from: "/account" } }),
    onError: (reason) => {
      const detail = reason instanceof ApiError && typeof (reason.body as { detail?: unknown } | null)?.detail === "string" ? String((reason.body as { detail: string }).detail) : "";
      setError(reason instanceof ApiError && reason.status === 400 ? (detail || "This reset link is invalid or has expired.") : "We could not reset your password right now.");
    },
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (password !== confirmPassword) { setError("Both passwords must match."); return; }
    reset.mutate();
  };
  return <div className="page-shell"><BrandHeader /><main className="auth-page"><section className="auth-visual"><img src="/api/media/shopify/IMG_3973.jpg" alt="SAFYRA Chikankari" /><div><span className="eyebrow">Account recovery</span><h1>Choose a<br /><em>new password.</em></h1><p>Your saved wishlist, bag and orders stay exactly as you left them.</p></div></section><section className="auth-panel"><div className="auth-card"><LockKeyhole size={22} /><span className="eyebrow">Customer account</span><h2>Set new password</h2>{!token ? <><p data-testid="reset-password-missing-token">This reset link is incomplete. Please request a fresh link.</p><Link to="/forgot-password" className="button button-dark button-full" data-testid="reset-password-request-new">Request a new link</Link></> : <><p>Links work once and expire 10 minutes after they are sent.</p><form onSubmit={submit} data-testid="reset-password-form"><label>New password<input type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} required data-testid="reset-password-new" /><small>10+ characters with upper, lower, number and symbol.</small></label><label>Confirm new password<input type="password" autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required data-testid="reset-password-confirm" /></label>{error && <div className="form-error" data-testid="reset-password-error">{error}</div>}<button className="button button-dark button-full" disabled={reset.isPending} data-testid="reset-password-submit">{reset.isPending ? "Updating…" : <>Update password <ArrowRight size={16} /></>}</button></form><div className="auth-links"><Link to="/forgot-password" data-testid="reset-password-resend-link">Send me a new link</Link></div></>}</div></section></main></div>;
}
