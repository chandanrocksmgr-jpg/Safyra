import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, MailCheck } from "lucide-react";
import { Link } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { apiPost } from "@/lib/api";
import type { PasswordResetResponse } from "@/lib/auth";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const request = useMutation({ mutationFn: () => apiPost<PasswordResetResponse>("/auth/password-reset/request", { email }), onError: () => setError("We could not start the reset right now. Please try again shortly.") });
  const submit = (event: FormEvent) => { event.preventDefault(); setError(""); request.mutate(); };
  return <div className="page-shell"><BrandHeader /><main className="auth-page"><section className="auth-visual"><img src="/api/media/shopify/IMG_3973.jpg" alt="SAFYRA Chikankari" /><div><span className="eyebrow">Account recovery</span><h1>Forgot your<br /><em>password?</em></h1><p>We will email a private link so you can choose a new one.</p></div></section><section className="auth-panel"><div className="auth-card"><MailCheck size={22} /><span className="eyebrow">Customer account</span><h2>Reset password</h2>{request.isSuccess ? <><p data-testid="forgot-password-sent">If an account exists for {email}, a reset link is on its way. The link works once and expires in 10 minutes.</p><Link to="/login" className="button button-dark button-full" data-testid="forgot-password-back-to-login">Back to sign in</Link></> : <><p>Enter the email on your SAFYRA account and we will send a reset link.</p><form onSubmit={submit} data-testid="forgot-password-form"><label>Email address<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required data-testid="forgot-password-email" /></label>{error && <div className="form-error" data-testid="forgot-password-error">{error}</div>}<button className="button button-dark button-full" disabled={request.isPending} data-testid="forgot-password-submit">{request.isPending ? "Sending…" : <>Send reset link <ArrowRight size={16} /></>}</button></form><div className="auth-links"><Link to="/login" data-testid="forgot-password-login-link">Back to sign in</Link></div></>}</div></section></main></div>;
}
