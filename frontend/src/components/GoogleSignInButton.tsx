interface GoogleSignInButtonProps {
  label?: string;
  testId: string;
  /** In-app path Google returns to (the callback then stays on it), e.g. "/checkout". */
  returnTo?: "/account" | "/checkout";
}

export default function GoogleSignInButton({ label = "Continue with Google", testId, returnTo = "/account" }: GoogleSignInButtonProps) {
  const beginGoogleSignIn = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + returnTo;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return <button type="button" className="google-signin-button" onClick={beginGoogleSignIn} data-testid={testId}>
    <span className="google-mark" aria-hidden="true">G</span><span>{label}</span>
  </button>;
}