from __future__ import annotations

from app.backend import (
    MockBackend,
    SimulatedSupervisorClient,
    evaluate_actions_for_policy,
    extract_response_text,
)
from app.models import ActionDecision, ActionRisk, PolicyConfig


def test_policy_threshold_controls_automatic_simulation() -> None:
    backend = MockBackend()
    signal = backend.get_signal("sig-premium-inactivity")
    policy = PolicyConfig(low_cost_threshold=0.05, max_auto_actions=10)

    decisions = evaluate_actions_for_policy(signal.recommended_actions, policy)

    by_name = {decision.action.action_name: decision for decision in decisions}
    assert by_name["Drama Premiere Push"].decision == ActionDecision.AUTO_SIMULATE
    assert by_name["Premium Save Offer"].decision == ActionDecision.REVIEW_REQUIRED
    assert "cost above low-cost threshold" in by_name["Premium Save Offer"].reasons


def test_policy_risk_override_blocks_automatic_simulation() -> None:
    backend = MockBackend()
    signal = backend.get_signal("sig-premium-inactivity")
    policy = PolicyConfig(low_cost_threshold=1.00, auto_risk_levels=[ActionRisk.LOW])

    decisions = evaluate_actions_for_policy(signal.recommended_actions, policy)

    risky_decision = next(decision for decision in decisions if decision.action.risk_level == ActionRisk.MEDIUM)
    assert risky_decision.decision == ActionDecision.REVIEW_REQUIRED
    assert "risk level requires review" in risky_decision.reasons


def test_simulated_activation_records_only_auto_eligible_actions() -> None:
    backend = MockBackend()
    policy = PolicyConfig(low_cost_threshold=0.10, max_auto_actions=10)

    result = backend.simulate_activation("sig-premium-inactivity", policy)

    assert result.signal_id == "sig-premium-inactivity"
    assert result.activated_count == 2
    assert result.review_required_count == 3
    assert all(record.simulation_only for record in result.records)
    assert {record.action_name for record in result.records} == {
        "Drama Premiere Push",
        "Service Recovery Check-in",
    }


def test_supervisor_adapter_returns_investigation_trace() -> None:
    backend = MockBackend()
    signal = backend.get_signal("sig-premium-inactivity")
    supervisor = SimulatedSupervisorClient()

    investigation = supervisor.investigate(signal)

    assert investigation.signal_id == signal.signal_id
    assert investigation.supervisor_endpoint == "simulated"
    assert "Premium subscribers" in investigation.summary
    assert investigation.tool_calls[0].name == "nba_signal_analytics"


def test_extract_response_text_uses_final_assistant_message() -> None:
    payload = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "starting"}],
            },
            {
                "type": "function_call_output",
                "output": "{\"rows\": []}",
            },
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "final decision"}],
            },
        ]
    }

    assert extract_response_text(payload) == "final decision"
