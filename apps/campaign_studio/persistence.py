"""Lakebase persistence for Campaign Studio.

Wraps CRUD on ``media_demo.generated_campaigns`` via raw psycopg3 SQL to
match the project's "no ORM in core" pattern. The row schema is defined
in ``pipelines/migrations/001_generated_campaigns.sql``.

``CampaignStore`` takes a ``conn_factory`` callable that yields a fresh
psycopg ``Connection`` per call (short-lived transactions, one per method).
Tests inject a ``FakeStore`` with the same shape and bypass Postgres.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional, Protocol


class Store(Protocol):
    """Minimal interface ``app.py`` depends on — keeps tests from needing psycopg."""

    def create(self, cid: str, filter_: dict[str, Any]) -> None: ...

    def get(self, cid: str) -> Optional[dict[str, Any]]: ...

    def update_asset(self, cid: str, format_name: str, asset: dict[str, Any]) -> None: ...

    def update_status(self, cid: str, status: str) -> None: ...


class CampaignStore:
    """Postgres-backed ``Store`` for ``media_demo.generated_campaigns``.

    ``conn_factory`` is called once per method and must return a context-
    managed ``psycopg.Connection``. Each method runs inside an implicit
    transaction that commits on successful block exit.
    """

    def __init__(
        self,
        conn_factory: Callable[[], Any],
        *,
        created_by: str = "campaign_studio",
    ) -> None:
        self._conn_factory = conn_factory
        self._created_by = created_by

    def create(self, cid: str, filter_: dict[str, Any]) -> None:
        sql = """
            INSERT INTO media_demo.generated_campaigns
                (campaign_id, segment_filter_json, assets_json, status, created_by)
            VALUES (%s, %s::jsonb, '{}'::jsonb, 'running', %s)
        """
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, (cid, json.dumps(filter_), self._created_by))

    def get(self, cid: str) -> Optional[dict[str, Any]]:
        sql = """
            SELECT campaign_id, segment_filter_json, assets_json, status,
                   created_by, created_ts, updated_ts
            FROM media_demo.generated_campaigns
            WHERE campaign_id = %s
        """
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, (cid,))
            row = cur.fetchone()
            if row is None:
                return None
            # psycopg already decodes jsonb into Python dict/list.
            return {
                "campaign_id": row[0],
                "filter": row[1],
                "assets": row[2],
                "status": row[3],
                "created_by": row[4],
                "created_ts": row[5],
                "updated_ts": row[6],
            }

    def update_asset(
        self, cid: str, format_name: str, asset: dict[str, Any]
    ) -> None:
        # jsonb_set merges the format's asset sub-object into ``assets_json``
        # without replacing the whole blob — concurrent regens for different
        # formats stay safe under this pattern.
        sql = """
            UPDATE media_demo.generated_campaigns
            SET assets_json = jsonb_set(assets_json, %s, %s::jsonb, true),
                updated_ts = now()
            WHERE campaign_id = %s
        """
        path = "{" + format_name + "}"
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, (path, json.dumps(asset), cid))

    def update_status(self, cid: str, status: str) -> None:
        sql = """
            UPDATE media_demo.generated_campaigns
            SET status = %s, updated_ts = now()
            WHERE campaign_id = %s
        """
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, (status, cid))


class FakeStore:
    """In-memory ``Store`` for tests.

    Mirrors the ``CampaignStore`` interface exactly so app code can stay
    agnostic. Persists nothing across instances.
    """

    def __init__(self) -> None:
        self._rows: dict[str, dict[str, Any]] = {}

    def create(self, cid: str, filter_: dict[str, Any]) -> None:
        self._rows[cid] = {
            "campaign_id": cid,
            "filter": filter_,
            "assets": {},
            "status": "running",
        }

    def get(self, cid: str) -> Optional[dict[str, Any]]:
        row = self._rows.get(cid)
        if row is None:
            return None
        # Return a shallow copy so callers can't mutate our storage.
        return dict(row)

    def update_asset(
        self, cid: str, format_name: str, asset: dict[str, Any]
    ) -> None:
        self._rows[cid]["assets"][format_name] = asset

    def update_status(self, cid: str, status: str) -> None:
        self._rows[cid]["status"] = status
