"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os
import tempfile

import httpx
import pytest
import pytest_asyncio
from filelock import FileLock

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Async variant, for tests that also await motor/backend helpers directly."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# --- app-specific fixtures below this line ---

ADMIN_EMAIL = os.environ.get("TSCHECK_ADMIN_EMAIL", "admin@safyra.co")
ADMIN_PASSWORD = os.environ.get("TSCHECK_ADMIN_PASSWORD", "Safyra!Admin#2026")
CUSTOMER_EMAIL = os.environ.get("TSCHECK_CUSTOMER_EMAIL", "customer@safyra.co")
CUSTOMER_PASSWORD = os.environ.get("TSCHECK_CUSTOMER_PASSWORD", "Safyra!Customer#2026")


SESSION_COOKIE = "safyra_session"


def rebind_session_cookie(c: "httpx.Client", login_response: "httpx.Response") -> None:
    """The app sets the session cookie with Secure (APP_URL is https in this env), so httpx's
    cookie jar correctly refuses to replay it over the plain-http localhost connection used by
    these tests. Re-set the same token without the secure flag so the client can keep sending it
    to http://localhost:8001 exactly as the browser would over the real https deployment."""
    token = login_response.cookies.get(SESSION_COOKIE)
    assert token, f"no {SESSION_COOKIE} cookie on login response: {dict(login_response.cookies)}"
    c.cookies.set(SESSION_COOKIE, token)


ADMIN_ACCOUNT_LOCK_PATH = os.path.join(tempfile.gettempdir(), "tscheck_admin_account.lock")


@pytest.fixture
def admin_account_lock():
    """Serializes any test that reads or mutates the single seeded admin account's password/
    sessions across pytest-xdist workers. Without this, a password-change/session-invalidation
    test in one module (scheduled on one worker under --dist loadscope) can run concurrently with
    an admin-authenticated request in a different module on another worker, invalidating that
    other worker's freshly-issued session mid-request. Request this fixture (directly, or via
    admin_client below) in any test that logs in as the seeded admin or changes its password."""
    lock = FileLock(ADMIN_ACCOUNT_LOCK_PATH, timeout=60)
    with lock:
        yield


@pytest.fixture
def admin_client(admin_account_lock):
    """httpx client authenticated as the seeded admin (session cookie persisted across requests).

    Holds admin_account_lock for the fixture's lifetime (i.e. for the whole test), so this test's
    admin session cannot be invalidated by a concurrent password-change test on another worker.
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.post("/auth/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        assert resp.status_code == 200, f"admin login failed: {resp.status_code} {resp.text[:300]}"
        rebind_session_cookie(c, resp)
        yield c


@pytest.fixture
def customer_client():
    """httpx client authenticated as the seeded demo customer (session cookie persisted)."""
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        resp = c.post("/auth/login", json={"email": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD})
        assert resp.status_code == 200, f"customer login failed: {resp.status_code} {resp.text[:300]}"
        rebind_session_cookie(c, resp)
        yield c
