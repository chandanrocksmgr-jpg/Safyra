"""PayU reconciliation cron endpoint is protected and idempotent: a missing/wrong Bearer
secret is rejected with 401; an authorized call is accepted quickly with 202; and a duplicate
webhook/run id is acknowledged without duplicate processing."""
import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

from tests.conftest import API_URL

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
CRON_SECRET = os.environ["WEBHOOK_CRON_SECRET"]


def test_missing_or_wrong_secret_returns_401(client):
    run_id = f"tscheck-payu-cron-{uuid.uuid4().hex[:10]}"
    payload = {"event": "scheduled", "run_id": run_id, "schedule_id": "tscheck-schedule"}

    no_auth = client.post("/cron/payu-reconcile", json=payload)
    assert no_auth.status_code == 401, f"missing secret expected 401, got {no_auth.status_code}: {no_auth.text[:300]}"

    wrong_auth = client.post(
        "/cron/payu-reconcile", json=payload,
        headers={"Authorization": "Bearer not-the-real-secret"},
    )
    assert wrong_auth.status_code == 401, f"wrong secret expected 401, got {wrong_auth.status_code}: {wrong_auth.text[:300]}"


def test_authorized_cron_call_is_fast_and_idempotent_on_duplicate(client):
    run_id = f"tscheck-payu-cron-{uuid.uuid4().hex[:10]}"
    payload = {"event": "scheduled", "run_id": run_id, "schedule_id": "tscheck-schedule"}
    headers = {"Authorization": f"Bearer {CRON_SECRET}"}

    with httpx.Client(base_url=API_URL, timeout=10.0) as timed_client:
        first = timed_client.post("/cron/payu-reconcile", json=payload, headers=headers)
    assert first.status_code == 202, f"authorized cron call expected 202, got {first.status_code}: {first.text[:300]}"
    first_body = first.json()
    assert first_body["accepted"] is True
    assert first_body["duplicate"] is False

    duplicate = client.post("/cron/payu-reconcile", json=payload, headers=headers)
    assert duplicate.status_code == 202, f"duplicate cron call expected 202, got {duplicate.status_code}: {duplicate.text[:300]}"
    duplicate_body = duplicate.json()
    assert duplicate_body["accepted"] is True
    assert duplicate_body["duplicate"] is True, "re-submitting the same run_id must be acknowledged as a duplicate, not reprocessed"
