from __future__ import annotations

from datetime import datetime
from enum import Enum

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


class SignalStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    ACTIONED = "actioned"
    REVIEW_REQUIRED = "review_required"


class SignalSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionDecision(str, Enum):
    AUTO_SIMULATE = "auto_simulate"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class PolicyConfig(BaseModel):
    var_threshold: float = Field(default=8000.0, ge=0)
    auto_risk_levels: list[ActionRisk] = Field(default_factory=lambda: [ActionRisk.LOW])
    max_auto_actions: int = Field(default=25, ge=1, le=500)
    require_human_for_offers: bool = False


class PolicyPatch(BaseModel):
    var_threshold: float | None = Field(default=None, ge=0)
    auto_risk_levels: list[ActionRisk] | None = None
    max_auto_actions: int | None = Field(default=None, ge=1, le=500)
    require_human_for_offers: bool | None = None


class NbaActionCandidate(BaseModel):
    action_id: str
    action_name: str
    action_type: str
    channel: str
    cost_per_delivery: float = Field(ge=0)
    expected_lift: float = Field(ge=0)
    rank: int = Field(ge=1)
    risk_level: ActionRisk = ActionRisk.LOW
    target_count: int = Field(ge=0)
    rationale: str
    is_offer: bool = False
    holdout_blocked: bool = False


class PolicyDecision(BaseModel):
    action: NbaActionCandidate
    decision: ActionDecision
    reasons: list[str]


class SignalIncident(BaseModel):
    signal_id: str
    title: str
    status: SignalStatus
    severity: SignalSeverity
    segment: str
    detected_at: datetime
    affected_customers: int = Field(ge=0)
    churn_delta: float
    churn_risk_score: float = Field(default=0.0, ge=0, le=1)
    content_engagement_score: float = Field(default=0.0, ge=0, le=1)
    billing_friction_score: float = Field(default=0.0, ge=0, le=1)
    signal_drivers: list[str] = Field(default_factory=list)
    estimated_value_at_risk: float = Field(ge=0)
    summary: str
    root_causes: list[str]
    recommended_actions: list[NbaActionCandidate]
    evidence: list[str]


class SignalListItem(BaseModel):
    signal_id: str
    title: str
    status: SignalStatus
    severity: SignalSeverity
    segment: str
    detected_at: datetime
    affected_customers: int = Field(ge=0)
    churn_delta: float
    churn_risk_score: float = Field(default=0.0, ge=0, le=1)
    content_engagement_score: float = Field(default=0.0, ge=0, le=1)
    billing_friction_score: float = Field(default=0.0, ge=0, le=1)
    signal_drivers: list[str] = Field(default_factory=list)
    estimated_value_at_risk: float = Field(ge=0)


class SupervisorToolCall(BaseModel):
    name: str
    input: str
    output: str


class InvestigationResult(BaseModel):
    signal_id: str
    supervisor_endpoint: str
    summary: str
    tool_calls: list[SupervisorToolCall]
    recommended_focus: list[str]


class ActivationRecord(BaseModel):
    activation_id: str
    signal_id: str
    action_id: str
    action_name: str
    channel: str
    target_count: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    simulation_only: bool = True
    created_at: datetime


class ActivationResult(BaseModel):
    signal_id: str
    activated_count: int = Field(ge=0)
    review_required_count: int = Field(ge=0)
    records: list[ActivationRecord]
    decisions: list[PolicyDecision]
