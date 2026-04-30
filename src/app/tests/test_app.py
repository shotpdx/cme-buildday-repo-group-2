import os
import sys
from pathlib import Path

import dash
from dash.development.base_component import Component

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["USE_MOCK_BACKEND"] = "true"

from app.app import app, create_app  # noqa: E402


def test_app_layout_is_valid_dash_component() -> None:
    assert isinstance(app.layout, Component)


def test_create_app_works_in_mock_mode() -> None:
    mock_app = create_app()

    assert isinstance(mock_app, dash.Dash)
    assert mock_app.server is not None
    assert mock_app.layout is not None
