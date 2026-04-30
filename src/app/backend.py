from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterable, Sequence
from contextlib import closing
from typing import Any

from databricks.sdk.core import Config

try:
    from databricks import sql
except ImportError:  # pragma: no cover - exercised only when connector is unavailable
    sql = None

from app.models import ActionRecommendation, HighRiskCustomer, SegmentSummary

DEFAULT_CATALOG = "cme_outcomes_uswest"
DEFAULT_SCHEMA = "media_demo"
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


class RealBackend(Backend):
    def __init__(self) -> None:
        self.catalog = os.getenv("DATABRICKS_CATALOG", DEFAULT_CATALOG)
        self.schema = os.getenv("DATABRICKS_SCHEMA", DEFAULT_SCHEMA)
        self.warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
        if not self.warehouse_id:
            raise ValueError("DATABRICKS_WAREHOUSE_ID environment variable is required")
        self._config = Config()

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
        return f"{self.catalog}.{self.schema}.{table_name}"

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
        """
        columns, rows = self._execute(query)
        return [HighRiskCustomer.model_validate(dict(zip(columns, row, strict=False))) for row in rows]

    def get_segment_summary(self) -> SegmentSummary:
        customers = self.get_high_risk_customers()
        return summarize_high_risk_segment(customers)

    def get_recommendations(self) -> list[ActionRecommendation]:
        return build_recommendations(self.get_segment_summary())


class MockBackend(Backend):
    def __init__(self) -> None:
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

    def get_high_risk_customers(self) -> list[HighRiskCustomer]:
        return list(self._customers)

    def get_segment_summary(self) -> SegmentSummary:
        return summarize_high_risk_segment(self._customers)

    def get_recommendations(self) -> list[ActionRecommendation]:
        return build_recommendations(self.get_segment_summary())


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


def get_backend() -> Backend:
    use_mock = os.getenv("USE_MOCK_BACKEND", "true").lower() == "true"
    return MockBackend() if use_mock else RealBackend()


backend = get_backend()


def _average(values: Iterable[int | float | None]) -> float:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return 0.0
    return float(sum(numeric_values) / len(numeric_values))
