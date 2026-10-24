from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lib.db import db
from lib.invoice_service import render_invoice_pdf
from lib.security import get_current_user, is_super_admin


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    # Junior admins never see invoices: they hold customer and payment data.
    privileged = is_super_admin(user)
    if invoice.get("document_type") == "credit_note" and not privileged:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not privileged and invoice.get("customer_id") != user.get("id"):
        raise HTTPException(status_code=404, detail="Invoice not found")
    filename = invoice["number"].replace("/", "-") + ".pdf"
    return Response(render_invoice_pdf(invoice), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})