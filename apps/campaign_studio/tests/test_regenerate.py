"""Regenerate endpoint — bumps one format to ``quality="medium"`` and updates the store."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app import build_app
from persistence import FakeStore


class RecordingOrchestrator:
    """Orchestrator that records calls so we can assert the quality bump."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def render(self, agg, *, size, quality, personalize=True):
        from lakefoundry.creative.orchestrator import CreativeOutput

        self.calls.append({"size": size, "quality": quality, "personalize": personalize})
        return CreativeOutput(
            brief={
                "theme": "t",
                "mood": "m",
                "visual_elements": ["a", "b"],
                "subject_description": "s",
                "copy_direction": {"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            },
            image_path=Path(f"/tmp/regen-{size}-{quality}.png"),
            copy={"tagline": f"regen-{quality}", "cta": "cta", "subtitle": "sub"},
            image_cache_hit=False,
            latency_s=0.02,
        )


def test_regenerate_updates_asset():
    orch = RecordingOrchestrator()
    store = FakeStore()
    app = build_app(
        orchestrator=orch,
        build_aggregate=lambda f: {"primary_segment": "Sports Enthusiast"},
        store=store,
    )
    client = TestClient(app)

    cid = client.post("/campaigns", json={"segment_filter": {}}).json()["campaign_id"]

    # Drain initial fan-out so 4 low-quality assets land in the store first.
    with client.stream("GET", f"/campaigns/{cid}/events") as stream:
        for line in stream.iter_lines():
            if "event: done" in line:
                break

    initial = store.get(cid)["assets"]["social_square"]
    assert initial["copy"]["tagline"] == "regen-low"
    # All 4 initial calls were low-quality.
    assert all(c["quality"] == "low" for c in orch.calls)
    initial_call_count = len(orch.calls)

    # Regenerate just ``social_square`` at bumped quality.
    r = client.post(f"/campaigns/{cid}/regenerate/social_square")
    assert r.status_code == 200
    body = r.json()
    assert body["copy"]["tagline"] == "regen-medium"
    assert "medium" in body["image_path"]
    assert body["latency_s"] == 0.02

    # Store reflects the bumped asset — other 3 untouched.
    updated = store.get(cid)
    assert updated["assets"]["social_square"]["copy"]["tagline"] == "regen-medium"
    assert updated["assets"]["vertical_story"]["copy"]["tagline"] == "regen-low"

    # Exactly one new orchestrator call, and it was quality="medium".
    assert len(orch.calls) == initial_call_count + 1
    assert orch.calls[-1]["quality"] == "medium"
    assert orch.calls[-1]["size"] == "1024x1024"


def test_regenerate_unknown_campaign_returns_404():
    app = build_app(
        orchestrator=RecordingOrchestrator(),
        build_aggregate=lambda f: {},
        store=FakeStore(),
    )
    client = TestClient(app)
    r = client.post("/campaigns/does-not-exist/regenerate/social_square")
    assert r.status_code == 404


def test_regenerate_unknown_format_returns_400():
    orch = RecordingOrchestrator()
    store = FakeStore()
    app = build_app(
        orchestrator=orch,
        build_aggregate=lambda f: {},
        store=store,
    )
    client = TestClient(app)
    cid = client.post("/campaigns", json={"segment_filter": {}}).json()["campaign_id"]
    r = client.post(f"/campaigns/{cid}/regenerate/bogus_format")
    assert r.status_code == 400
