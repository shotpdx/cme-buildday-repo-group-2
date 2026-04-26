"""D2C home-screen reference app. Serves /hero/{canonical_id}."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


class HeroResponse(BaseModel):
    image_path: str
    tagline: str
    cta: str
    subtitle: str
    source: str


def build_app(*, fetch_segment, image_client, fetch_copy) -> FastAPI:
    app = FastAPI(title="D2C Home Screen Demo")

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
