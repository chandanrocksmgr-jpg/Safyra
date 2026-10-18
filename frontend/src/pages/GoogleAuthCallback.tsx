import { useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, LoaderCircle, ShieldAlert } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { apiPost } from "@/lib/api";
import type { GoogleAuthResponse } from "@/lib/auth";
import { beginSession } from "@/lib/session";

export default function GoogleAuthCallback() {
  const location = useLocation();
  const navigate = useNavigate();
  const processed = useRef(false);
  const sessionId = new URLSearchParams(location.hash.replace(/^#/, "")).get("session_id") ?? "";
  const exchange = useMutation({
    mutationFn: () => apiPost<GoogleAuthResponse>("/auth/google/session", { session_id: sessionId }),
    onSuccess: ({ user }) => {
      beginSession(user);
      navigate("/account", { replace: true });
    },
    onError: () => {
      window.history.replaceState(null, document.title, location.pathname);
    },
  });
  useEffect(() => {
    if (!sessionId || processed.current) return;
    processed.current = true;
    exchange.mutate();
  }, [exchange, sessionId]);
  if (!sessionId) return <main className="google-callback-page" data-testid="google-callback-invalid"><ShieldAlert /><h1>Google sign-in could not be completed.</h1><Link to="/login" className="button button-dark" data-testid="google-callback-login">Return to sign in</Link></main>;
  if (exchange.isError) return <main className="google-callback-page" data-testid="google-callback-error"><ShieldAlert /><span className="eyebrow">Secure sign-in</span><h1>We could not verify that Google response.</h1><p>No SAFYRA account or Admin access was changed.</p><Link to="/login" className="button button-dark" data-testid="google-callback-retry">Try again</Link></main>;
  return <main className="google-callback-page" data-testid="google-callback-processing"><LoaderCircle className="google-callback-spinner" /><span className="eyebrow">Secure sign-in</span><h1>Bringing your SAFYRA wardrobe together.</h1><p><CheckCircle2 size={15} /> Your Google response is being verified server-side.</p></main>;
}