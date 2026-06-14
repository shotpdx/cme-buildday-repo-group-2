from __future__ import annotations

from fastapi.testclient import TestClient

from app.app import create_app


def test_api_lists_signal_queue() -> None:
    client = TestClient(create_app())

    response = client.get("/api/signals")

    assert response.status_code == 200
    signals = response.json()
    assert signals[0]["signal_id"] == "sig-premium-inactivity"
    assert signals[0]["status"] == "new"
    assert signals[0]["churn_risk_score"] == 0.82
    assert signals[0]["signal_drivers"] == ["Low content engagement", "High billing friction"]


def test_api_updates_policy_and_applies_it_to_activation() -> None:
    client = TestClient(create_app())

    policy_response = client.patch("/api/policy", json={"low_cost_threshold": 0.05})
    assert policy_response.status_code == 200
    assert policy_response.json()["low_cost_threshold"] == 0.05

    activation_response = client.post("/api/signals/sig-premium-inactivity/activate")

    assert activation_response.status_code == 200
    payload = activation_response.json()
    assert payload["activated_count"] == 1
    assert payload["review_required_count"] == 4


def test_api_investigates_signal_with_supervisor_trace() -> None:
    client = TestClient(create_app())

    response = client.post("/api/signals/sig-premium-inactivity/investigate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal_id"] == "sig-premium-inactivity"
    assert payload["tool_calls"][0]["name"] == "nba_signal_analytics"
