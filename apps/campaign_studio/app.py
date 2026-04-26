"""Campaign Studio reference app — SSE fan-out over four creative formats.

``build_app`` is a factory that returns a configured FastAPI app. It takes
an orchestrator with a sync ``render(aggregate, *, size, quality, personalize)``
method and a sync ``build_aggregate(filter_)`` callable that reduces a
``segment_filter`` to a single "virtual segment" aggregate row.

Module-level ``_CAMPAIGNS`` and ``_QUEUES`` registries hold per-campaign
state in-memory for the demo. Task 13 swaps these for Lakebase persistence.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

FORMATS: list[dict[str, str]] = [
    {"name": "social_square", "size": "1024x1024"},
    {"name": "vertical_story", "size": "1024x1792"},
    {"name": "display_banner", "size": "1792x1024"},
    {"name": "email_header", "size": "1792x1024"},
]

# Module-level registries — in-memory for the demo. Task 13 replaces
# ``_CAMPAIGNS`` with Lakebase ``generated_campaigns`` rows.
_CAMPAIGNS: dict[str, dict[str, Any]] = {}
_QUEUES: dict[str, asyncio.Queue[dict[str, Any]]] = {}


class CreateCampaignRequest(BaseModel):
    segment_filter: dict[str, Any]


class CreateCampaignResponse(BaseModel):
    campaign_id: str


def build_app(
    *,
    orchestrator: Any,
    build_aggregate: Callable[[dict[str, Any]], dict[str, Any]],
) -> FastAPI:
    app = FastAPI(title="Campaign Studio")

    @app.post("/campaigns", response_model=CreateCampaignResponse)
    async def create_campaign(req: CreateCampaignRequest) -> CreateCampaignResponse:
        cid = str(uuid.uuid4())
        _CAMPAIGNS[cid] = {
            "filter": req.segment_filter,
            "assets": {},
            "status": "pending",
        }
        # Queue is created lazily in the SSE handler so the producer task
        # and the consumer generator share the same event loop. (Under
        # Starlette's TestClient each request owns its own loop, so a
        # ``create_task`` scheduled here would be orphaned when the POST
        # response returns.) See ``_run_campaign``.
        return CreateCampaignResponse(campaign_id=cid)

    @app.get("/campaigns/{cid}/events")
    async def stream_events(cid: str, request: Request) -> StreamingResponse:
        if cid not in _CAMPAIGNS:
            return StreamingResponse(
                iter(["event: error\ndata: unknown campaign\n\n"]),
                media_type="text/event-stream",
            )

        queue: asyncio.Queue[dict[str, Any]] = _QUEUES.setdefault(cid, asyncio.Queue())

        async def gen() -> AsyncIterator[str]:
            # Start the fan-out inside this request's event loop so it
            # produces events for this generator to drain.
            if _CAMPAIGNS[cid]["status"] == "pending":
                _CAMPAIGNS[cid]["status"] = "running"
                asyncio.create_task(
                    _run_campaign(
                        cid,
                        _CAMPAIGNS[cid]["filter"],
                        orchestrator,
                        build_aggregate,
                    )
                )
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                if event["type"] == "done":
                    return

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


async def _run_campaign(
    cid: str,
    filter_: dict[str, Any],
    orch: Any,
    build_aggregate: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    aggregate = await asyncio.to_thread(build_aggregate, filter_)
    sem = asyncio.Semaphore(4)

    async def one(fmt: dict[str, str]) -> None:
        async with sem:
            result = await asyncio.to_thread(
                orch.render,
                aggregate,
                size=fmt["size"],
                quality="low",
                personalize=False,
            )
            _CAMPAIGNS[cid]["assets"][fmt["name"]] = {
                "image_path": str(result.image_path),
                "copy": result.copy,
                "latency_s": result.latency_s,
            }
            await _QUEUES[cid].put(
                {
                    "type": "tile",
                    "data": {
                        "format": fmt["name"],
                        "image_path": str(result.image_path),
                        "copy": result.copy,
                    },
                }
            )

    await asyncio.gather(*[one(f) for f in FORMATS])
    _CAMPAIGNS[cid]["status"] = "complete"
    await _QUEUES[cid].put({"type": "done", "data": {"campaign_id": cid}})
