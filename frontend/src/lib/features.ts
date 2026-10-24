// Emergent-managed Google sign-in (customers only). Verified 2026-10: auth.emergentagent.com hands off to Google correctly.
// Note: session-data answers 404 "user_data_not_found" for an invalid/expired/reused session_id — that is expected, not an outage.
export const GOOGLE_SIGN_IN_ENABLED = true;
