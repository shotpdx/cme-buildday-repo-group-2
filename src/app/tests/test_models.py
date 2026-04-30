from app.models import ActionRecommendation, HighRiskCustomer, SegmentSummary


def test_high_risk_customer_model_accepts_expected_fields() -> None:
    customer = HighRiskCustomer(
        canonical_id="hh_001",
        email="customer@example.com",
        first_name="Jane",
        last_name="Doe",
        persona="Binger",
        churn_risk_score=0.78,
        churn_risk_category="High",
        days_since_last_engagement=52,
        total_watch_seconds=14400,
        unique_content_viewed=1,
        customer_tenure_days=365,
        has_subscription=True,
        current_subscription_tier="Premium",
        top_genre_1="Drama",
        is_multi_platform=True,
    )

    assert customer.canonical_id == "hh_001"
    assert customer.top_genre_1 == "Drama"


def test_segment_summary_model_stores_aggregations() -> None:
    summary = SegmentSummary(
        total_customers=2,
        churn_risk_category_distribution={"High": 1, "Medium": 1},
        persona_distribution={"Binger": 1, "Family": 1},
        average_total_watch_seconds=100.0,
        average_days_since_last_engagement=20.0,
        average_unique_content_viewed=1.5,
        subscription_status_breakdown={True: 1, False: 1},
        top_genres=[("Drama", 1), ("Comedy", 1)],
        unique_content_viewed_one_count=1,
    )

    assert summary.total_customers == 2
    assert summary.subscription_status_breakdown[True] == 1


def test_action_recommendation_model_tracks_trigger_state() -> None:
    recommendation = ActionRecommendation(
        rule_name="Content Action",
        recommendation="Curate a personalized Drama content discovery campaign",
        is_triggered=True,
        rationale="80% of customers viewed only one title and Drama is dominant.",
    )

    assert recommendation.is_triggered is True
    assert "Drama" in recommendation.recommendation
