"""Export endpoint — streams a zip with 4 PNGs and a manifest.json."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app import build_app
from persistence import FakeStore


class FakeOrchestrator:
    """Orchestrator whose output paths are injected by the test fixture."""

    def __init__(self, image_paths: dict[str, Path]) -> None:
        self._image_paths = image_paths

    def render(self, agg, *, size, quality, personalize=True):
        from lakefoundry.creative.orchestrator import CreativeOutput

        # Pick a path by size — one per format (sizes are unique across formats
        # except display_banner vs email_header which share 1792x1024, so we
        # fall back to the remaining path). This only has to hold for the
        # four-format fan-out the test exercises.
        size_to_format = {
            "1024x1024": "social_square",
            "1024x1792": "vertical_story",
            "1792x1024": "display_banner",  # first one wins; second call gets email_header
        }
        fmt_name = size_to_format.get(size, "social_square")
        path = self._image_paths.get(fmt_name) or next(iter(self._image_paths.values()))
        return CreativeOutput(
            brief={
                "theme": "t",
                "mood": "m",
                "visual_elements": ["a"],
                "subject_description": "s",
                "copy_direction": {"tagline": "tl", "cta": "cta", "subtitle": "sub"},
            },
            image_path=path,
            copy={"tagline": fmt_name, "cta": "cta", "subtitle": "sub"},
            image_cache_hit=True,
            latency_s=0.01,
        )


def _make_png_files(tmp_path: Path) -> dict[str, Path]:
    """Write 4 tiny files (PNG magic bytes) and return a format -> path map."""
    png_header = b"\x89PNG\r\n\x1a\n"
    paths: dict[str, Path] = {}
    for fmt in ("social_square", "vertical_story", "display_banner", "email_header"):
        p = tmp_path / f"{fmt}.png"
        p.write_bytes(png_header + fmt.encode())
        paths[fmt] = p
    return paths


def test_export_returns_zip_with_four_images_and_manifest(tmp_path: Path) -> None:
    image_paths = _make_png_files(tmp_path)
    store = FakeStore()

    # Seed the store directly — bypass the orchestrator fan-out so we control
    # image_path values precisely.
    cid = "test-campaign-xyz"
    store.create(cid, {"persona": "Sports Fan"})
    for fmt_name, path in image_paths.items():
        store.update_asset(
            cid,
            fmt_name,
            {
                "image_path": str(path),
                "copy": {"tagline": fmt_name, "cta": "cta", "subtitle": "sub"},
                "latency_s": 0.01,
            },
        )
    store.update_status(cid, "approved")

    app = build_app(
        orchestrator=FakeOrchestrator(image_paths),
        build_aggregate=lambda f: {},
        store=store,
    )
    client = TestClient(app)

    r = client.get(f"/campaigns/{cid}/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"] == f'attachment; filename="campaign-{cid}.zip"'

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())
        assert names == {
            "social_square.png",
            "vertical_story.png",
            "display_banner.png",
            "email_header.png",
            "manifest.json",
        }

        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["campaign_id"] == cid
        assert manifest["filter"] == {"persona": "Sports Fan"}
        assert manifest["status"] == "approved"
        assert set(manifest["formats"].keys()) == {
            "social_square",
            "vertical_story",
            "display_banner",
            "email_header",
        }
        for fmt_name, entry in manifest["formats"].items():
            assert entry["arcname"] == f"{fmt_name}.png"
            assert entry["copy"]["tagline"] == fmt_name
            assert entry["latency_s"] == 0.01
            assert Path(entry["image_path"]).name == f"{fmt_name}.png"

        # Each PNG in the zip matches the content we wrote.
        for fmt_name, path in image_paths.items():
            assert zf.read(f"{fmt_name}.png") == path.read_bytes()


def test_export_unknown_campaign_returns_404() -> None:
    app = build_app(
        orchestrator=FakeOrchestrator({}),
        build_aggregate=lambda f: {},
        store=FakeStore(),
    )
    client = TestClient(app)
    r = client.get("/campaigns/does-not-exist/export")
    assert r.status_code == 404
