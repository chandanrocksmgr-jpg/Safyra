import { useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, MailCheck, X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import BrandHeader from "@/components/BrandHeader";
import { apiPost } from "@/lib/api";
import type { VerificationResponse } from "@/lib/auth";

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const started = useRef(false);
  const queryClient = useQueryClient();
  const verify = useMutation({ mutationFn: () => apiPost<VerificationResponse>("/email-verification/confirm", { token }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["session"] }); queryClient.invalidateQueries({ queryKey: ["account"] }); } });
  useEffect(() => { if (token && !started.current) { started.current = true; verify.mutate(); } }, [token, verify]);
  return <div className="page-shell"><BrandHeader /><main className="verification-page" data-testid="verification-page">{!token || verify.isError ? <section className="verification-card"><X /><span className="eyebrow">Link unavailable</span><h1>This confirmation link is invalid or expired.</h1><p>Sign in to My Account and request a fresh private link.</p><Link to="/account" className="button button-dark" data-testid="verification-account-link">Go to My Account</Link></section> : verify.isPending ? <section className="verification-card"><MailCheck /><span className="eyebrow">Private account check</span><h1>Confirming your email…</h1></section> : <section className="verification-card"><Check /><span className="eyebrow">Email confirmed</span><h1>Your SAFYRA orders are now together.</h1><p>{verify.data?.claimed_orders ? `${verify.data.claimed_orders} eligible guest order${verify.data.claimed_orders === 1 ? "" : "s"} added to My Account.` : "Your verified account is ready for future orders and invoices."}</p><Link to="/account" className="button button-dark" data-testid="verification-view-orders">View My Account</Link></section>}</main></div>;
}