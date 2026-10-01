"""Collections can be safely archived/restored; legacy DELETE soft-archives instead of
destroying data; archived groups disappear from the anonymous catalog-groups listing."""

import time

import httpx


def _unique_name(prefix: str) -> str:
    return f"tscheck-{prefix}-{int(time.time() * 1000)}"


def test_archive_and_restore_round_trip(admin_client: httpx.Client):
    name = _unique_name("archive")
    create = admin_client.post("/catalog-groups", json={
        "name": name,
        "slug": name,
        "group_type": "collection",
        "status": "active",
    })
    assert create.status_code == 201, create.text[:300]
    group = create.json()
    group_id = group["id"]

    # Active group is visible to anonymous callers.
    anon_list = httpx.get("http://localhost:8001/api/catalog-groups")
    assert anon_list.status_code == 200
    assert any(g["id"] == group_id for g in anon_list.json()), "new active group missing from anonymous listing"

    # Archive via the supported PATCH status transition (no data loss expected).
    archive = admin_client.patch(f"/catalog-groups/{group_id}", json={"status": "archived"})
    assert archive.status_code == 200, archive.text[:300]
    assert archive.json()["status"] == "archived"
    assert archive.json()["name"] == name, "archiving must not alter the stored name/data"

    # Archived group disappears from the anonymous listing.
    anon_list_after = httpx.get("http://localhost:8001/api/catalog-groups")
    assert anon_list_after.status_code == 200
    assert not any(g["id"] == group_id for g in anon_list_after.json()), "archived group still public"

    # Restore returns it to active and back into the anonymous listing.
    restore = admin_client.patch(f"/catalog-groups/{group_id}", json={"status": "active"})
    assert restore.status_code == 200, restore.text[:300]
    assert restore.json()["status"] == "active"

    anon_list_restored = httpx.get("http://localhost:8001/api/catalog-groups")
    assert any(g["id"] == group_id for g in anon_list_restored.json()), "restored group missing from anonymous listing"


def test_legacy_delete_soft_archives_instead_of_destroying(admin_client: httpx.Client):
    name = _unique_name("legacy-delete")
    create = admin_client.post("/catalog-groups", json={
        "name": name,
        "slug": name,
        "group_type": "category",
        "status": "active",
    })
    assert create.status_code == 201, create.text[:300]
    group_id = create.json()["id"]

    delete_resp = admin_client.delete(f"/catalog-groups/{group_id}")
    assert delete_resp.status_code == 204, delete_resp.text[:300]

    # Data must still exist (soft-archived), visible to an admin with include_all, not destroyed.
    admin_list = admin_client.get("/catalog-groups", params={"include_all": True})
    assert admin_list.status_code == 200
    match = next((g for g in admin_list.json() if g["id"] == group_id), None)
    assert match is not None, "legacy DELETE destroyed the record instead of soft-archiving it"
    assert match["status"] == "archived"
    assert match["name"] == name

    # And it must be hidden from the anonymous/public listing.
    anon_list = httpx.get("http://localhost:8001/api/catalog-groups")
    assert not any(g["id"] == group_id for g in anon_list.json())
