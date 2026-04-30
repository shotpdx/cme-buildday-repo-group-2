from __future__ import annotations

from pydantic import BaseModel, Field


class HighRiskCustomer(BaseModel):
    canonical_id: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    persona: str | None = None
    churn_risk_score: float
    churn_risk_category: str
    days_since_last_engagement: int | None = None
    total_watch_seconds: int | None = None
    unique_content_viewed: int | None = None
    customer_tenure_days: int | None = None
    has_subscription: bool | None = None
    current_subscription_tier: str | None = None
    top_genre_1: str | None = None
    is_multi_platform: bool | None = None


class ActionRecommendation(BaseModel):
    rule_name: str
    recommendation: str
    is_triggered: bool
    rationale: str


class SegmentSummary(BaseModel):
    total_customers: int = Field(ge=0)
    churn_risk_category_distribution: dict[str, int]
    persona_distribution: dict[str, int]
    average_total_watch_seconds: float
    average_days_since_last_engagement: float
    average_unique_content_viewed: float
    subscription_status_breakdown: dict[bool, int]
    top_genres: list[tuple[str, int]]
    unique_content_viewed_one_count: int = Field(ge=0)
