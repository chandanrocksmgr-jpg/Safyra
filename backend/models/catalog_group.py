from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


GroupType = Literal["category", "collection"]
PublishingStatus = Literal["draft", "active", "archived"]


class CatalogGroupFields(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    group_type: GroupType
    description: str = Field(default="", max_length=1200)
    image_url: str = ""
    status: PublishingStatus = "draft"
    sort_order: int = Field(default=0, ge=0, le=9999)
    show_on_home: bool = True


class CatalogGroupCreate(CatalogGroupFields):
    pass


class CatalogGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    slug: Optional[str] = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    group_type: Optional[GroupType] = None
    description: Optional[str] = Field(default=None, max_length=1200)
    image_url: Optional[str] = None
    status: Optional[PublishingStatus] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=9999)
    show_on_home: Optional[bool] = None


class CatalogGroup(CatalogGroupFields):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))