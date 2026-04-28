import asyncio
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import build_app
from persistence import FakeStore


class FakeOrchestrator:
    def render(self, agg, *, size, quality, personalize=True):
        from lakefoundry.creative.orchestrator import CreativeOutput
        from pathlib import Path
        return CreativeOutput(
            brief={"theme": "t", "mood": "m", "visual_elements": ["a", "b"],
                   "subject_description": "s", "copy_direction": {"tagline": "tl", "cta": "cta",
                                                                  "subtitle": "sub"}},
            image_path=Path(f"/tmp/{size}.png"),
            copy={"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            image_cache_hit=True,
            latency_s=0.01,
        )


def test_create_campaign_returns_id():
    app = build_app(orchestrator=FakeOrchestrator(),
                    build_aggregate=lambda f: {"primary_segment": "Sports Enthusiast"},
                    store=FakeStore())
    client = TestClient(app)
    r = client.post("/campaigns", json={"segment_filter": {"persona": "Sports Fan"}})
    assert r.status_code == 200
    assert "campaign_id" in r.json()


def test_sse_stream_emits_one_tile_per_format_and_done():
    app = build_app(orchestrator=FakeOrchestrator(),
                    build_aggregate=lambda f: {"primary_segment": "Sports Enthusiast"},
                    store=FakeStore())
    client = TestClient(app)
    r = client.post("/campaigns", json={"segment_filter": {}})
    cid = r.json()["campaign_id"]

    # Drain the SSE stream
    events = []
    with client.stream("GET", f"/campaigns/{cid}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("event: "):
                events.append(line.split(": ", 1)[1])
            if "event: done" in line:
                break

    tile_events = [e for e in events if e == "tile"]
    assert len(tile_events) == 4
    assert "done" in events
