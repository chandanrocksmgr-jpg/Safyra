from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from lib.db import db
from lib.security import require_admin
from models.homepage import HomepageSettings, HomepageUpdate


router = APIRouter(prefix="/homepage", tags=["homepage"])


async def _get_or_create() -> HomepageSettings:
    document = await db.site_content.find_one({"id": "homepage"})
    if document:
        document.pop("_id", None)
        return HomepageSettings(**document)
    settings = HomepageSettings()
    await db.site_content.insert_one(settings.model_dump())
    return settings


@router.get("", response_model=HomepageSettings)
async def get_homepage():
    return await _get_or_create()


@router.put("", response_model=HomepageSettings)
async def update_homepage(input: HomepageUpdate, _: dict = Depends(require_admin)):
    settings = HomepageSettings(**input.model_dump(), updated_at=datetime.now(timezone.utc))
    await db.site_content.replace_one({"id": "homepage"}, settings.model_dump(), upsert=True)
    return settings