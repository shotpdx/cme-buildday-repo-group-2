"""Production entrypoint for campaign studio."""
from __future__ import annotations

import json
import os
from pathlib import Path

from lakefoundry.creative.azure_openai_image import AzureOpenAIImage
from lakefoundry.creative.orchestrator import CreativeOrchestrator

from app import build_app
from persistence import CampaignStore

# Minimal real brief synthesizer for buy-side — re-use the batch template for now.
from sys import path as _sp
_sp.append(str(Path(__file__).resolve().parents[2] / "pipelines" / "segment_hero_pregen"))
from generate import synthesize_brief_for_segment  # noqa: E402


def build_aggregate(filter_: dict) -> dict:
    # Reduces a multi-customer filter to a single aggregate "virtual segment".
    import psycopg
    with psycopg.connect(
        host=os.environ["PGHOST"], dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
        sslmode="require",
    ) as conn, conn.cursor() as cur:
        conds = []
        params = []
        for k, v in filter_.items():
            conds.append(f"{k} = %s")
            params.append(v)
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        cur.execute(f"""
            SELECT mode() WITHIN GROUP (ORDER BY primary_segment) AS primary_segment,
                   mode() WITHIN GROUP (ORDER BY value_segment) AS value_segment,
                   mode() WITHIN GROUP (ORDER BY top_genre_1) AS top_genre_1,
                   mode() WITHIN GROUP (ORDER BY persona) AS persona,
                   COUNT(*) AS customer_count
            FROM gold_media_audience_segments_sync
            {where}
        """, params)
        row = cur.fetchone()
        cols = [d.name for d in cur.description]  # type: ignore[union-attr]
        return dict(zip(cols, row))  # type: ignore[arg-type]


image_client = AzureOpenAIImage(
    volume_root=Path(os.environ["CREATIVES_VOLUME_ROOT"]),
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_KEY"],
)

orchestrator = CreativeOrchestrator(
    synthesize_brief=synthesize_brief_for_segment,
    image_client=image_client,
)


def _conn_factory():
    import psycopg
    return psycopg.connect(
        host=os.environ["PGHOST"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode="require",
    )


store = CampaignStore(_conn_factory)

app = build_app(
    orchestrator=orchestrator,
    build_aggregate=build_aggregate,
    store=store,
)
