import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Eye, EyeOff, LockKeyhole } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { apiPost, ApiError } from "@/lib/api";
import type { AuthResponse } from "@/lib/auth";
import { beginSession } from "@/lib/session";
import GoogleSignInButton from "@/components/GoogleSignInButton";
import { GOOGLE_SIGN_IN_ENABLED } from "@/lib/features";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const login = useMutation({ mutationFn: () => apiPost<AuthResponse>("/auth/login", { email, password }), onSuccess: ({ user }) => { beginSession(user); navigate((location.state as { from?: string } | null)?.from ?? "/account"); }, onError: (reason) => setError(reason instanceof ApiError && reason.status === 401 ? "That email and password do not match." : "Sign in is unavailable right now.") });
  const submit = (event: FormEvent) => { event.preventDefault(); setError(""); login.mutate(); };
  return <div className="page-shell"><BrandHeader /><main className="auth-page"><section className="auth-visual"><img src="/api/media/shopify/IMG_3973.jpg" alt="SAFYRA Aira Pure Kota Doria Angrakha" /><div><span className="eyebrow">Your SAFYRA wardrobe</span><h1>Welcome<br /><em>back.</em></h1><p>Sign in to keep your wishlist, bag and order journey together.</p></div></section><section className="auth-panel"><div className="auth-card"><LockKeyhole size={22} /><span className="eyebrow">Customer account</span><h2>Sign in</h2><p>Access saved pieces, order history, invoices and tracking.</p>{GOOGLE_SIGN_IN_ENABLED && <><GoogleSignInButton testId="customer-google-login" /><div className="auth-divider" data-testid="customer-login-divider"><span>or use email</span></div></>}<form onSubmit={submit} data-testid="customer-login-form"><label>Email address<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required data-testid="customer-login-email" /></label><label>Password<div className="password-field"><input type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required data-testid="customer-login-password" /><button type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label="Show password" data-testid="customer-login-password-toggle">{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>{error && <div className="form-error" data-testid="customer-login-error">{error}</div>}<button className="button button-dark button-full" disabled={login.isPending} data-testid="customer-login-submit">{login.isPending ? "Signing in…" : <>Sign in <ArrowRight size={16} /></>}</button></form><div className="auth-links"><span>New to SAFYRA?</span><Link to="/signup" data-testid="customer-signup-link">Create an account</Link><Link to="/shop" data-testid="continue-as-guest-link">Continue shopping as guest</Link></div></div></section></main></div>;
}