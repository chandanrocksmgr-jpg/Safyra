from datetime import datetime, timezone
from typing import Optional
import uuid

from pydantic import BaseModel, Field, ConfigDict


class ProductFields(BaseModel):
    title: str
    slug: str
    category: str
    collection: str
    fabric: str
    craft: str
    price: int
    mrp: Optional[int] = None
    stock: int = 0
    stock_by_size: dict[str, int] = Field(default_factory=dict)
    sizes: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    image_url: str
    image_urls: list[str] = Field(default_factory=list)
    description: str
    fit: str
    measurements: str
    transparency: str
    lining: str
    care: str
    dispatch_days: str
    availability: str = "Made to order"
    tags: list[str] = Field(default_factory=list)
    featured: bool = False
    best_seller: bool = False
    new_arrival: bool = False


class ProductCreate(ProductFields):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None
    collection: Optional[str] = None
    fabric: Optional[str] = None
    craft: Optional[str] = None
    price: Optional[int] = None
    mrp: Optional[int] = None
    stock: Optional[int] = None
    stock_by_size: Optional[dict[str, int]] = None
    sizes: Optional[list[str]] = None
    colors: Optional[list[str]] = None
    image_url: Optional[str] = None
    image_urls: Optional[list[str]] = None
    description: Optional[str] = None
    fit: Optional[str] = None
    measurements: Optional[str] = None
    transparency: Optional[str] = None
    lining: Optional[str] = None
    care: Optional[str] = None
    dispatch_days: Optional[str] = None
    availability: Optional[str] = None
    tags: Optional[list[str]] = None
    featured: Optional[bool] = None
    best_seller: Optional[bool] = None
    new_arrival: Optional[bool] = None


class Product(ProductFields):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


DEFAULT_PRODUCTS: list[Product] = [
    Product(
        title="Luxury Nazakat Collection",
        slug="luxury-nazakat-collection",
        category="Anarkali Sets",
        collection="Safyra Luxury",
        fabric="Pure Viscose",
        craft="Resham silk Chikankari with Mukaish & Badla",
        price=3850,
        mrp=8400,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "XXL", "XXXL"],
        colors=["Blood red", "Forest green"],
        image_url="https://safyra.co/cdn/shop/files/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg?v=1767270653&width=1200",
        image_urls=["https://safyra.co/cdn/shop/files/BF92BEEC-84EB-497C-9B69-2948C142F272.jpg?v=1767270653&width=1200", "https://safyra.co/cdn/shop/files/B774FE4A-8E49-49F8-9DB7-3B1A69457A93.jpg?v=1767270653&width=1200"],
        description="A quiet celebration of pure viscose, fluid drape and delicate handcrafted Resham silk Chikankari. The coordinated set is finished with a soft shimmer of Mukaish and Badla work.",
        fit="Fluid, easy A-line silhouette",
        measurements="Model wears M; length and fit vary by selected size. Ask our Lucknow stylist for a custom fit conversation.",
        transparency="Lightweight textile with a soft, graceful fall",
        lining="Please confirm lining and set composition with the stylist before ordering",
        care="Dry clean only",
        dispatch_days="25–29 days",
        availability="Made to order",
        tags=["Luxury", "Mukaish", "Badla"],
        featured=True,
        best_seller=True,
    ),
    Product(
        title="Aira Pure Kota Doria Angrakha",
        slug="aira-pure-kota-doria-angrakha",
        category="Angrakha Suits",
        collection="Everyday Edit",
        fabric="Pure Kota Doria",
        craft="Hand-embroidered Chikankari",
        price=3850,
        mrp=4500,
        stock=0,
        stock_by_size={},
        sizes=["XS", "S", "M", "L", "XL", "2XL", "3XL"],
        colors=["Blush petal", "Serene Sky", "Vanilla", "Midnight bloom", "Buttercup yellow"],
        image_url="https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=1200",
        image_urls=["https://safyra.co/cdn/shop/files/rn-image_picker_lib_temp_b45b8222-b248-4367-890e-33fce779156b.png?v=1768253915&width=1200", "https://safyra.co/cdn/shop/files/IMG_3973.jpg?v=1772064171&width=1200"],
        description="Pure Kota Doria meets the charm of a classic Angrakha silhouette. Lightweight, breathable and finished with delicate hand-embroidered Chikankari for effortless grace.",
        fit="A-line, flowy Angrakha",
        measurements="Approx. 48 inch length; model wears M and is 5'5\" tall",
        transparency="Airy Kota Doria; a complimentary matching inner is included",
        lining="1 complementary matching inner included",
        care="Dry clean only",
        dispatch_days="12–15 business days",
        availability="Made to order",
        tags=["Kota Doria", "Angrakha"],
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
        price=3499,
        mrp=3850,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "XXL", "XXXL"],
        colors=["Vanilla", "Peach blossom", "Aster blue", "Lilac mist", "Blush petal"],
        image_url="https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1200",
        image_urls=["https://safyra.co/cdn/shop/files/rn-image_picker_lib_temp_5cea29bd-732e-4335-ba9f-0085b5624372.jpg?v=1772064200&width=1200", "https://safyra.co/cdn/shop/files/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png?v=1780244603&width=1200"],
        description="An airy Kota Doria Anarkali adorned with handcrafted French knot stitches and enchanting rose and floral motifs for a delicate, three-dimensional texture.",
        fit="Flowy Anarkali with a regal drape",
        measurements="Approx. 46–48 inch length; model wears M and is 5'5\" tall",
        transparency="Light and breathable; the weave has an airy drape",
        lining="Choose a set with complimentary inner, pants or dupatta",
        care="Dry clean only",
        dispatch_days="12–15 business days",
        availability="Made to order",
        tags=["Kota Doria", "French Knot"],
        featured=True,
        new_arrival=True,
    ),
    Product(
        title="Sang-e-Mar-Mar — Rose Edition",
        slug="sang-e-mar-mar-rose-edition",
        category="Straight Kurtis",
        collection="Safyra Luxury",
        fabric="Natural textile blend",
        craft="Handcrafted Chikankari",
        price=6650,
        mrp=7600,
        stock=0,
        stock_by_size={},
        sizes=[],
        colors=["Rose"],
        image_url="https://safyra.co/cdn/shop/files/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg?v=1772205935&width=1200",
        image_urls=["https://safyra.co/cdn/shop/files/preview_images/60cd79dc58734a6597c9712ff4d66366.thumbnail.0000000000.jpg?v=1766183317&width=1200", "https://safyra.co/cdn/shop/files/136112B1-2A2D-4DF5-A6A7-E890FF9B97FF.jpg?v=1772205935&width=1200"],
        description="A limited rose edition from SAFYRA’s luxury edit. Connect with the team to enquire about the next made-to-order window.",
        fit="Please enquire for fit and measurements",
        measurements="Please enquire for current size availability",
        transparency="Please enquire for fabric and lining details",
        lining="Please enquire before ordering",
        care="Dry clean only",
        dispatch_days="Please enquire",
        availability="Currently unavailable",
        tags=["Rose Edition", "Luxury"],
        featured=True,
    ),
    Product(
        title="Mehar Handcrafted Muslin Kurti",
        slug="mehar-handcrafted-muslin-kurti",
        category="Straight Kurtis",
        collection="Everyday Edit",
        fabric="Pure Muslin",
        craft="Resham threadwork Chikankari",
        price=2999,
        mrp=3600,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "2XL"],
        colors=["Ivory", "Sage green"],
        image_url="https://images.unsplash.com/photo-1667665970124-2273c6ef3489?crop=entropy&cs=srgb&fm=jpg&q=85",
        image_urls=["https://images.unsplash.com/photo-1667665970124-2273c6ef3489?crop=entropy&cs=srgb&fm=jpg&q=85"],
        description="A considered everyday layer in soft muslin, designed to let the handwork do the talking.",
        fit="Relaxed straight fit",
        measurements="Select your size for the available size range",
        transparency="Soft, breathable muslin with a light drape",
        lining="Please confirm lining with the stylist",
        care="Gentle hand wash or dry clean",
        dispatch_days="7–10 business days",
        availability="Made to order",
        tags=["Muslin", "Everyday"],
        best_seller=True,
    ),
    Product(
        title="Noor Mul Chanderi Kurti Set",
        slug="noor-mul-chanderi-kurti-set",
        category="Kurti Sets",
        collection="Everyday Edit",
        fabric="Mul Chanderi",
        craft="Handcrafted Chikankari",
        price=4299,
        mrp=5200,
        stock=0,
        stock_by_size={},
        sizes=["S", "M", "L", "XL", "2XL", "3XL"],
        colors=["Powder blue", "Mint", "Ivory"],
        image_url="https://images.pexels.com/photos/16324981/pexels-photo-16324981.jpeg?auto=compress&cs=tinysrgb&w=1200",
        image_urls=["https://images.pexels.com/photos/16324981/pexels-photo-16324981.jpeg?auto=compress&cs=tinysrgb&w=1200"],
        description="A breathable Mul Chanderi set with a quiet sheen and handcrafted detail, made for generous, graceful movement.",
        fit="Easy straight kurti set",
        measurements="Select your size for the available size range",
        transparency="Lightweight Chanderi; opacity varies by colour",
        lining="Please confirm lining and set composition with the stylist",
        care="Dry clean only",
        dispatch_days="12–15 business days",
        availability="Made to order",
        tags=["Chanderi", "Kurti Set"],
        new_arrival=True,
    ),
]