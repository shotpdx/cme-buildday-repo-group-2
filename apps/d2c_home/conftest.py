"""Pytest bootstrap — ensures the app dir is on sys.path so ``from app import build_app`` works."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
