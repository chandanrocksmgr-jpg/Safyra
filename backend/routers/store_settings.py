from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import Response

from lib.db import db
from lib.invoice_service import generate_invoice_for_order, get_store_settings_document, missing_invoice_fields, render_invoice_pdf, sample_invoice
from lib.security import require_admin
from models.store_settings import GenerateInvoicesResponse, StoreSettings, StoreSettingsUpdate
from routers.order_emails import send_invoice_ready_email


router = APIRouter(prefix="/store-settings", tags=["store settings"])


def _response(document: dict) -> StoreSettings:
    cleaned = dict(document)
    cleaned.pop("_id", None)
    missing = missing_invoice_fields(cleaned)
    return StoreSettings(**cleaned, invoice_ready=not missing, missing_fields=missing)


@router.get("", response_model=StoreSettings)
async def get_store_settings(_: dict = Depends(require_admin)):
    return _response(await get_store_settings_document())


@router.patch("", response_model=StoreSettings)
async def update_store_settings(input: StoreSettingsUpdate, _: dict = Depends(require_admin)):
    await get_store_settings_document()
    changes = input.model_dump(exclude_unset=True)
    for field in ["gstin", "hsn_code", "invoice_prefix", "credit_note_prefix"]:
        if changes.get(field):
            changes[field] = changes[field].upper()
    changes["updated_at"] = datetime.now(timezone.utc)
    await db.store_settings.update_one({"id": "store"}, {"$set": changes}, upsert=True)
    return _response(await get_store_settings_document())


@router.get("/invoice-preview")
async def invoice_preview(_: dict = Depends(require_admin)):
    document = sample_invoice(await get_store_settings_document())
    return Response(render_invoice_pdf(document, sample=True), media_type="application/pdf", headers={"Content-Disposition": "inline; filename=SAFYRA-SAMPLE-INVOICE.pdf"})


@router.post("/generate-pending-invoices", response_model=GenerateInvoicesResponse)
async def generate_pending_invoices(background_tasks: BackgroundTasks, _: dict = Depends(require_admin)):
    orders = await db.orders.find({"payment_status": "Paid", "invoice_status": {"$ne": "issued"}}).limit(200).to_list(200)
    generated = 0
    for order in orders:
        invoice = await generate_invoice_for_order(order["id"])
        generated += int(bool(invoice))
        if invoice:
            background_tasks.add_task(send_invoice_ready_email, invoice["id"])
    return GenerateInvoicesResponse(generated=generated, blocked=len(orders) - generated)