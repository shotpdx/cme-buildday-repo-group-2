"""Campaign Studio reference app — SSE fan-out over four creative formats.

``build_app`` is a factory that returns a configured FastAPI app. It takes
an orchestrator with a sync ``render(aggregate, *, size, quality, personalize)``
method, a sync ``build_aggregate(filter_)`` callable that reduces a
``segment_filter`` to a single "virtual segment" aggregate row, and a
``store`` implementing the ``persistence.Store`` protocol for Lakebase-
backed durability.

Module-level ``_QUEUES`` holds transient SSE queues; these don't need to
survive restarts because the final state lives in ``generated_campaigns``.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from persistence import Store

FORMATS: list[dict[str, str]] = [
    {"name": "social_square", "size": "1024x1024"},
    {"name": "vertical_story", "size": "1024x1792"},
    {"name": "display_banner", "size": "1792x1024"},
    {"name": "email_header", "size": "1792x1024"},
]

# Transient SSE fan-out queues — rebuilt on each app boot. Durable state
# lives in the Lakebase ``generated_campaigns`` table via ``Store``.
_QUEUES: dict[str, asyncio.Queue[dict[str, Any]]] = {}


def _format_size(name: str) -> str:
    for fmt in FORMATS:
        if fmt["name"] == name:
            return fmt["size"]
    raise KeyError(name)


class CreateCampaignRequest(BaseModel):
    segment_filter: dict[str, Any]


class CreateCampaignResponse(BaseModel):
    campaign_id: str


def build_app(
    *,
    orchestrator: Any,
    build_aggregate: Callable[[dict[str, Any]], dict[str, Any]],
    store: Store,
) -> FastAPI:
    app = FastAPI(title="Campaign Studio")

    @app.post("/campaigns", response_model=CreateCampaignResponse)
    async def create_campaign(req: CreateCampaignRequest) -> CreateCampaignResponse:
        cid = str(uuid.uuid4())
        store.create(cid, req.segment_filter)
        # Queue is created lazily in the SSE handler so the producer task
        # and the consumer generator share the same event loop. (Under
        # Starlette's TestClient each request owns its own loop, so a
        # ``create_task`` scheduled here would be orphaned when the POST
        # response returns.) See ``_run_campaign``.
        return CreateCampaignResponse(campaign_id=cid)

    @app.get("/campaigns/{cid}/events")
    async def stream_events(cid: str, request: Request) -> StreamingResponse:
        campaign = store.get(cid)
        if campaign is None:
            return StreamingResponse(
                iter(["event: error\ndata: unknown campaign\n\n"]),
                media_type="text/event-stream",
            )

        queue: asyncio.Queue[dict[str, Any]] = _QUEUES.setdefault(cid, asyncio.Queue())

        async def gen() -> AsyncIterator[str]:
            # Start the fan-out inside this request's event loop so it
            # produces events for this generator to drain.
            current = store.get(cid)
            if current is not None and current["status"] == "running" and not current["assets"]:
                asyncio.create_task(
                    _run_campaign(
                        cid,
                        current["filter"],
                        orchestrator,
                        build_aggregate,
                        store,
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

    @app.post("/campaigns/{cid}/regenerate/{format_name}")
    async def regenerate_format(cid: str, format_name: str) -> dict[str, Any]:
        """Re-render a single format at bumped quality and return the new asset.

        The initial fan-out renders at ``quality="low"`` for speed; regenerate
        bumps to ``"medium"`` on the assumption the user wants a better take.
        We skip SSE for this path — a plain JSON response keeps the demo
        wiring simple per the plan's "minor UX caveat" note.
        """
        campaign = store.get(cid)
        if campaign is None:
            raise HTTPException(status_code=404, detail="unknown campaign")
        try:
            size = _format_size(format_name)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"unknown format: {format_name}")

        aggregate = await asyncio.to_thread(build_aggregate, campaign["filter"])
        result = await asyncio.to_thread(
            orchestrator.render,
            aggregate,
            size=size,
            quality="medium",
            personalize=False,
        )
        asset = {
            "image_path": str(result.image_path),
            "copy": result.copy,
            "latency_s": result.latency_s,
        }
        store.update_asset(cid, format_name, asset)
        return asset

    return app


async def _run_campaign(
    cid: str,
    filter_: dict[str, Any],
    orch: Any,
    build_aggregate: Callable[[dict[str, Any]], dict[str, Any]],
    store: Store,
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
            asset = {
                "image_path": str(result.image_path),
                "copy": result.copy,
                "latency_s": result.latency_s,
            }
            store.update_asset(cid, fmt["name"], asset)
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
    store.update_status(cid, "complete")
    await _QUEUES[cid].put({"type": "done", "data": {"campaign_id": cid}})
