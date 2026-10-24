import { useEffect, useRef, useState } from "react";
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
  const [failed, setFailed] = useState(false);
  // One-time session exchange with local state (not useMutation): under StrictMode a mutation fired from a mount
  // effect loses its observer, so the error state never reached this screen and the spinner hung forever.
  useEffect(() => {
    if (!sessionId || processed.current) return;
    processed.current = true;
    apiPost<GoogleAuthResponse>("/auth/google/session", { session_id: sessionId })
      .then(({ user }) => {
        beginSession(user);
        navigate("/account", { replace: true });
      })
      .catch(() => {
        // Drop the single-use session_id from the address bar; this screen stays mounted to show the retry state.
        window.history.replaceState(null, document.title, location.pathname);
        setFailed(true);
      });
  }, [location.pathname, navigate, sessionId]);
  if (!sessionId) return <main className="google-callback-page" data-testid="google-callback-invalid"><ShieldAlert /><h1>Google sign-in could not be completed.</h1><Link to="/login" className="button button-dark" data-testid="google-callback-login">Return to sign in</Link></main>;
  if (failed) return <main className="google-callback-page" data-testid="google-callback-error"><ShieldAlert /><span className="eyebrow">Secure sign-in</span><h1>We could not verify that Google response.</h1><p>No SAFYRA account or Admin access was changed.</p><Link to="/login" className="button button-dark" data-testid="google-callback-retry">Try again</Link></main>;
  return <main className="google-callback-page" data-testid="google-callback-processing"><LoaderCircle className="google-callback-spinner" /><span className="eyebrow">Secure sign-in</span><h1>Bringing your SAFYRA wardrobe together.</h1><p><CheckCircle2 size={15} /> Your Google response is being verified server-side.</p></main>;
}