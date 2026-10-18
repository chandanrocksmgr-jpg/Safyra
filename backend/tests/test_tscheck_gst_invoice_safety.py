"""GST invoice configuration is legally safe while details are missing: /store-settings
identifies every missing GST field, blocks real invoice generation, exposes a clearly
watermarked SAMPLE preview PDF, and keeps the invoice sequence at 1 (0001) until genuine
settings are complete. Read-only against the live (intentionally incomplete) settings row --
this file never patches /store-settings, so it cannot drift the real configuration."""
import base64
import re
import zlib


def _pdf_contains_text(pdf_bytes: bytes, needle: str) -> bool:
    """Best-effort text search inside a reportlab-generated PDF: content streams here are
    ASCII85Decode+FlateDecode-encoded, so decode each `stream ... endstream` block and look for
    the needle in the decoded bytes (covers the common case of literal `(...) Tj` text runs)."""
    if needle.encode() in pdf_bytes:
        return True
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", pdf_bytes, re.DOTALL):
        raw = match.group(1).strip()
        if raw.endswith(b"~>"):
            raw = raw[:-2]
        try:
            decoded = zlib.decompress(base64.a85decode(raw))
        except (zlib.error, ValueError):
            continue
        if needle.encode() in decoded:
            return True
    return False


def test_store_settings_identifies_missing_fields_and_blocks_invoicing(admin_client):
    resp = admin_client.get("/store-settings")
    assert resp.status_code == 200, f"GET /store-settings -> {resp.status_code}: {resp.text[:300]}"
    settings = resp.json()
    assert settings["invoice_ready"] is False, "invoice generation should be blocked while GST fields are incomplete"
    expected_missing = {"GSTIN", "registered address", "seller state", "state code", "GST rate", "HSN code", "support email", "support phone", "authorised signatory"}
    assert expected_missing <= set(settings["missing_fields"]), f"missing_fields should list every blank GST field, got {settings['missing_fields']}"
    assert settings["invoice_next_number"] == 1, "invoice sequence must stay at 0001 while settings are incomplete"
    assert settings["legal_name"] == "SAFYRA CHIKANKARI"


def test_store_settings_requires_admin(client):
    resp = client.get("/store-settings")
    assert resp.status_code in (401, 403), f"anonymous store-settings access expected 401/403, got {resp.status_code}: {resp.text[:300]}"


def test_sample_invoice_preview_is_clearly_watermarked_not_a_real_invoice(admin_client):
    resp = admin_client.get("/store-settings/invoice-preview")
    assert resp.status_code == 200, f"GET /store-settings/invoice-preview -> {resp.status_code}: {resp.text[:300]}"
    assert resp.headers["content-type"] == "application/pdf"
    assert "SAFYRA-SAMPLE-INVOICE.pdf" in resp.headers.get("content-disposition", "")
    body = resp.content
    assert body.startswith(b"%PDF"), "response should be a real PDF document"
    assert _pdf_contains_text(body, "SAMPLE - NOT A TAX INVOICE"), "sample preview must carry an explicit, visible non-tax-invoice watermark"
