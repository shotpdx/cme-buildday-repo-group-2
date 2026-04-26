"""Approve endpoint — flips status to 'approved' and returns 204."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import build_app
from persistence import FakeStore


class FakeOrchestrator:
    def render(self, agg, *, size, quality, personalize=True):
        from lakefoundry.creative.orchestrator import CreativeOutput

        return CreativeOutput(
            brief={
                "theme": "t",
                "mood": "m",
                "visual_elements": ["a"],
                "subject_description": "s",
                "copy_direction": {"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            },
            image_path=Path(f"/tmp/{size}.png"),
            copy={"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            image_cache_hit=True,
            latency_s=0.01,
        )


def test_approve_sets_status():
    store = FakeStore()
    app = build_app(
        orchestrator=FakeOrchestrator(),
        build_aggregate=lambda f: {"primary_segment": "Sports Enthusiast"},
        store=store,
    )
    client = TestClient(app)

    cid = client.post("/campaigns", json={"segment_filter": {}}).json()["campaign_id"]
    assert store.get(cid)["status"] == "running"

    r = client.post(f"/campaigns/{cid}/approve")
    assert r.status_code == 204
    assert r.content == b""
    assert store.get(cid)["status"] == "approved"


def test_approve_unknown_campaign_returns_404():
    app = build_app(
        orchestrator=FakeOrchestrator(),
        build_aggregate=lambda f: {},
        store=FakeStore(),
    )
    client = TestClient(app)
    r = client.post("/campaigns/does-not-exist/approve")
    assert r.status_code == 404
