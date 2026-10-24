from pydantic import BaseModel, Field


class InformationSection(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=2000)


class InformationFaq(BaseModel):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=2000)


class InformationContent(BaseModel):
    eyebrow: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    title_emphasis: str = Field(default="", max_length=120)
    intro: str = Field(min_length=1, max_length=600)
    sections: list[InformationSection] = Field(default_factory=list, max_length=12)
    faq_title: str = Field(min_length=1, max_length=120)
    faqs: list[InformationFaq] = Field(default_factory=list, max_length=20)
    help_label: str = Field(min_length=1, max_length=80)
    help_message: str = Field(min_length=1, max_length=400)
