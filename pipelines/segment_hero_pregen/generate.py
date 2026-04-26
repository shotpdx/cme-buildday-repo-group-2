"""Render and cache one hero image per segment key. Run as a Databricks notebook task."""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import AzureOpenAI
from pyspark.sql import SparkSession

from lakefoundry.creative.azure_openai_image import AzureOpenAIImage, ImageRequest, cache_key

SPARK = SparkSession.getActiveSession()
VOLUME_ROOT = Path(os.environ.get("CREATIVES_VOLUME_ROOT",
                                  "/Volumes/cme_outcomes_uswest/media_demo/creatives/heroes"))
VOLUME_ROOT.mkdir(parents=True, exist_ok=True)


def synthesize_brief_for_segment(row: dict) -> dict:
    # For batch, a deterministic template is cheaper and more consistent than Claude per-call.
    return {
        "theme": f"{row['primary_segment']} peak moment",
        "mood": _mood_for(row),
        "visual_elements": _elements_for(row),
        "subject_description": _subject_for(row),
        "copy_direction": {
            "tagline": _tagline_for(row),
            "cta": _cta_for(row),
            "subtitle": "",  # filled live per-customer
        },
    }


def _mood_for(row):
    return {
        "Sports Enthusiast": "Triumphant, adrenaline-charged",
        "News Consumer": "Focused, urgent",
        "Entertainment Seeker": "Warm, escapist",
        "Casual Browser": "Relaxed, unhurried",
        "Digital Native": "Bright, kinetic",
    }.get(row["primary_segment"], "Cinematic")


def _elements_for(row):
    base = {
        "Sports": ["stadium lights", "crowd silhouettes"],
        "News": ["dim newsroom", "monitor glow"],
        "Entertainment": ["cozy couch", "soft evening light"],
        "Drama": ["moody interior", "long shadows"],
        "Comedy": ["bright kitchen", "warm tones"],
        "Documentary": ["natural landscape", "golden hour"],
        "Reality": ["candid party lights", "neon accents"],
        "Kids": ["playful primary colors", "soft plush textures"],
    }.get(row["top_genre_1"], ["cinematic lighting", "rich color"])
    return base + ["photographic"]


def _subject_for(row):
    return f"A scene evoking the {row['top_genre_1'].lower()} genre, framed for a streaming home-screen hero."


def _tagline_for(row):
    return {
        "Premium Engaged": "Tonight's your night.",
        "High Value": "Your shows are waiting.",
        "Conversion Target": "Start watching now.",
        "At Risk": "Come back to what you love.",
        "Churned": "Tonight, we reconnect.",
        "Standard": "Your lineup is ready.",
    }.get(row["value_segment"], "Start watching tonight.")


def _cta_for(row):
    return "Watch now" if row["value_segment"] != "Churned" else "Welcome back"


def render_one(row, image_client):
    brief = synthesize_brief_for_segment(row)
    prompt = (
        f"{brief['subject_description']} Scene includes: {', '.join(brief['visual_elements'])}. "
        f"Mood: {brief['mood']}. Photographic, cinematic lighting, no text, no watermark, no logos."
    )
    req = ImageRequest(prompt=prompt, size="1024x1792", quality="medium")
    t0 = time.time()
    result = image_client.generate(req)
    return {"segment_key": f"{row['primary_segment']}|{row['value_segment']}|{row['top_genre_1']}",
            "cache_hit": result.cache_hit, "latency_s": round(time.time() - t0, 1),
            "path": str(result.path), "brief": brief}


def main():
    keys = SPARK.table("segment_hero_keys").collect()
    image_client = AzureOpenAIImage(
        volume_root=VOLUME_ROOT,
        endpoint="https://lakefoundry-azure-openai.openai.azure.com/",
        api_key=os.environ["AZURE_OPENAI_KEY"],
    )
    # Cap parallelism to avoid rate limits.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(render_one, r.asDict(), image_client) for r in keys]
        summary = [f.result() for f in as_completed(futures)]

    # Persist brief copy for each segment back to Lakebase so the sell-side app can read it.
    for s in summary:
        print(json.dumps(s))

    # Optional: write briefs to a sidecar table
    briefs = [{"segment_key": s["segment_key"], "brief_json": json.dumps(s["brief"])} for s in summary]
    SPARK.createDataFrame(briefs).write.mode("overwrite").saveAsTable(
        "cme_outcomes_uswest.media_demo.segment_hero_briefs"
    )


if __name__ == "__main__":
    main()
