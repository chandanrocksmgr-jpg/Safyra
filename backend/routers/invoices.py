from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lib.db import db
from lib.invoice_service import render_invoice_pdf
from lib.security import get_current_user


router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.get("document_type") == "credit_note" and user.get("role") != "admin":
        raise HTTPException(status_code=404, detail="Invoice not found")
    if user.get("role") != "admin" and invoice.get("customer_id") != user.get("id"):
        raise HTTPException(status_code=404, detail="Invoice not found")
    filename = invoice["number"].replace("/", "-") + ".pdf"
    return Response(render_invoice_pdf(invoice), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})