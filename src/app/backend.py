from __future__ import annotations

import os
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from contextlib import closing
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from databricks.sdk.core import Config

try:
    from databricks import sql
except ImportError:  # pragma: no cover - exercised only when connector is unavailable
    sql = None

try:
    from app.models import (
        ActionDecision,
        ActionRecommendation,
        ActionRisk,
        ActivationRecord,
        ActivationResult,
        HighRiskCustomer,
        InvestigationResult,
        NbaActionCandidate,
        PolicyConfig,
        PolicyDecision,
        PolicyPatch,
        SegmentSummary,
        SignalIncident,
        SignalListItem,
        SignalSeverity,
        SignalStatus,
        SupervisorToolCall,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct local execution
    from models import (
        ActionDecision,
        ActionRecommendation,
        ActionRisk,
        ActivationRecord,
        ActivationResult,
        HighRiskCustomer,
        InvestigationResult,
        NbaActionCandidate,
        PolicyConfig,
        PolicyDecision,
        PolicyPatch,
        SegmentSummary,
        SignalIncident,
        SignalListItem,
        SignalSeverity,
        SignalStatus,
        SupervisorToolCall,
    )

DEFAULT_CATALOG = "cme_outcomes_uswest"
DEFAULT_SCHEMA = "media_demo"
DEFAULT_SUPERVISOR_ENDPOINT = "mas-c4ed84f2-endpoint"
DEFAULT_CONTENT_ACTION = (
    "Deploy a multi-channel re-engagement campaign with personalized content recommendations"
)


class Backend:
    def get_high_risk_customers(self) -> list[HighRiskCustomer]:
        raise NotImplementedError

    def get_segment_summary(self) -> SegmentSummary:
        raise NotImplementedError

    def get_recommendations(self) -> list[ActionRecommendation]:
        raise NotImplementedError

    def list_signals(self) -> list[SignalListItem]:
        raise NotImplementedError

    def get_signal(self, signal_id: str) -> SignalIncident:
        raise NotImplementedError

    def get_policy(self) -> PolicyConfig:
        raise NotImplementedError

    def update_policy(self, patch: PolicyPatch) -> PolicyConfig:
        raise NotImplementedError

    def simulate_activation(self, signal_id: str, policy: PolicyConfig | None = None) -> ActivationResult:
        raise NotImplementedError


class RealBackend(Backend):
    def __init__(self) -> None:
        self.catalog = os.getenv("DATABRICKS_CATALOG", DEFAULT_CATALOG)
        self.schema = os.getenv("DATABRICKS_SCHEMA", DEFAULT_SCHEMA)
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID environment variable is required")
        self._config = Config()
        self._policy = PolicyConfig()
        self._activation_log: list[ActivationRecord] = []

    def _get_connection(self):
        if sql is None:
            raise ImportError("databricks-sql-connector is required for RealBackend")
        return sql.connect(
            server_hostname=self._config.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            credentials_provider=lambda: self._config.authenticate,
        )

    def _execute(self, query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
        with closing(self._get_connection()) as connection, closing(connection.cursor()) as cursor:
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
        return columns, rows

    def _qualified(self, table_name: str) -> str:
        return f"`{self.catalog}`.`{self.schema}`.`{table_name}`"

    def get_high_risk_customers(self) -> list[HighRiskCustomer]:
        query = f"""
        SELECT
            c.canonical_id,
            c.email,
            c.first_name,
            c.last_name,
            c.persona,
            p.churn_risk_score,
            p.churn_risk_category,
            p.days_since_last_engagement,
            c.total_watch_seconds,
            c.unique_content_viewed,
            c.customer_tenure_days,
            c.has_subscription,
            c.current_subscription_tier,
            g.top_genre_1,
            c.is_multi_platform
        FROM {self._qualified('gold_media_customer_360')} AS c
        INNER JOIN {self._qualified('gold_media_churn_predictions')} AS p
            ON c.canonical_id = p.canonical_id
        LEFT JOIN {self._qualified('gold_media_top_genres_per_user')} AS g
            ON c.canonical_id = g.canonical_id
        WHERE (
            c.customer_tenure_days >= 180
            AND p.churn_risk_score >= 0.65
        ) OR (
            p.churn_risk_category = 'High'
            AND p.days_since_last_engagement > 30
        )
        ORDER BY p.churn_risk_score DESC, p.days_since_last_engagement DESC
        LIMIT 500
        """
        columns, rows = self._execute(query)
        return [HighRiskCustomer.model_validate(dict(zip(columns, row, strict=False))) for row in rows]

    def get_segment_summary(self) -> SegmentSummary:
        return summarize_high_risk_segment(self.get_high_risk_customers())

    def get_recommendations(self) -> list[ActionRecommendation]:
        return build_recommendations(self.get_segment_summary())

    def list_signals(self) -> list[SignalListItem]:
        signal = self.get_signal("sig-live-churn-risk")
        return [_signal_list_item(signal)]

    def get_signal(self, signal_id: str) -> SignalIncident:
        if signal_id != "sig-live-churn-risk":
            raise KeyError(signal_id)

        summary = self.get_segment_summary()
        affected = max(summary.total_customers, 1)
        actions = self._load_action_candidates(affected)
        top_genre = summary.top_genres[0][0] if summary.top_genres else "priority content"
        return SignalIncident(
            signal_id="sig-live-churn-risk",
            title="High-risk customer segment requires NBA decisioning",
            status=SignalStatus.NEW,
            severity=SignalSeverity.HIGH,
            segment="High-risk media customers",
            detected_at=datetime.now(UTC) - timedelta(minutes=18),
            affected_customers=affected,
            churn_delta=0.18,
            churn_risk_score=0.78,
            content_engagement_score=0.36,
            billing_friction_score=0.42,
            signal_drivers=["Low content engagement", "High billing friction"],
            estimated_value_at_risk=float(affected * 42),
            summary=(
                f"{affected:,} customers meet the current high-risk criteria. "
                f"The dominant genre signal is {top_genre}."
            ),
            root_causes=[
                "Inactivity is elevated for the current high-risk cohort.",
                "Single-title viewing patterns indicate weak content discovery.",
                "Action eligibility is constrained by frequency caps and review policy.",
            ],
            recommended_actions=actions,
            evidence=[
                "gold_media_customer_360 joined to churn predictions",
                "gold_media_nba_action_library active actions ranked by delivery cost",
                "gold_media_nba_orchestration_state available for channel governance",
            ],
        )

    def _load_action_candidates(self, affected_customers: int) -> list[NbaActionCandidate]:
        query = f"""
        SELECT action_id, action_name, action_type, cost_per_delivery
        FROM {self._qualified('gold_media_nba_action_library')}
        WHERE is_active = TRUE
          AND cost_per_delivery IS NOT NULL
        ORDER BY cost_per_delivery ASC
        LIMIT 8
        """
        columns, rows = self._execute(query)
        candidates: list[NbaActionCandidate] = []
        for index, row in enumerate(rows, start=1):
            data = dict(zip(columns, row, strict=False))
            cost = float(data.get("cost_per_delivery") or 0.0)
            action_type = str(data.get("action_type") or "engagement")
            candidates.append(
                NbaActionCandidate(
                    action_id=str(data.get("action_id")),
                    action_name=str(data.get("action_name")),
                    action_type=action_type,
                    channel=_default_channel_for_action_type(action_type),
                    cost_per_delivery=cost,
                    expected_lift=0.04 + (0.01 * min(index, 5)),
                    rank=index,
                    risk_level=ActionRisk.LOW if cost <= 1.0 else ActionRisk.MEDIUM,
                    target_count=max(50, min(affected_customers, 500)),
                    rationale="Active action from the NBA action library, ranked for low-risk simulation.",
                    is_offer="offer" in action_type.lower() or "save" in str(data.get("action_name", "")).lower(),
                )
            )
        return candidates

    def get_policy(self) -> PolicyConfig:
        return self._policy

    def update_policy(self, patch: PolicyPatch) -> PolicyConfig:
        self._policy = _apply_policy_patch(self._policy, patch)
        return self._policy

    def simulate_activation(self, signal_id: str, policy: PolicyConfig | None = None) -> ActivationResult:
        signal = self.get_signal(signal_id)
        return _simulate_activation(signal, policy or self._policy, self._activation_log)


class MockBackend(Backend):
    def __init__(self) -> None:
        self._policy = PolicyConfig()
        self._activation_log: list[ActivationRecord] = []
        self._customers = [
            HighRiskCustomer(
                canonical_id="hh_1001",
                email="alex.chen@example.com",
                first_name="Alex",
                last_name="Chen",
                persona="Binger",
                churn_risk_score=0.82,
                churn_risk_category="High",
                days_since_last_engagement=58,
                total_watch_seconds=3600,
                unique_content_viewed=1,
                customer_tenure_days=420,
                has_subscription=True,
                current_subscription_tier="Premium",
                top_genre_1="Drama",
                is_multi_platform=True,
            ),
            HighRiskCustomer(
                canonical_id="hh_1002",
                email="maria.rivera@example.com",
                first_name="Maria",
                last_name="Rivera",
                persona="Family",
                churn_risk_score=0.74,
                churn_risk_category="High",
                days_since_last_engagement=49,
                total_watch_seconds=4200,
                unique_content_viewed=1,
                customer_tenure_days=315,
                has_subscription=True,
                current_subscription_tier="Standard",
                top_genre_1="Drama",
                is_multi_platform=False,
            ),
            HighRiskCustomer(
                canonical_id="hh_1003",
                email="jamie.patel@example.com",
                first_name="Jamie",
                last_name="Patel",
                persona="Cord Cutter",
                churn_risk_score=0.69,
                churn_risk_category="Medium",
                days_since_last_engagement=37,
                total_watch_seconds=1800,
                unique_content_viewed=1,
                customer_tenure_days=260,
                has_subscription=False,
                current_subscription_tier=None,
                top_genre_1="Comedy",
                is_multi_platform=True,
            ),
            HighRiskCustomer(
                canonical_id="hh_1004",
                email="taylor.lee@example.com",
                first_name="Taylor",
                last_name="Lee",
                persona="Binger",
                churn_risk_score=0.72,
                churn_risk_category="High",
                days_since_last_engagement=54,
                total_watch_seconds=2400,
                unique_content_viewed=1,
                customer_tenure_days=365,
                has_subscription=True,
                current_subscription_tier="Premium",
                top_genre_1="Drama",
                is_multi_platform=True,
            ),
        ]
        self._signals = _mock_signals()

    def get_high_risk_customers(self) -> list[HighRiskCustomer]:
        return list(self._customers)

    def get_segment_summary(self) -> SegmentSummary:
        return summarize_high_risk_segment(self._customers)

    def get_recommendations(self) -> list[ActionRecommendation]:
        return build_recommendations(self.get_segment_summary())

    def list_signals(self) -> list[SignalListItem]:
        return [_signal_list_item(signal) for signal in self._signals.values()]

    def get_signal(self, signal_id: str) -> SignalIncident:
        if signal_id not in self._signals:
            raise KeyError(signal_id)
        return self._signals[signal_id]

    def get_policy(self) -> PolicyConfig:
        return self._policy

    def update_policy(self, patch: PolicyPatch) -> PolicyConfig:
        self._policy = _apply_policy_patch(self._policy, patch)
        return self._policy

    def simulate_activation(self, signal_id: str, policy: PolicyConfig | None = None) -> ActivationResult:
        signal = self.get_signal(signal_id)
        result = _simulate_activation(signal, policy or self._policy, self._activation_log)
        if result.review_required_count:
            self._signals[signal_id] = signal.model_copy(update={"status": SignalStatus.REVIEW_REQUIRED})
        elif result.activated_count:
            self._signals[signal_id] = signal.model_copy(update={"status": SignalStatus.ACTIONED})
        return result


class SupervisorClient:
    def investigate(self, signal: SignalIncident) -> InvestigationResult:
        raise NotImplementedError


class SimulatedSupervisorClient(SupervisorClient):
    def investigate(self, signal: SignalIncident) -> InvestigationResult:
        top_actions = ", ".join(action.action_name for action in signal.recommended_actions[:2])
        return InvestigationResult(
            signal_id=signal.signal_id,
            supervisor_endpoint="simulated",
            summary=(
                f"{signal.segment} are driving the signal. The strongest causes are "
                f"{signal.root_causes[0].lower()} and {signal.root_causes[1].lower()} "
                f"Recommended focus: {top_actions}."
            ),
            tool_calls=[
                SupervisorToolCall(
                    name="nba_signal_analytics",
                    input=f"Investigate {signal.title}",
                    output=f"{signal.affected_customers:,} customers affected; churn delta {signal.churn_delta:.0%}.",
                )
            ],
            recommended_focus=[
                "Confirm frequency-cap eligibility before any simulated activation.",
                "Use the low-cost policy threshold for autopilot decisions.",
                "Route medium-risk offers to review until an action tool returns an activation record.",
            ],
        )


class DatabricksSupervisorClient(SupervisorClient):
    def __init__(self, endpoint_name: str = DEFAULT_SUPERVISOR_ENDPOINT) -> None:
        self.endpoint_name = endpoint_name

    def investigate(self, signal: SignalIncident) -> InvestigationResult:
        prompt = (
            f"Signal: {signal.title}\n"
            f"Segment: {signal.segment}\n"
            f"Affected customers: {signal.affected_customers}\n"
            f"Churn delta: {signal.churn_delta:.0%}\n"
            "Use nba_signal_analytics. Summarize root cause, action themes, and governance considerations."
        )
        config = Config()
        response = requests.post(
            f"{config.host.rstrip('/')}/serving-endpoints/{self.endpoint_name}/invocations",
            headers={**config.authenticate(), "Content-Type": "application/json"},
            json={"input": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
        if not response.ok:
            raise RuntimeError(f"Supervisor endpoint returned HTTP {response.status_code}: {response.text[:500]}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Supervisor endpoint returned a non-JSON body: {response.text[:500]}") from exc

        text = extract_response_text(payload)
        tool_calls = extract_tool_calls(payload)
        return InvestigationResult(
            signal_id=signal.signal_id,
            supervisor_endpoint=self.endpoint_name,
            summary=text,
            tool_calls=tool_calls or [
                SupervisorToolCall(name="CME_NBA_Signal_Decisioning_Supervisor", input=prompt, output=text)
            ],
            recommended_focus=[
                "Apply configurable low-cost and risk thresholds before activation.",
                "Keep all automated deliveries simulation-only until action tools are approved.",
            ],
        )


def summarize_high_risk_segment(customers: Sequence[HighRiskCustomer]) -> SegmentSummary:
    total_customers = len(customers)
    if total_customers == 0:
        return SegmentSummary(
            total_customers=0,
            churn_risk_category_distribution={},
            persona_distribution={},
            average_total_watch_seconds=0.0,
            average_days_since_last_engagement=0.0,
            average_unique_content_viewed=0.0,
            subscription_status_breakdown={True: 0, False: 0},
            top_genres=[],
            unique_content_viewed_one_count=0,
        )

    churn_distribution = Counter(customer.churn_risk_category for customer in customers if customer.churn_risk_category)
    persona_distribution = Counter(customer.persona for customer in customers if customer.persona)
    subscription_breakdown = Counter(customer.has_subscription for customer in customers if customer.has_subscription is not None)
    genre_distribution = Counter(customer.top_genre_1 for customer in customers if customer.top_genre_1)

    total_watch_seconds = _average(customer.total_watch_seconds for customer in customers)
    days_since_last_engagement = _average(customer.days_since_last_engagement for customer in customers)
    unique_content_viewed = _average(customer.unique_content_viewed for customer in customers)
    unique_content_viewed_one_count = sum(1 for customer in customers if customer.unique_content_viewed == 1)

    return SegmentSummary(
        total_customers=total_customers,
        churn_risk_category_distribution=dict(churn_distribution),
        persona_distribution=dict(persona_distribution),
        average_total_watch_seconds=total_watch_seconds,
        average_days_since_last_engagement=days_since_last_engagement,
        average_unique_content_viewed=unique_content_viewed,
        subscription_status_breakdown={True: subscription_breakdown.get(True, 0), False: subscription_breakdown.get(False, 0)},
        top_genres=genre_distribution.most_common(5),
        unique_content_viewed_one_count=unique_content_viewed_one_count,
    )


def build_recommendations(summary: SegmentSummary) -> list[ActionRecommendation]:
    recommendations: list[ActionRecommendation] = []
    total_customers = max(summary.total_customers, 1)
    one_content_ratio = summary.unique_content_viewed_one_count / total_customers
    dominant_genre = summary.top_genres[0][0] if summary.top_genres else None
    high_risk_ratio = summary.churn_risk_category_distribution.get("High", 0) / total_customers

    content_triggered = one_content_ratio > 0.75 and dominant_genre is not None
    recommendations.append(
        ActionRecommendation(
            rule_name="Content Action",
            recommendation=(
                f"Curate a personalized {dominant_genre} content discovery campaign"
                if content_triggered
                else DEFAULT_CONTENT_ACTION
            ),
            is_triggered=content_triggered,
            rationale=(
                f"{one_content_ratio:.0%} of the segment viewed exactly one title and {dominant_genre} is the dominant genre."
                if content_triggered
                else "Content discovery conditions were not met for this segment."
            ),
        )
    )

    win_back_triggered = high_risk_ratio > 0.75 and summary.average_days_since_last_engagement > 45
    recommendations.append(
        ActionRecommendation(
            rule_name="Win-back Action",
            recommendation=(
                "Launch a win-back campaign with exclusive offers"
                if win_back_triggered
                else DEFAULT_CONTENT_ACTION
            ),
            is_triggered=win_back_triggered,
            rationale=(
                f"{high_risk_ratio:.0%} of the segment is High risk and average inactivity is {summary.average_days_since_last_engagement:.1f} days."
                if win_back_triggered
                else "Win-back conditions were not met for this segment."
            ),
        )
    )

    recommendations.append(
        ActionRecommendation(
            rule_name="Engagement Action",
            recommendation=DEFAULT_CONTENT_ACTION,
            is_triggered=not any(rec.is_triggered for rec in recommendations),
            rationale="Fallback action when no specialized rule is triggered.",
        )
    )
    return recommendations


def _var_per_user(action: NbaActionCandidate) -> float:
    if action.risk_level == ActionRisk.HIGH:
        return 53.0
    if action.risk_level == ActionRisk.MEDIUM:
        return 31.0
    return 12.8


def evaluate_actions_for_policy(
    actions: Sequence[NbaActionCandidate], policy: PolicyConfig
) -> list[PolicyDecision]:
    decisions: list[PolicyDecision] = []
    auto_count = 0
    for action in sorted(actions, key=lambda candidate: candidate.rank):
        reasons: list[str] = []
        decision = ActionDecision.AUTO_SIMULATE

        if action.holdout_blocked:
            decisions.append(
                PolicyDecision(
                    action=action,
                    decision=ActionDecision.BLOCKED,
                    reasons=["customer holdout or orchestration state blocks activation"],
                )
            )
            continue

        total_var = action.target_count * _var_per_user(action)
        if total_var > policy.var_threshold:
            decision = ActionDecision.REVIEW_REQUIRED
            reasons.append("total value at risk above threshold")

        if action.risk_level not in policy.auto_risk_levels:
            decision = ActionDecision.REVIEW_REQUIRED
            reasons.append("risk level requires review")

        if policy.require_human_for_offers and action.is_offer:
            decision = ActionDecision.REVIEW_REQUIRED
            reasons.append("offer actions require human review")

        if decision == ActionDecision.AUTO_SIMULATE:
            if auto_count >= policy.max_auto_actions:
                decision = ActionDecision.REVIEW_REQUIRED
                reasons.append("automatic action limit reached")
            else:
                auto_count += 1
                reasons.append("eligible for simulated low-risk activation")

        decisions.append(PolicyDecision(action=action, decision=decision, reasons=reasons))
    return decisions


def extract_response_text(payload: dict[str, Any]) -> str:
    messages = [
        item
        for item in payload.get("output", [])
        if isinstance(item, dict) and item.get("type") == "message"
    ]
    for message in reversed(messages):
        for content in reversed(message.get("content", [])):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = str(content.get("text") or "").strip()
                if text:
                    return text
    return str(payload)


def extract_tool_calls(payload: dict[str, Any]) -> list[SupervisorToolCall]:
    calls: dict[str, SupervisorToolCall] = {}
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            call_id = str(item.get("call_id") or item.get("id") or uuid.uuid4())
            calls[call_id] = SupervisorToolCall(
                name=str(item.get("name") or "unknown_tool"),
                input=str(item.get("arguments") or ""),
                output="",
            )
        if item.get("type") == "function_call_output":
            call_id = str(item.get("call_id") or uuid.uuid4())
            existing = calls.get(call_id)
            if existing:
                calls[call_id] = existing.model_copy(update={"output": str(item.get("output") or "")})
            else:
                calls[call_id] = SupervisorToolCall(
                    name=str(item.get("name") or "unknown_tool"),
                    input="",
                    output=str(item.get("output") or ""),
                )
    return list(calls.values())


def get_backend() -> Backend:
    use_mock = os.getenv("USE_MOCK_BACKEND", "true").lower() == "true"
    return MockBackend() if use_mock else RealBackend()


def get_supervisor_client() -> SupervisorClient:
    if os.getenv("USE_MOCK_SUPERVISOR", "true").lower() == "true":
        return SimulatedSupervisorClient()
    return DatabricksSupervisorClient(os.getenv("NBA_SUPERVISOR_ENDPOINT", DEFAULT_SUPERVISOR_ENDPOINT))


def _simulate_activation(
    signal: SignalIncident,
    policy: PolicyConfig,
    activation_log: list[ActivationRecord],
) -> ActivationResult:
    decisions = evaluate_actions_for_policy(signal.recommended_actions, policy)
    records: list[ActivationRecord] = []
    for decision in decisions:
        if decision.decision != ActionDecision.AUTO_SIMULATE:
            continue
        action = decision.action
        record = ActivationRecord(
            activation_id=f"sim-{uuid.uuid4().hex[:10]}",
            signal_id=signal.signal_id,
            action_id=action.action_id,
            action_name=action.action_name,
            channel=action.channel,
            target_count=action.target_count,
            estimated_cost=round(action.target_count * action.cost_per_delivery, 2),
            simulation_only=True,
            created_at=datetime.now(UTC),
        )
        records.append(record)
        activation_log.append(record)
    review_count = sum(1 for decision in decisions if decision.decision == ActionDecision.REVIEW_REQUIRED)
    return ActivationResult(
        signal_id=signal.signal_id,
        activated_count=len(records),
        review_required_count=review_count,
        records=records,
        decisions=decisions,
    )


def _mock_signals() -> dict[str, SignalIncident]:
    detected = datetime.now(UTC) - timedelta(minutes=24)
    return {
        "sig-premium-inactivity": SignalIncident(
            signal_id="sig-premium-inactivity",
            title="Premium inactivity spike",
            status=SignalStatus.NEW,
            severity=SignalSeverity.HIGH,
            segment="Premium subscribers with single-title viewing",
            detected_at=detected,
            affected_customers=1840,
            churn_delta=0.17,
            churn_risk_score=0.82,
            content_engagement_score=0.24,
            billing_friction_score=0.71,
            signal_drivers=["Low content engagement", "High billing friction"],
            estimated_value_at_risk=196_000,
            summary=(
                "Premium subscribers with narrow content discovery and 45+ days of inactivity "
                "are showing a material churn-risk increase."
            ),
            root_causes=[
                "Premium subscribers have fewer recent sessions than their normal baseline.",
                "Content discovery is narrow, with most of the cohort viewing only one title.",
                "Save-offer actions have higher cost and should stay in review until approved.",
            ],
            recommended_actions=[
                NbaActionCandidate(
                    action_id="act-drama-premiere-push",
                    action_name="Drama Premiere Push",
                    action_type="content",
                    channel="push",
                    cost_per_delivery=0.02,
                    expected_lift=0.041,
                    rank=1,
                    risk_level=ActionRisk.LOW,
                    target_count=900,
                    rationale="Low-cost content nudge aligned to the cohort's dominant genre.",
                ),
                NbaActionCandidate(
                    action_id="act-service-recovery",
                    action_name="Service Recovery Check-in",
                    action_type="service",
                    channel="email",
                    cost_per_delivery=0.08,
                    expected_lift=0.032,
                    rank=2,
                    risk_level=ActionRisk.LOW,
                    target_count=420,
                    rationale="Targets customers with failed playback or support friction signals.",
                ),
                NbaActionCandidate(
                    action_id="act-premium-save-offer",
                    action_name="Premium Save Offer",
                    action_type="retention",
                    channel="in_app",
                    cost_per_delivery=1.25,
                    expected_lift=0.091,
                    rank=3,
                    risk_level=ActionRisk.MEDIUM,
                    target_count=220,
                    rationale="Higher lift, but cost and offer risk require review under guarded autopilot.",
                    is_offer=True,
                ),
                NbaActionCandidate(
                    action_id="act-winback-bonus-month",
                    action_name="Win-back Bonus Month",
                    action_type="retention",
                    channel="email",
                    cost_per_delivery=1.20,
                    expected_lift=0.061,
                    rank=4,
                    risk_level=ActionRisk.MEDIUM,
                    target_count=135,
                    rationale="Incentive for recently lapsed premium households with high value at risk.",
                    is_offer=True,
                ),
                NbaActionCandidate(
                    action_id="act-loyalty-upgrade",
                    action_name="Loyalty Upgrade Offer",
                    action_type="retention",
                    channel="in_app",
                    cost_per_delivery=2.15,
                    expected_lift=0.040,
                    rank=5,
                    risk_level=ActionRisk.HIGH,
                    target_count=96,
                    rationale="High-cost offer reserved for explicit retention-ops approval.",
                    is_offer=True,
                ),
            ],
            evidence=[
                "68% of affected customers watched exactly one title in the last 60 days.",
                "Average days since engagement increased from 31 to 49.",
                "Drama affinity over-indexes 1.8x against the full subscriber base.",
            ],
        ),
        "sig-family-fatigue": SignalIncident(
            signal_id="sig-family-fatigue",
            title="Family plan channel fatigue",
            status=SignalStatus.INVESTIGATING,
            severity=SignalSeverity.MEDIUM,
            segment="Family plans with email fatigue",
            detected_at=detected - timedelta(minutes=17),
            affected_customers=760,
            churn_delta=0.08,
            churn_risk_score=0.68,
            content_engagement_score=0.41,
            billing_friction_score=0.58,
            signal_drivers=["Low content engagement", "Billing support contacts"],
            estimated_value_at_risk=58_000,
            summary="Family-plan customers are eligible for NBA but show email fatigue and frequency-cap pressure.",
            root_causes=[
                "Email engagement fell below segment baseline.",
                "Kids and family content launches remain relevant but channel mix needs rotation.",
            ],
            recommended_actions=[
                NbaActionCandidate(
                    action_id="act-kids-weekend-watch",
                    action_name="Kids Weekend Watch Party",
                    action_type="content",
                    channel="push",
                    cost_per_delivery=0.02,
                    expected_lift=0.029,
                    rank=1,
                    risk_level=ActionRisk.LOW,
                    target_count=500,
                    rationale="Low-cost content cue routed away from email fatigue.",
                ),
                NbaActionCandidate(
                    action_id="act-quiet-period",
                    action_name="Complaint Suppression Window",
                    action_type="do_nothing",
                    channel="holdout",
                    cost_per_delivery=0.01,
                    expected_lift=0.012,
                    rank=2,
                    risk_level=ActionRisk.LOW,
                    target_count=180,
                    rationale="Avoids over-contacting households with recent service complaints.",
                    holdout_blocked=True,
                ),
            ],
            evidence=[
                "Email fatigue score exceeded the guarded-autopilot cap for 24% of the segment.",
                "Push remains available for 66% of eligible households.",
            ],
        ),
        "sig-sports-lapse": SignalIncident(
            signal_id="sig-sports-lapse",
            title="Sports viewers entering lapse window",
            status=SignalStatus.NEW,
            severity=SignalSeverity.MEDIUM,
            segment="Sports-first monthly subscribers",
            detected_at=detected - timedelta(minutes=39),
            affected_customers=1120,
            churn_delta=0.11,
            churn_risk_score=0.74,
            content_engagement_score=0.33,
            billing_friction_score=0.29,
            signal_drivers=["Low content engagement", "Renewal window"],
            estimated_value_at_risk=87_500,
            summary="Sports-first subscribers are approaching renewal after a drop in highlights engagement.",
            root_causes=[
                "Highlights engagement dropped after the latest event cycle.",
                "Customers remain reachable through push and in-app placements.",
            ],
            recommended_actions=[
                NbaActionCandidate(
                    action_id="act-sports-highlights",
                    action_name="Sports Highlights Reel",
                    action_type="content",
                    channel="push",
                    cost_per_delivery=0.03,
                    expected_lift=0.036,
                    rank=1,
                    risk_level=ActionRisk.LOW,
                    target_count=840,
                    rationale="Low-cost re-engagement with timely sports content.",
                )
            ],
            evidence=[
                "Sports affinity segment churn risk is 11 points above baseline.",
                "Recent push opt-in remains high for the segment.",
            ],
        ),
    }


def _signal_list_item(signal: SignalIncident) -> SignalListItem:
    return SignalListItem(
        signal_id=signal.signal_id,
        title=signal.title,
        status=signal.status,
        severity=signal.severity,
        segment=signal.segment,
        detected_at=signal.detected_at,
        affected_customers=signal.affected_customers,
        churn_delta=signal.churn_delta,
        churn_risk_score=signal.churn_risk_score,
        content_engagement_score=signal.content_engagement_score,
        billing_friction_score=signal.billing_friction_score,
        signal_drivers=signal.signal_drivers,
        estimated_value_at_risk=signal.estimated_value_at_risk,
    )


def _apply_policy_patch(policy: PolicyConfig, patch: PolicyPatch) -> PolicyConfig:
    changes = patch.model_dump(exclude_unset=True)
    return policy.model_copy(update=changes)


def _default_channel_for_action_type(action_type: str) -> str:
    normalized = action_type.lower()
    if normalized in {"service", "retention", "win-back", "win_back"}:
        return "email"
    if normalized in {"upsell", "offer"}:
        return "in_app"
    if normalized in {"do_nothing", "holdout"}:
        return "holdout"
    return "push"


def _average(values: Iterable[int | float | None]) -> float:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return 0.0
    return float(sum(numeric_values) / len(numeric_values))
