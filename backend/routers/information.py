"""Editable care & information page content. Public read, Super Admin write."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lib.db import db
from lib.security import require_super_admin
from models.information import InformationContent

router = APIRouter(tags=["information"])

DEFAULT_CONTENT = {
    "eyebrow": "SAFYRA care & information",
    "title": "Product, delivery",
    "title_emphasis": "and care guidance.",
    "intro": "Clear product information and personal help when the answer depends on your piece or destination.",
    "sections": [
        {"id": "delivery", "label": "Dispatch & delivery", "title": "Clear timing, piece by piece.", "text": "Making and dispatch information is shown on each product whenever it has been verified. Delivery time can vary by destination. International orders are supported, with shipping options and charges confirmed personally before payment."},
        {"id": "exchange", "label": "Exchange / store credit", "title": "Confirm the right option before ordering.", "text": "Eligibility can depend on the garment, customisation and order status. Ask SAFYRA for the current exchange or store-credit terms for the exact piece you are considering."},
        {"id": "care", "label": "Garment care", "title": "Care for the textile and embroidery.", "text": "Follow the care guidance displayed on the product page. Where care information has not yet been approved, SAFYRA will confirm it before purchase rather than making a general claim."},
        {"id": "craft", "label": "Chikankari", "title": "Lucknowi Chikankari at SAFYRA.", "text": "The current catalogue documents the fabric and embroidery work product by product, including French knot Chikankari, Resham silk Chikankari, Mukaish and Badla where applicable."},
    ],
    "faq_title": "Helpful answers.",
    "faqs": [
        {"question": "How is the embroidery described?", "answer": "Each product page shows the Chikankari or additional work documented for that specific piece. Missing information is omitted until confirmed."},
        {"question": "Do you ship internationally?", "answer": "Yes. Connect with SAFYRA on WhatsApp for current options, timing and pricing for your destination."},
        {"question": "What support is available after ordering?", "answer": "SAFYRA offers personal support before dispatch and after delivery, with direct guidance when you need it."},
    ],
    "help_label": "Ask SAFYRA directly",
    "help_message": "Hello SAFYRA, I need help with product information, shipping or care.",
}


async def _current() -> dict:
    stored = await db.site_content.find_one({"id": "information"})
    return {**DEFAULT_CONTENT, **{key: value for key, value in (stored or {}).items() if key in DEFAULT_CONTENT}}


@router.get("/information", response_model=InformationContent)
async def get_information():
    return InformationContent(**await _current())


@router.put("/information", response_model=InformationContent)
async def update_information(input: InformationContent, _: dict = Depends(require_super_admin)):
    document = input.model_dump()
    await db.site_content.update_one(
        {"id": "information"},
        {"$set": {**document, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"id": "information"}},
        upsert=True,
    )
    return InformationContent(**document)
