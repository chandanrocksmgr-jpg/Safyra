import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { apiPost, ApiError } from "@/lib/api";
import type { AuthResponse } from "@/lib/auth";
import { beginSession } from "@/lib/session";

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const signup = useMutation({ mutationFn: () => apiPost<AuthResponse>("/auth/signup", form), onSuccess: ({ user }) => { beginSession(user); navigate("/account"); }, onError: (reason) => setError(reason instanceof ApiError && reason.status === 409 ? "An account already exists for this email." : "Check that your password meets every requirement.") });
  const submit = (event: FormEvent) => { event.preventDefault(); setError(""); signup.mutate(); };
  return <div className="page-shell"><BrandHeader /><main className="auth-page"><section className="auth-visual signup-visual"><img src="https://safyra.co/cdn/shop/files/F849CF0B-33AC-4B28-9058-B737D786C43F.png?v=1780243912&width=1200" alt="SAFYRA handwork detail" /><div><span className="eyebrow">Made personal</span><h1>Your edit,<br /><em>kept together.</em></h1></div></section><section className="auth-panel"><div className="auth-card"><span className="eyebrow">Customer account</span><h2>Create your account</h2><p>Save favourites, continue your bag across devices and follow every order.</p><form onSubmit={submit} data-testid="customer-signup-form"><label>Full name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} autoComplete="name" required data-testid="customer-signup-name" /></label><label>Email address<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} autoComplete="email" required data-testid="customer-signup-email" /></label><label>Password<input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} autoComplete="new-password" required data-testid="customer-signup-password" /><small>10+ characters with uppercase, lowercase, number and symbol.</small></label>{error && <div className="form-error" data-testid="customer-signup-error">{error}</div>}<button className="button button-dark button-full" disabled={signup.isPending} data-testid="customer-signup-submit">{signup.isPending ? "Creating account…" : <>Create account <ArrowRight size={16} /></>}</button></form><div className="auth-links"><span>Already have an account?</span><Link to="/login" data-testid="customer-login-link">Sign in</Link></div></div></section></main></div>;
}