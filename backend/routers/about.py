"""Editable brand story / founder page. Public read, Super Admin write."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lib.db import db
from lib.security import require_super_admin
from models.about import AboutContent

router = APIRouter(tags=["about"])

DEFAULT_CONTENT = {
    "eyebrow": "The SAFYRA house",
    "title": "Lucknowi Chikankari,",
    "title_emphasis": "made to be kept.",
    "intro": "SAFYRA is a small Lucknow atelier working with Chikankari artisans on pieces made slowly, in limited numbers, and finished by hand.",
    "hero_image_url": "",
    "story_sections": [
        {"heading": "Where each piece begins", "body": "Every SAFYRA piece starts as a length of fabric chosen for how it holds Chikankari — pure Kota Doria, mulmul, chanderi and silks. The block is printed, then handed to the artisan who embroiders it stitch by stitch.", "image_url": ""},
        {"heading": "The hands behind the thread", "body": "Our artisans work in and around Lucknow, many of them continuing work learnt from their mothers and grandmothers. Each order is made in small runs so the embroidery is never rushed.", "image_url": ""},
        {"heading": "Finished, checked, then sent", "body": "After washing and finishing, every piece is checked for the work described on its product page. What we cannot confirm, we do not claim.", "image_url": ""},
    ],
    "values_title": "What we hold to",
    "values": [
        {"title": "Handwork first", "body": "Chikankari, Mukaish and Badla done by hand, documented piece by piece."},
        {"title": "Honest description", "body": "Fabric, work, lining and transparency stated plainly, never exaggerated."},
        {"title": "Made in small numbers", "body": "Limited runs rather than mass production, so each piece keeps its character."},
        {"title": "Personal service", "body": "Direct help with size, customisation and care, before and after you order."},
    ],
    "founder": {
        "name": "Afira",
        "role": "Founder, SAFYRA CHIKANKARI",
        "quote": "I wanted Chikankari that felt like heirloom clothing again — not something made to be worn twice.",
        "body": "SAFYRA began with a small group of artisans and a simple idea: describe the work truthfully, pay for the hours it takes, and make pieces worth keeping. Every collection still passes through my hands before it reaches you.",
        "image_url": "",
    },
    "cta_label": "Talk to SAFYRA",
    "cta_message": "Hello SAFYRA, I would like to know more about your craft and collections.",
}


async def _current() -> dict:
    stored = await db.site_content.find_one({"id": "about"})
    return {**DEFAULT_CONTENT, **{key: value for key, value in (stored or {}).items() if key in DEFAULT_CONTENT}}


@router.get("/about", response_model=AboutContent)
async def get_about():
    return AboutContent(**await _current())


@router.put("/about", response_model=AboutContent)
async def update_about(input: AboutContent, _: dict = Depends(require_super_admin)):
    document = input.model_dump()
    await db.site_content.update_one(
        {"id": "about"},
        {"$set": {**document, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"id": "about"}},
        upsert=True,
    )
    return AboutContent(**document)
