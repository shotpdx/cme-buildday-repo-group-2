import pytest

from app.backend import MockBackend, build_recommendations
from app.models import ActionRecommendation, SegmentSummary


@pytest.fixture
def base_summary() -> SegmentSummary:
    return SegmentSummary(
        total_customers=100,
        churn_risk_category_distribution={"High": 60, "Medium": 40},
        persona_distribution={"Binger": 55, "Family": 45},
        average_total_watch_seconds=7200.0,
        average_days_since_last_engagement=20.0,
        average_unique_content_viewed=1.2,
        subscription_status_breakdown={True: 70, False: 30},
        top_genres=[("Drama", 50), ("Comedy", 25), ("Action", 15), ("Sci-Fi", 7), ("Kids", 3)],
        unique_content_viewed_one_count=80,
    )


def test_mock_backend_returns_realistic_sample_data() -> None:
    backend = MockBackend()

    customers = backend.get_high_risk_customers()
    summary = backend.get_segment_summary()
    recommendations = backend.get_recommendations()

    assert customers
    assert all(customer.churn_risk_score >= 0 for customer in customers)
    assert summary.total_customers == len(customers)
    assert summary.top_genres
    assert recommendations
    assert all(isinstance(rec, ActionRecommendation) for rec in recommendations)


def test_build_recommendations_triggers_content_rule(base_summary: SegmentSummary) -> None:
    recommendations = build_recommendations(base_summary)

    assert recommendations[0].rule_name == "Content Action"
    assert recommendations[0].is_triggered is True
    assert "Drama" in recommendations[0].recommendation


def test_build_recommendations_triggers_win_back_rule() -> None:
    summary = SegmentSummary(
        total_customers=100,
        churn_risk_category_distribution={"High": 80, "Medium": 20},
        persona_distribution={"Cord Cutter": 100},
        average_total_watch_seconds=1800.0,
        average_days_since_last_engagement=60.0,
        average_unique_content_viewed=2.5,
        subscription_status_breakdown={True: 20, False: 80},
        top_genres=[("Thriller", 40)],
        unique_content_viewed_one_count=10,
    )

    recommendations = build_recommendations(summary)

    assert recommendations[1].rule_name == "Win-back Action"
    assert recommendations[1].is_triggered is True
    assert recommendations[1].recommendation == "Launch a win-back campaign with exclusive offers"


def test_build_recommendations_uses_default_fallback() -> None:
    summary = SegmentSummary(
        total_customers=100,
        churn_risk_category_distribution={"High": 50, "Medium": 50},
        persona_distribution={"Loyalist": 100},
        average_total_watch_seconds=5400.0,
        average_days_since_last_engagement=25.0,
        average_unique_content_viewed=3.0,
        subscription_status_breakdown={True: 95, False: 5},
        top_genres=[("Comedy", 35)],
        unique_content_viewed_one_count=20,
    )

    recommendations = build_recommendations(summary)

    assert recommendations[-1].rule_name == "Engagement Action"
    assert recommendations[-1].is_triggered is True
    assert recommendations[-1].recommendation.startswith("Deploy a multi-channel re-engagement campaign")
