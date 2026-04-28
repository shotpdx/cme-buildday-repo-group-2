"""Production entrypoint wiring Lakebase + Azure OpenAI into build_app()."""
from __future__ import annotations

import os
from pathlib import Path

from lakefoundry.creative.azure_openai_image import AzureOpenAIImage

from app import build_app


def _lakebase_conn():
    import psycopg

    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode="require",
    )


def fetch_segment(canonical_id: str):
    with _lakebase_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT canonical_id, persona, primary_segment, value_segment,
                   top_genre_1, first_name, churn_risk_category
            FROM gold_media_audience_segments_sync
            WHERE canonical_id = %s
            LIMIT 1
        """, (canonical_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d.name for d in cur.description]
        return dict(zip(cols, row))


# In-memory LRU for segment-key copy (the sell-side design requires caching these).
from functools import lru_cache

@lru_cache(maxsize=1024)
def fetch_copy(segment_key: str) -> dict:
    # For the reference app, read from cme_outcomes_uswest.media_demo.segment_hero_briefs.
    # Stub: real impl queries Lakebase or executes SQL once at startup.
    return {"tagline": "Tonight's your night.", "cta": "Watch now",
            "subtitle": "Your favorites are back."}


image_client = AzureOpenAIImage(
    volume_root=Path(os.environ["CREATIVES_VOLUME_ROOT"]),
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_KEY"],
)

app = build_app(fetch_segment=fetch_segment, image_client=image_client, fetch_copy=fetch_copy)
