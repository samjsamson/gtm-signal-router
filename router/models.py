from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class Lead(BaseModel):
    company: str
    website: HttpUrl
    employee_count: int = Field(ge=0)
    industry: str
    contact_name: str
    title: str
    location: str
    persona_note: str
    crm_record_id: Optional[str] = None
    source: str = "Sample dataset"


class Signals(BaseModel):
    scraped: bool = False
    b2b: bool = False
    ai_related: bool = False
    enterprise: bool = False
    sales_motion: Literal["enterprise", "self_serve", "unknown"] = "unknown"
    keywords: list[str] = []
    excerpt: str = ""
    confidence: float = 0.0


class Decision(BaseModel):
    score: int
    account_score: int
    persona_score: int
    route: Literal["Tier 1", "Nurture", "Disqualify", "Human Review"]
    reasons: list[str]
    outreach_angle: str
    llm_summary: Optional[str] = None
