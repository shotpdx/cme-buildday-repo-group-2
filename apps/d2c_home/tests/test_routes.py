from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app import build_app


def test_hero_returns_cached_with_personalized_subtitle(tmp_path, monkeypatch):
    seg = {"canonical_id": "c1", "persona": "Sports Fan",
           "primary_segment": "Sports Enthusiast", "value_segment": "High Value",
           "top_genre_1": "Sports", "first_name": "Alex"}
    lookup = MagicMock(return_value=seg)

    fake = tmp_path / "cached.png"
    fake.write_bytes(b"PNG")
    image_client = MagicMock()
    image_client.volume_path_for.return_value = fake

    copy_for = MagicMock(return_value={"tagline": "Your team.", "cta": "Watch", "subtitle": "Tipoff at 8pm."})

    app = build_app(fetch_segment=lookup, image_client=image_client, fetch_copy=copy_for)
    client = TestClient(app)

    r = client.get("/hero/c1")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "cached"
    assert "Alex" in body["subtitle"]
    assert body["tagline"] == "Your team."


def test_hero_falls_back_to_persona_default_on_cache_miss(tmp_path):
    seg = {"canonical_id": "c2", "persona": "Casual Viewer",
           "primary_segment": "Casual Browser", "value_segment": "Standard",
           "top_genre_1": "Entertainment"}
    image_client = MagicMock()
    image_client.volume_path_for.return_value = tmp_path / "missing.png"  # does not exist

    app = build_app(fetch_segment=lambda _: seg, image_client=image_client,
                    fetch_copy=lambda _: {"tagline": "", "cta": "", "subtitle": ""})
    client = TestClient(app)
    r = client.get("/hero/c2")
    assert r.status_code == 200
    assert r.json()["source"] == "persona_default"
