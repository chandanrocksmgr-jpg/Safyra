from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class HomepageHero(BaseModel):
    eyebrow: str = "Lucknowi Chikankari"
    title: str = "Chikankari,"
    emphasis: str = "made to be remembered."
    body: str = "Handcrafted Chikankari, created by skilled artisans in Lucknow."
    # Up to 5 photos; the homepage cycles through them automatically for a dynamic feel.
    image_urls: list[str] = Field(default_factory=lambda: ["/api/media/shopify/3E9BACB7-48E9-4163-B2BD-AA465BF33240.png"], max_length=5)
    primary_label: str = "Shop new arrivals"
    primary_url: str = "/shop?new=true&sort=newest"
    secondary_label: str = "Shop SAFYRA Luxury"
    secondary_url: str = "/shop?collection=Safyra%20Luxury"


class HomepageStory(BaseModel):
    eyebrow: str = "SAFYRA, Lucknow"
    title: str = "A focused Chikankari wardrobe."
    body: str = "SAFYRA works with Lucknowi Chikankari across Indian silhouettes and verified fabrics. Each product page brings the textile, embroidery description, fit and making information together in one place."
    image_url: str = "/api/media/shopify/IMG_3973.jpg"
    link_label: str = "About the craft"
    link_url: str = "/information#craft"


class HomepageSections(BaseModel):
    show_new_arrivals: bool = True
    show_categories: bool = True
    show_best_sellers: bool = True
    show_luxury: bool = True
    show_collections: bool = True
    show_customer_love: bool = True
    show_story: bool = True
    show_whatsapp: bool = True


class HomepageContent(BaseModel):
    announcement_messages: list[str] = Field(default_factory=lambda: [
        "FREE INDIA SHIPPING FROM ₹1,000",
        "A LITTLE SOMETHING FROM SAFYRA — WITH YOUR FIRST ORDER",
    ])
    hero: HomepageHero = Field(default_factory=HomepageHero)
    sections: HomepageSections = Field(default_factory=HomepageSections)
    new_arrivals_eyebrow: str = "Just added"
    new_arrivals_title: str = "Shop new arrivals"
    categories_eyebrow: str = "Choose a silhouette"
    categories_title: str = "Shop by category"
    best_sellers_eyebrow: str = "Customer favourites"
    best_sellers_title: str = "Bestsellers"
    collections_eyebrow: str = "Current collections"
    collections_title: str = "Shop by collection"
    luxury_eyebrow: str = "SAFYRA Luxury"
    story: HomepageStory = Field(default_factory=HomepageStory)
    whatsapp_eyebrow: str = "Customer care"
    whatsapp_title: str = "Personal help, before you order."


class HomepageUpdate(HomepageContent):
    pass


class HomepageSettings(HomepageContent):
    model_config = ConfigDict(extra="ignore")

    id: str = "homepage"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))