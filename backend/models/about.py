from pydantic import BaseModel, Field


class AboutStorySection(BaseModel):
    heading: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=3000)
    image_url: str = Field(default="", max_length=600)


class AboutValue(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1, max_length=600)


class AboutFounder(BaseModel):
    name: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=120)
    quote: str = Field(default="", max_length=600)
    body: str = Field(default="", max_length=3000)
    image_url: str = Field(default="", max_length=600)


class AboutContent(BaseModel):
    eyebrow: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    title_emphasis: str = Field(default="", max_length=120)
    intro: str = Field(min_length=1, max_length=800)
    hero_image_url: str = Field(default="", max_length=600)
    story_sections: list[AboutStorySection] = Field(default_factory=list, max_length=12)
    values_title: str = Field(default="", max_length=120)
    values: list[AboutValue] = Field(default_factory=list, max_length=12)
    founder: AboutFounder = Field(default_factory=AboutFounder)
    cta_label: str = Field(min_length=1, max_length=80)
    cta_message: str = Field(min_length=1, max_length=400)
