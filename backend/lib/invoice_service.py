from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from html import escape
import uuid

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lib.dates import now_in_app_tz
from lib.db import db


REQUIRED_INVOICE_FIELDS = {
    "gstin": "GSTIN", "registered_address": "registered address", "seller_state": "seller state",
    "state_code": "state code", "gst_rate": "GST rate", "hsn_code": "HSN code",
    "support_email": "support email", "support_phone": "support phone",
    "authorised_signatory": "authorised signatory",
}


def financial_year(value: datetime) -> str:
    year = value.year if value.month >= 4 else value.year - 1
    return f"{year}-{str(year + 1)[-2:]}"


async def get_store_settings_document() -> dict:
    existing = await db.store_settings.find_one({"id": "store"})
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    document = {
        "id": "store", "legal_name": "SAFYRA CHIKANKARI", "gstin": "", "registered_address": "",
        "seller_state": "", "state_code": "", "gst_rate": None, "hsn_code": "", "support_email": None,
        "support_phone": "", "authorised_signatory": "", "invoice_prefix": "SAFYRA",
        "invoice_next_number": 1, "credit_note_prefix": "CN-SAFYRA", "credit_note_next_number": 1,
        "tax_inclusive": True, "updated_at": now,
    }
    await db.store_settings.update_one({"id": "store"}, {"$setOnInsert": document}, upsert=True)
    return await db.store_settings.find_one({"id": "store"})


def missing_invoice_fields(settings: dict) -> list[str]:
    return [label for field, label in REQUIRED_INVOICE_FIELDS.items() if not settings.get(field)]


def _tax_parts(total: int, rate: float, intra_state: bool) -> tuple[int, int, int, int]:
    gross = Decimal(total)
    tax = (gross * Decimal(str(rate)) / (Decimal("100") + Decimal(str(rate)))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    taxable = gross - tax
    if intra_state:
        cgst = (tax / 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(taxable), int(cgst), int(tax - cgst), 0
    return int(taxable), 0, 0, int(tax)


async def _next_number(field: str) -> tuple[dict, int]:
    settings = await db.store_settings.find_one_and_update(
        {"id": "store"}, {"$inc": {field: 1}}, return_document=ReturnDocument.BEFORE,
    )
    if not settings:
        settings = await get_store_settings_document()
        settings = await db.store_settings.find_one_and_update(
            {"id": "store"}, {"$inc": {field: 1}}, return_document=ReturnDocument.BEFORE,
        )
    return settings, int(settings[field])


async def generate_invoice_for_order(order_id: str) -> dict | None:
    print(f"DEBUG_TSCHECK gifo enter {order_id}", flush=True)
    existing = await db.invoices.find_one({"order_id": order_id, "document_type": "invoice"})
    if existing:
        print("DEBUG_TSCHECK gifo existing found", flush=True)
        return existing
    order = await db.orders.find_one({"id": order_id, "payment_status": "Paid"})
    if not order:
        print("DEBUG_TSCHECK gifo no order", flush=True)
        return None
    settings = await get_store_settings_document()
    missing = missing_invoice_fields(settings)
    print(f"DEBUG_TSCHECK gifo missing={missing} source_request_id={order.get('source_request_id')!r}", flush=True)
    if missing:
        message = f"Invoice blocked—complete GST settings: {', '.join(missing)}"
        await db.orders.update_one({"id": order_id}, {"$set": {"invoice_status": "blocked", "invoice_error": message}})
        await db.order_requests.update_one({"id": order["source_request_id"]}, {"$set": {"invoice_status": "blocked", "invoice_error": message}})
        return None
    print("DEBUG_TSCHECK gifo about to call _next_number", flush=True)
    settings, sequence = await _next_number("invoice_next_number")
    print(f"DEBUG_TSCHECK gifo sequence={sequence} gst_rate={settings.get('gst_rate')!r} seller_state={settings.get('seller_state')!r}", flush=True)
    local_issued_at = now_in_app_tz()
    issued_at = local_issued_at.astimezone(timezone.utc)
    number = f"{settings['invoice_prefix']}/{financial_year(local_issued_at)}/{sequence:04d}"
    total = int(order.get("total") or order.get("subtotal") or 0)
    intra_state = order.get("state_region", "").strip().lower() == settings["seller_state"].strip().lower()
    taxable, cgst, sgst, igst = _tax_parts(total, float(settings["gst_rate"]), intra_state)
    invoice_items = []
    for item in order["items"]:
        item_taxable, item_cgst, item_sgst, item_igst = _tax_parts(int(item["line_total"]), float(settings["gst_rate"]), intra_state)
        invoice_items.append({
            **item, "taxable_value": item_taxable,
            "tax_amount": item_cgst + item_sgst + item_igst,
        })
    invoice = {
        "id": str(uuid.uuid4()), "document_type": "invoice", "number": number, "sequence": sequence,
        "financial_year": financial_year(local_issued_at), "issued_at": issued_at, "order_id": order_id,
        "order_number": order["order_number"], "source_request_id": order["source_request_id"],
        "customer_id": order.get("customer_id"), "seller": {
            key: settings.get(key) for key in ["legal_name", "gstin", "registered_address", "seller_state", "state_code", "support_email", "support_phone", "authorised_signatory"]
        },
        "buyer": {key: order.get(key) for key in ["name", "email", "phone", "address", "city", "state_region", "postal_code", "country"]},
        "items": invoice_items, "hsn_code": settings["hsn_code"], "gst_rate": settings["gst_rate"],
        "place_of_supply": order.get("state_region", ""), "reverse_charge": "No",
        "regular_subtotal": order.get("regular_subtotal", order["subtotal"]), "discount_total": order.get("discount_total", 0),
        "subtotal": order["subtotal"], "shipping_amount": order.get("shipping_amount") or 0, "total": total,
        "taxable_value": taxable, "cgst": cgst, "sgst": sgst, "igst": igst, "status": "issued",
    }
    try:
        await db.invoices.insert_one(invoice)
    except DuplicateKeyError:
        return await db.invoices.find_one({"order_id": order_id, "document_type": "invoice"})
    update = {"invoice_id": invoice["id"], "invoice_number": number, "invoice_status": "issued", "invoice_error": ""}
    await db.orders.update_one({"id": order_id}, {"$set": update})
    await db.order_requests.update_one({"id": order["source_request_id"]}, {"$set": update})
    if order.get("customer_id"):
        await db.users.update_one({"id": order["customer_id"], "orders.id": order_id}, {"$set": {
            "orders.$.invoice_id": invoice["id"], "orders.$.invoice_number": number, "orders.$.invoice_status": "issued",
        }})
    return invoice


async def generate_credit_note_for_order(order_id: str) -> dict | None:
    existing = await db.invoices.find_one({"order_id": order_id, "document_type": "credit_note"})
    if existing:
        return existing
    order = await db.orders.find_one({"id": order_id, "refund_status": "Refunded"})
    invoice = await db.invoices.find_one({"order_id": order_id, "document_type": "invoice"})
    if not order or not invoice or not order.get("refund_amount"):
        return None
    settings, sequence = await _next_number("credit_note_next_number")
    local_issued_at = now_in_app_tz()
    issued_at = local_issued_at.astimezone(timezone.utc)
    number = f"{settings['credit_note_prefix']}/{financial_year(local_issued_at)}/{sequence:04d}"
    total = min(int(order["refund_amount"]), int(invoice["total"]))
    intra_state = order.get("state_region", "").strip().lower() == settings["seller_state"].strip().lower()
    taxable, cgst, sgst, igst = _tax_parts(total, float(settings["gst_rate"]), intra_state)
    credit = {
        **{key: invoice[key] for key in ["order_id", "order_number", "source_request_id", "customer_id", "seller", "buyer", "items", "hsn_code", "gst_rate"]},
        "id": str(uuid.uuid4()), "document_type": "credit_note", "number": number, "sequence": sequence,
        "financial_year": financial_year(local_issued_at), "issued_at": issued_at, "linked_invoice_id": invoice["id"],
        "linked_invoice_number": invoice["number"], "reason": order.get("refund_reason", ""),
        "subtotal": total, "shipping_amount": 0, "discount_total": 0, "regular_subtotal": total,
        "total": total, "taxable_value": taxable, "cgst": cgst, "sgst": sgst, "igst": igst, "status": "issued",
    }
    try:
        await db.invoices.insert_one(credit)
    except DuplicateKeyError:
        return await db.invoices.find_one({"order_id": order_id, "document_type": "credit_note"})
    await db.orders.update_one({"id": order_id}, {"$set": {"credit_note_id": credit["id"], "credit_note_number": number}})
    await db.order_requests.update_one({"id": order["source_request_id"]}, {"$set": {"credit_note_id": credit["id"], "credit_note_number": number}})
    return credit


def sample_invoice(settings: dict) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "document_type": "invoice", "number": "SAMPLE/NOT-ISSUED/0000", "issued_at": now,
        "order_number": "SAMPLE-ORDER", "seller": {
            "legal_name": settings.get("legal_name") or "SAFYRA CHIKANKARI",
            "gstin": settings.get("gstin") or "[ADD GSTIN]",
            "registered_address": settings.get("registered_address") or "[ADD REGISTERED ADDRESS]",
            "seller_state": settings.get("seller_state") or "[ADD STATE]", "state_code": settings.get("state_code") or "[ADD CODE]",
            "support_email": str(settings.get("support_email") or "[ADD EMAIL]"), "support_phone": settings.get("support_phone") or "[ADD PHONE]",
            "authorised_signatory": settings.get("authorised_signatory") or "[ADD SIGNATORY]",
        },
        "buyer": {"name": "Sample customer", "email": "sample@example.invalid", "phone": "—", "address": "Sample delivery address", "city": "Lucknow", "state_region": "Uttar Pradesh", "postal_code": "000000", "country": "India"},
        "items": [{"title": "Sample SAFYRA piece", "quantity": 1, "price": 1000, "line_total": 1000, "size": "M", "color": "Ivory"}],
        "hsn_code": settings.get("hsn_code") or "[ADD HSN]", "gst_rate": settings.get("gst_rate") or 0,
        "regular_subtotal": 1000, "discount_total": 0, "subtotal": 1000, "shipping_amount": 0,
        "total": 1000, "taxable_value": 1000, "cgst": 0, "sgst": 0, "igst": 0, "status": "sample",
    }


def render_invoice_pdf(document: dict, sample: bool = False) -> bytes:
    output = BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("InvoiceTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, textColor=colors.HexColor("#261C19"), alignment=TA_RIGHT)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#5C463D"))
    right = ParagraphStyle("Right", parent=small, alignment=TA_RIGHT)
    story = []
    if sample:
        story.extend([Paragraph("SAMPLE - NOT A TAX INVOICE", ParagraphStyle("Sample", parent=styles["Heading1"], alignment=TA_CENTER, textColor=colors.HexColor("#8B261D"))), Spacer(1, 6 * mm)])
    seller = document["seller"]
    doc_label = "GST TAX INVOICE" if document["document_type"] == "invoice" else "GST CREDIT NOTE"
    story.append(Table([
        [Paragraph(f"<b>{escape(str(seller['legal_name']))}</b><br/>{escape(str(seller['registered_address']))}<br/>GSTIN: {escape(str(seller['gstin']))}<br/>{escape(str(seller['seller_state']))} ({escape(str(seller['state_code']))})", small), Paragraph(f"<b>{doc_label}</b><br/>{escape(str(document['number']))}<br/>{document['issued_at'].strftime('%d %b %Y')}<br/>Order: {escape(str(document['order_number']))}", title)],
    ], colWidths=[100 * mm, 60 * mm], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])) )
    buyer_lines = [escape(str(document["buyer"].get(key) or "")) for key in ["name", "address", "city", "state_region", "postal_code", "country", "email", "phone"]]
    buyer_lines.extend([f"Place of supply: {escape(str(document.get('place_of_supply') or document['buyer'].get('state_region') or ''))}", f"Reverse charge: {escape(str(document.get('reverse_charge', 'No')))}"])
    story.extend([Spacer(1, 8 * mm), Paragraph("<b>Bill to</b>", styles["Heading3"]), Paragraph("<br/>".join(buyer_lines), small), Spacer(1, 7 * mm)])
    rows = [["Description", "HSN", "Qty", "GST", "Taxable", "Total"]]
    for item in document["items"]:
        item_taxable = item.get("taxable_value")
        if item_taxable is None:
            item_taxable, _, _, _ = _tax_parts(int(item["line_total"]), float(document["gst_rate"]), bool(document.get("cgst")))
        rows.append([Paragraph(f"{escape(str(item['title']))}<br/><font size=7>{escape(str(item.get('size','')))} · {escape(str(item.get('color','')))}</font>", small), escape(str(document["hsn_code"])), str(item["quantity"]), f"{float(document['gst_rate']):g}%", f"INR {item_taxable:,}", f"INR {item['line_total']:,}"])
    table = Table(rows, colWidths=[68 * mm, 22 * mm, 12 * mm, 16 * mm, 24 * mm, 26 * mm], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#261C19")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D6C7B2")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (2, 1), (-1, -1), "RIGHT"), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([table, Spacer(1, 6 * mm)])
    totals = [["Product subtotal", f"INR {document['subtotal']:,}"], ["Shipping", f"INR {document['shipping_amount']:,}"], ["Taxable value", f"INR {document['taxable_value']:,}"]]
    if document.get("cgst"): totals += [[f"CGST ({float(document['gst_rate']) / 2:g}%)", f"INR {document['cgst']:,}"], [f"SGST ({float(document['gst_rate']) / 2:g}%)", f"INR {document['sgst']:,}"]]
    if document.get("igst"): totals += [[f"IGST ({float(document['gst_rate']):g}%)", f"INR {document['igst']:,}"]]
    totals.append(["Total", f"INR {document['total']:,}"])
    totals_table = Table(totals, colWidths=[55 * mm, 35 * mm], hAlign="RIGHT", style=TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("LINEABOVE", (0, -1), (-1, -1), .75, colors.HexColor("#261C19")), ("FONTSIZE", (0, 0), (-1, -1), 8), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.extend([totals_table, Spacer(1, 12 * mm), Paragraph(f"Authorised signatory: {escape(str(seller['authorised_signatory']))}", right), Paragraph(f"Support: {escape(str(seller['support_email']))} · {escape(str(seller['support_phone']))}", small), Paragraph("Computer-generated document. Prices are GST-inclusive.", small)])
    pdf.build(story)
    return output.getvalue()