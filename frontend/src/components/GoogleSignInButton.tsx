interface GoogleSignInButtonProps {
  label?: string;
  testId: string;
}

export default function GoogleSignInButton({ label = "Continue with Google", testId }: GoogleSignInButtonProps) {
  const beginGoogleSignIn = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/account";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return <button type="button" className="google-signin-button" onClick={beginGoogleSignIn} data-testid={testId}>
    <span className="google-mark" aria-hidden="true">G</span><span>{label}</span>
  </button>;
}