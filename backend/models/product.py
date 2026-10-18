from datetime import datetime, timezone
from typing import Literal, Optional
import uuid

from pydantic import BaseModel, Field, ConfigDict, field_validator


IMAGE_URL_HINT = "Image links must start with https:// or be an uploaded image. Links copied from WhatsApp or your device (blob:, file:) only work on your phone."


def _check_image_url(value: Optional[str], allow_empty: bool) -> Optional[str]:
    if value is None or (allow_empty and value == ""):
        return value
    if not value.strip().startswith(("https://", "http://", "/api/media/")):
        raise ValueError(IMAGE_URL_HINT)
    return value.strip()


class ProductImageValidation(BaseModel):
    @field_validator("image_url", check_fields=False)
    @classmethod
    def _primary_image(cls, value: Optional[str]) -> Optional[str]:
        return _check_image_url(value, allow_empty=False)

    @field_validator("size_guide_image", check_fields=False)
    @classmethod
    def _size_guide_image(cls, value: Optional[str]) -> Optional[str]:
        return _check_image_url(value, allow_empty=True)

    @field_validator("image_urls", check_fields=False)
    @classmethod
    def _gallery_images(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        return None if value is None else [_check_image_url(item, allow_empty=False) or "" for item in value]


class ProductSetType(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=100)
    price: int = Field(ge=0)
    mrp: Optional[int] = Field(default=None, ge=0)


class ProductVariantOverride(BaseModel):
    set_type_id: str = Field(min_length=1, max_length=80)
    size: str = Field(default="", max_length=40)
    color: str = Field(default="", max_length=80)
    price: Optional[int] = Field(default=None, ge=0)
    mrp: Optional[int] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
    availability: Optional[str] = Field(default=None, max_length=80)


class ActiveDiscount(BaseModel):
    id: str
    name: str
    discount_type: Literal["percentage", "fixed"]
    value: int


class ProductFields(BaseModel):
    title: str
    slug: str
    category: str
    collection: str
    fabric: str
    craft: str
    hsn_code: str = Field(default="", pattern=r"^$|^\d{8}$")
    price: int
    mrp: Optional[int] = None
    stock: int = 0
    stock_by_size: dict[str, int] = Field(default_factory=dict)
    sizes: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    image_url: str
    image_urls: list[str] = Field(default_factory=list, max_length=40)
    description: str
    fit: str
    measurements: str
    transparency: str
    lining: str
    care: str
    dispatch_days: str
    availability: str = "Made to order"
    customisation: str = ""
    origin: str = ""
    occasion: list[str] = Field(default_factory=list)
    style_keywords: list[str] = Field(default_factory=list)
    size_guide_image: str = ""
    complete_look_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    featured: bool = False
    best_seller: bool = False
    new_arrival: bool = False
    status: Literal["draft", "active", "archived"] = "active"
    set_types: list[ProductSetType] = Field(default_factory=list, max_length=20)
    variant_overrides: list[ProductVariantOverride] = Field(default_factory=list, max_length=500)


class ProductCreate(ProductImageValidation, ProductFields):
    pass


class ProductUpdate(ProductImageValidation):
    title: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None
    collection: Optional[str] = None
    fabric: Optional[str] = None
    craft: Optional[str] = None
    hsn_code: Optional[str] = Field(default=None, pattern=r"^$|^\d{8}$")
    price: Optional[int] = None
    mrp: Optional[int] = None
    stock: Optional[int] = None
    stock_by_size: Optional[dict[str, int]] = None
    sizes: Optional[list[str]] = None
    colors: Optional[list[str]] = None
    image_url: Optional[str] = None
    image_urls: Optional[list[str]] = Field(default=None, max_length=40)
    description: Optional[str] = None
    fit: Optional[str] = None
    measurements: Optional[str] = None
    transparency: Optional[str] = None
    lining: Optional[str] = None
    care: Optional[str] = None
    dispatch_days: Optional[str] = None
    availability: Optional[str] = None
    customisation: Optional[str] = None
    origin: Optional[str] = None
    occasion: Optional[list[str]] = None
    style_keywords: Optional[list[str]] = None
    size_guide_image: Optional[str] = None
    complete_look_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    featured: Optional[bool] = None
    best_seller: Optional[bool] = None
    new_arrival: Optional[bool] = None
    status: Optional[Literal["draft", "active", "archived"]] = None
    set_types: Optional[list[ProductSetType]] = Field(default=None, max_length=20)
    variant_overrides: Optional[list[ProductVariantOverride]] = Field(default=None, max_length=500)


class Product(ProductFields):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active_discount: Optional[ActiveDiscount] = None


DEFAULT_PRODUCTS: list[Product] = [
    Product(
        title="Luxury Nazakat Collection",
        slug="luxury-nazakat-collection",
        category="Anarkali Sets",
        collection="Safyra Luxury",
        fabric="Pure Viscose",
        craft="Resham silk Chikankari with Mukaish & Badla",
        hsn_code="62114922",
        price=3850,
        mrp=8400,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "XXL", "XXXL"],
        colors=["Blood red", "Forest green"],
        image_url="/api/media/shopify/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg",
        image_urls=["/api/media/shopify/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg", "/api/media/shopify/B774FE4A-8E49-49F8-9DB7-3B1A69457A93.jpg"],
        description="A quiet celebration of pure viscose, fluid drape and delicate handcrafted Resham silk Chikankari. The coordinated set is finished with a soft shimmer of Mukaish and Badla work.",
        fit="",
        measurements="",
        transparency="",
        lining="",
        care="",
        dispatch_days="25–29 days",
        availability="Made to order",
        tags=["Luxury", "Mukaish", "Badla"],
        style_keywords=["Anarkali", "Occasionwear"],
        size_guide_image="/api/media/shopify/IMG_3734.jpg",
        featured=True,
    ),
    Product(
        title="Aira Pure Kota Doria Angrakha",
        slug="aira-pure-kota-doria-angrakha",
        category="Angrakha Suits",
        collection="Everyday Edit",
        fabric="Pure Kota Doria",
        craft="Hand-embroidered Chikankari",
        hsn_code="62114922",
        price=3850,
        mrp=4500,
        stock=0,
        stock_by_size={},
        sizes=["XS", "S", "M", "L", "XL", "2XL", "3XL"],
        colors=["Blush petal", "Serene Sky", "Vanilla", "Midnight bloom", "Buttercup yellow"],
        image_url="/api/media/shopify/IMG_3973.jpg",
        image_urls=["/api/media/shopify/rn-image_picker_lib_temp_b45b8222-b248-4367-890e-33fce779156b.png", "/api/media/shopify/IMG_3973.jpg"],
        description="Pure Kota Doria meets the charm of a classic Angrakha silhouette. Lightweight, breathable and finished with delicate hand-embroidered Chikankari for effortless grace.",
        fit="A-line, flowy Angrakha",
        measurements="Approx. 48 inch length; model wears M and is 5'5\" tall",
        transparency="Airy Kota Doria; a complimentary matching inner is included",
        lining="1 complementary matching inner included",
        care="Dry clean only",
        dispatch_days="12–15 business days",
        availability="Made to order",
        customisation="Custom dyeing is available through WhatsApp assistance",
        tags=["Kota Doria", "Angrakha"],
        origin="India",
        style_keywords=["Angrakha", "A-line"],
        size_guide_image="/api/media/shopify/IMG_3734.jpg",
        featured=True,
        new_arrival=True,
    ),
    Product(
        title="Vaaya Pure Kota Doria Anarkali",
        slug="vaaya-pure-kota-doria-anarkali",
        category="Anarkali Sets",
        collection="Vaaya Kota Doria",
        fabric="Pure Kota Doria",
        craft="French knot Chikankari with rose & floral motifs",
        hsn_code="62114922",
        price=3499,
        mrp=3850,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "XXL", "XXXL"],
        colors=["Vanilla", "Peach blossom", "Aster blue", "Lilac mist", "Blush petal"],
        image_url="/api/media/shopify/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png",
        image_urls=["/api/media/shopify/rn-image_picker_lib_temp_5cea29bd-732e-4335-ba9f-0085b5624372.jpg", "/api/media/shopify/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png"],
        description="An airy Kota Doria Anarkali adorned with handcrafted French knot stitches and enchanting rose and floral motifs for a delicate, three-dimensional texture.",
        fit="Flowy Anarkali with a regal drape",
        measurements="Approx. 46–48 inch length; model wears M and is 5'5\" tall",
        transparency="Light and breathable; the weave has an airy drape",
        lining="Choose a set with complimentary inner, pants or dupatta",
        care="Dry clean only",
        dispatch_days="12–15 business days",
        availability="Made to order",
        tags=["Kota Doria", "French Knot"],
        customisation="Custom dyeing is available through WhatsApp assistance",
        origin="India",
        style_keywords=["Anarkali", "Flowy"],
        size_guide_image="/api/media/shopify/IMG_3734.jpg",
        featured=True,
        new_arrival=True,
    ),
    Product(
        title="Sang-e-Mar-Mar — Rose Edition",
        slug="sang-e-mar-mar-rose-edition",
        category="Straight Kurtis",
        collection="Safyra Luxury",
        fabric="",
        craft="",
        hsn_code="62114922",
        price=6650,
        mrp=7600,
        stock=0,
        stock_by_size={},
        sizes=[],
        colors=["Rose"],
        image_url="/api/media/shopify/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg",
        image_urls=["/api/media/shopify/preview_images/60cd79dc58734a6597c9712ff4d66366.thumbnail.0000000000.jpg", "/api/media/shopify/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg"],
        description="",
        fit="",
        measurements="",
        transparency="",
        lining="",
        care="",
        dispatch_days="",
        availability="Currently unavailable",
        tags=["Rose Edition", "Luxury"],
        featured=True,
    ),
]