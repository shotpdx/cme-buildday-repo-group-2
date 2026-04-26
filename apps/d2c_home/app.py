"""D2C home-screen reference app. Serves /hero/{canonical_id} and the demo UI."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


class HeroResponse(BaseModel):
    image_path: str
    tagline: str
    cta: str
    subtitle: str
    source: str


# Hardcoded demo canonical IDs covering the five personas. The UI drop-down
# in templates/index.html iterates over these. Task 11 keeps these in-code
# so the demo works without a seeded Lakebase row set; swap for a live query
# ("top 10 canonical_ids per persona with a cached hero image") in production.
DEMO_CANONICAL_IDS: list[dict[str, str]] = [
    {"canonical_id": "demo-sports-01",   "persona": "Sports Fan",                  "label": "Sports Fan · Alex"},
    {"canonical_id": "demo-sports-02",   "persona": "Sports Fan",                  "label": "Sports Fan · Jordan"},
    {"canonical_id": "demo-news-01",     "persona": "News Junkie",                 "label": "News Junkie · Sam"},
    {"canonical_id": "demo-news-02",     "persona": "News Junkie",                 "label": "News Junkie · Priya"},
    {"canonical_id": "demo-binge-01",    "persona": "Entertainment Binge Watcher", "label": "Binge Watcher · Taylor"},
    {"canonical_id": "demo-binge-02",    "persona": "Entertainment Binge Watcher", "label": "Binge Watcher · Morgan"},
    {"canonical_id": "demo-casual-01",   "persona": "Casual Viewer",               "label": "Casual Viewer · Lee"},
    {"canonical_id": "demo-casual-02",   "persona": "Casual Viewer",               "label": "Casual Viewer · Robin"},
    {"canonical_id": "demo-cord-01",     "persona": "Cord Cutter",                 "label": "Cord Cutter · Casey"},
    {"canonical_id": "demo-cord-02",     "persona": "Cord Cutter",                 "label": "Cord Cutter · River"},
]


def build_app(
    *,
    fetch_segment: Callable[[str], dict[str, Any] | None],
    image_client: Any,
    fetch_copy: Callable[[str], dict[str, str]],
) -> FastAPI:
    app = FastAPI(title="D2C Home Screen Demo")

    app_dir = Path(__file__).parent
    static_dir = app_dir / "static"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "persona_defaults").mkdir(exist_ok=True)

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(app_dir / "templates"))

    # Allow-list roots for the /image proxy: cached heroes live under the UC
    # Volume root in production and under the app's static/persona_defaults
    # dir for fallbacks. Resolve both so path-traversal attempts are rejected.
    volume_root_env = os.environ.get("CREATIVES_VOLUME_ROOT")
    allowed_roots: list[Path] = [(static_dir / "persona_defaults").resolve()]
    if volume_root_env:
        allowed_roots.append(Path(volume_root_env).resolve())

    @app.get("/")
    async def index(request: Request) -> Any:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"demo_ids": DEMO_CANONICAL_IDS},
        )

    @app.get("/hero/{canonical_id}", response_model=HeroResponse)
    async def hero(canonical_id: str) -> HeroResponse:
        row = fetch_segment(canonical_id)
        if not row:
            raise HTTPException(status_code=404, detail="Unknown canonical_id")

        from lakefoundry.creative.azure_openai_image import ImageRequest, cache_key

        segment_key = f"{row['primary_segment']}|{row['value_segment']}|{row['top_genre_1']}"
        prompt = _prompt_for_segment_key(segment_key)
        req = ImageRequest(prompt=prompt, size="1024x1792", quality="medium")
        cached = image_client.volume_path_for(cache_key(req))

        if cached.exists():
            copy = fetch_copy(segment_key)
            subtitle = (f"{row['first_name']} — {copy['subtitle']}"
                        if row.get("first_name") else copy["subtitle"]).rstrip(" —")
            return HeroResponse(image_path=str(cached), tagline=copy["tagline"],
                                cta=copy["cta"], subtitle=subtitle, source="cached")

        return _persona_default_response(row["persona"])

    @app.get("/image")
    async def image(path: str) -> FileResponse:
        """Proxy an image from an allow-listed volume root.

        The `/hero/*` API returns absolute filesystem paths (UC Volume mount
        or bundled persona default). The browser can't reach those directly,
        so the UI fetches via /image?path=... and we validate the path lives
        under one of the allow-listed roots before serving it.
        """
        try:
            resolved = Path(path).resolve()
        except (OSError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid path")

        if not any(
            resolved == root or root in resolved.parents for root in allowed_roots
        ):
            raise HTTPException(status_code=403, detail="Path not allowed")

        if not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="Image not found")

        return FileResponse(str(resolved))

    return app


def _prompt_for_segment_key(segment_key: str) -> str:
    """Must match the prompt the batch pipeline used, so cache keys align."""
    primary, value, genre = segment_key.split("|")
    return (
        f"A scene evoking the {genre.lower()} genre, framed for a streaming home-screen hero. "
        f"Scene includes: ... Mood: ... Photographic, cinematic lighting, no text, no watermark, no logos."
    )


def _persona_default_response(persona: str) -> HeroResponse:
    static_root = Path(__file__).parent / "static" / "persona_defaults"
    slug = persona.lower().replace(" ", "_")
    path = static_root / f"{slug}.png"
    defaults = {
        "Sports Fan": ("Tonight's the game.", "Watch", ""),
        "News Junkie": ("Today's top story.", "Watch", ""),
        "Entertainment Binge Watcher": ("Your next binge awaits.", "Watch", ""),
        "Casual Viewer": ("Something good to watch.", "Watch", ""),
        "Cord Cutter": ("Streaming without the bundle.", "Watch", ""),
    }
    tagline, cta, subtitle = defaults.get(persona, ("Watch now.", "Watch", ""))
    return HeroResponse(image_path=str(path), tagline=tagline, cta=cta,
                        subtitle=subtitle, source="persona_default")
