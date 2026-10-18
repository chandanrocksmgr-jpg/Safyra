# Emergent Google Auth Testing Playbook

## Required callback checks
- Start Google sign-in from the current browser origin only; never hardcode or add a fallback redirect URL.
- The callback returns to `/account#session_id=...`.
- Callback detection must use React Router `useLocation().hash` synchronously before protected routing.
- The auth provider must skip its normal session check while a `session_id` fragment is present.
- Exchange the `session_id` server-side through Emergent Auth `/session-data`; never call it from the browser.
- Process the fragment once with a `useRef`, clear it immediately, then verify the server session.

## Session checks
- The backend is the source of truth through `/api/auth/me` or the app's equivalent session endpoint.
- Persist only a server-side session and an httpOnly secure cookie; never store OAuth tokens in browser storage.
- A Google email matching an existing customer links to that same user and preserves wishlist, cart and orders.
- A Google-verified email claims only exact-email eligible paid guest orders and invoices.
- Google authentication must never grant the Admin role or access `/admin`.
- Email/password customer login and separate Admin email/password login must remain functional.

## Browser checks
- Start Google sign-in from preview/deployed/custom domains and confirm the redirect derives from `window.location.origin`.
- Confirm callback does not race the global auth provider or remain stuck after the hash is cleared.
- Confirm My Account loads after exchange and `/api/auth/session` returns the linked customer.
- Confirm logout removes the server session and clears the cookie.

## Test identity and cleanup
- Record allowed Google test identities and linked app users in `/app/memory/test_credentials.md` without passwords.
- Any seeded test user/session/order must use a unique test marker and be deleted after verification.
- Never create or preserve a Google-authenticated Admin account.