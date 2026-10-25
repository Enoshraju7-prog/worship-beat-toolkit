"""Load the actual local UI and export an audition through its button."""

from pathlib import Path
import sys

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest
from worship_beats.project import save_json

APP = Path(__file__).resolve().parents[1] / "src/worship_beats/app.py"


def test_app_opens_empty(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(APP)])
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "Worship Beat Toolkit"


def test_app_loads_project_and_builds_draft(project, monkeypatch):
    p, path = project
    p["source"]["master"] = p["stem"]
    save_json(path, p)
    monkeypatch.setattr(sys, "argv", [str(APP), str(path)])
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    button = next(
        b for b in app.button if b.label == "Build listening previews / draft pack"
    )
    button.click().run(timeout=60)
    assert not app.exception
    assert list((path.parent / "exports").glob("*/WORSHIP_BEATS.rmxl"))
