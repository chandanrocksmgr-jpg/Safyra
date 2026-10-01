"""Criterion: Collections and categories are independently editable.

Creates a temporary Draft category/collection group, verifies admin can
create/edit/delete it, and confirms it stays absent from the public
/api/catalog-groups results (which only return status=active groups).
"""
import uuid

import httpx




def test_draft_catalog_group_crud_and_hidden_publicly(admin_client):
    slug = f"tscheck-draft-group-{uuid.uuid4().hex[:8]}"
    payload = {
        "name": slug,
        "slug": slug,
        "group_type": "collection",
        "description": "tscheck temporary draft collection",
        "status": "draft",
        "sort_order": 999,
        "show_on_home": True,
        "image_url": "https://example.com/tscheck-group.jpg",
    }
    created = None
    try:
        resp = admin_client.post("/catalog-groups", json=payload)
        assert resp.status_code == 201, f"create draft group failed: {resp.status_code} {resp.text[:300]}"
        created = resp.json()
        group_id = created["id"]
        assert created["status"] == "draft"

        # Edit it
        patch = admin_client.patch(f"/catalog-groups/{group_id}", json={"sort_order": 5, "description": "tscheck edited"})
        assert patch.status_code == 200, f"edit draft group failed: {patch.status_code} {patch.text[:300]}"
        assert patch.json()["sort_order"] == 5
        assert patch.json()["description"] == "tscheck edited"

        # Visible to admin (include_all=true)
        admin_list = admin_client.get("/catalog-groups?include_all=true")
        assert admin_list.status_code == 200
        admin_ids = {g["id"] for g in admin_list.json()}
        assert group_id in admin_ids, "draft group should be visible to admin include_all listing"

        # Absent from public catalog-groups (status filter defaults to active-only)
        with httpx.Client(base_url="http://localhost:8001/api") as anon:
            public_list = anon.get("/catalog-groups")
        assert public_list.status_code == 200
        public_ids = {g["id"] for g in public_list.json()}
        assert group_id not in public_ids, "draft group leaked into public /api/catalog-groups"
    finally:
        if created:
            del_resp = admin_client.delete(f"/catalog-groups/{created['id']}")
            assert del_resp.status_code == 204, f"cleanup delete failed: {del_resp.status_code} {del_resp.text[:200]}"
