"""Persistence-layer tests for Campaign Studio.

These use ``FakeStore`` (the in-memory ``Store`` implementation) to verify
that ``app.py`` routes go through the store protocol for all durable state.
Running against real Postgres is covered by manual Lakebase smoke tests.
"""
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
                "visual_elements": ["a", "b"],
                "subject_description": "s",
                "copy_direction": {"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            },
            image_path=Path(f"/tmp/{size}.png"),
            copy={"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            image_cache_hit=True,
            latency_s=0.01,
        )


def test_campaign_is_persisted_to_lakebase():
    """After the SSE stream completes, the store row has all 4 format assets."""
    store = FakeStore()
    app = build_app(
        orchestrator=FakeOrchestrator(),
        build_aggregate=lambda f: {"primary_segment": "Sports Enthusiast"},
        store=store,
    )
    client = TestClient(app)

    r = client.post(
        "/campaigns",
        json={"segment_filter": {"persona": "Sports Fan"}},
    )
    cid = r.json()["campaign_id"]

    # Immediately after create, the row exists with running status + empty assets.
    initial = store.get(cid)
    assert initial is not None
    assert initial["status"] == "running"
    assert initial["assets"] == {}
    assert initial["filter"] == {"persona": "Sports Fan"}

    # Drain the SSE stream — this triggers the fan-out that writes 4 assets.
    with client.stream("GET", f"/campaigns/{cid}/events") as stream:
        for line in stream.iter_lines():
            if "event: done" in line:
                break

    final = store.get(cid)
    assert final is not None
    assert final["status"] == "complete"
    assert set(final["assets"].keys()) == {
        "social_square",
        "vertical_story",
        "display_banner",
        "email_header",
    }
    for asset in final["assets"].values():
        assert "image_path" in asset
        assert "copy" in asset
        assert "latency_s" in asset
