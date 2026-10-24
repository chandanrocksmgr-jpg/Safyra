# Emergent Google Auth — testing notes (SAFYRA)

Flow: Login/Signup "Continue with Google" → `https://auth.emergentagent.com/?redirect=<window.location.origin>/account`
→ Google → back to `/account#session_id=...` → `GoogleAuthCallback` POSTs `/api/auth/google/session`
→ backend calls `GET https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data` (header `X-Session-ID`)
→ creates/links a **customer** user by email (admins are refused with 403) and starts the app's own httpOnly session cookie (7 days).

- Real Google login cannot be automated; verify the button → Google hand-off, and the callback error state with a fake session id.
- A fake/expired/reused session_id makes session-data return 404 `user_data_not_found` → our API returns 401 → callback page shows "We could not verify that Google response." This is expected.
- Each session_id can be exchanged once (`oauth_exchanges` unique hash) → a replay returns 409.
- For signed-in customer flows without Google, use the password QA customer in /app/memory/test_credentials.md.
