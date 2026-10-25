"""Portable project documents and review invalidation."""

from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import tempfile

SCHEMA_VERSION = 1
SR = 44100


def save_json(path: Path, data: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
        tmp = Path(f.name)
    tmp.replace(path)


def load_project(path: Path) -> dict:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if p.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported project version; use a version-1 project.json.")
    return p


def fingerprint(p: dict) -> str:
    fields = {
        k: p.get(k)
        for k in (
            "source",
            "stem",
            "stem_sha256",
            "separation",
            "mode",
            "target_bpm",
            "pulses_per_cycle",
            "notation_meter",
            "grid",
            "cut_lead_seconds",
            "pads",
            "columns",
            "sections",
            "routes",
            "fill_pairs",
            "demos",
        )
    }
    return hashlib.sha256(
        json.dumps(fields, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def approve(p: dict, note: str) -> None:
    validate_project(p)
    if not note.strip():
        raise ValueError("Write a listening-review note before approving.")
    p["review"] = {
        "approved_fingerprint": fingerprint(p),
        "note": note,
        "human_listening_approved": True,
    }


def is_approved(p: dict) -> bool:
    return p.get("review", {}).get("approved_fingerprint") == fingerprint(p)


def validate_project(p: dict) -> None:
    bpm = float(p["target_bpm"])
    pulses = p["pulses_per_cycle"]
    if not math.isfinite(bpm) or not 20 <= bpm <= 300:
        raise ValueError("BPM must be finite and between 20 and 300.")
    if type(pulses) is not int or not 1 <= pulses <= 16:
        raise ValueError("Sampler pulses per cycle must be a whole number from 1–16.")
    if (
        not math.isfinite(float(p["source"]["duration_seconds"]))
        or p["source"]["duration_seconds"] <= 0
    ):
        raise ValueError("Source duration must be finite and positive.")
    pads = p.get("pads", [])
    numbers = [x["number"] for x in pads]
    if not pads or len(set(numbers)) != len(numbers):
        raise ValueError("Select pads with unique numbers.")
    for pad in pads:
        if not isinstance(pad["number"], int) or not 1 <= pad["number"] <= 99:
            raise ValueError("Pad numbers must be integers 1–99.")
        bars = pad["cycles"]
        if not isinstance(bars, int) or bars < 1:
            raise ValueError("Each pad needs a positive whole number of cycles.")
        if bars * round(SR * 60 / bpm * pulses) / SR >= 20:
            raise ValueError(
                f"Pad {pad['number']:02d} is 20 seconds or longer; split/shorten it."
            )
        start = float(pad["source_start"])
        period = float(pad["source_cycle_seconds"])
        if (
            not math.isfinite(start)
            or start < 0
            or not math.isfinite(period)
            or period <= 0
        ):
            raise ValueError("Invalid source boundary/period.")
        if start + bars * period > p["source"]["duration_seconds"] + 1 / SR:
            raise ValueError("Pad exceeds the requested source excerpt.")
        if pad["mode"] not in ("Loop", "One Shot"):
            raise ValueError("Mode must be Loop or One Shot.")
    cols = p["columns"]
    if (
        len(cols) != 3
        or any(len(c) not in (5, 6) for c in cols)
        or len({len(c) for c in cols}) != 1
    ):
        raise ValueError("Use exactly three columns with five or six equal rows.")
    refs = [n for c in cols for n in c if n]
    if set(refs) != set(numbers):
        raise ValueError(
            "Layout must contain every selected pad and no unknown numbers."
        )
    for key in ("routes", "fill_pairs"):
        for pair in p.get(key, []):
            if len(pair) != 2 or any(n not in numbers for n in pair):
                raise ValueError(f"Invalid {key} reference.")
    for seq in p.get("demos", {}).values():
        if not seq or any(n not in numbers for n in seq):
            raise ValueError("Invalid demo sequence.")


def resolve_asset(project_file: Path, relative: str) -> Path:
    root = Path(project_file).resolve().parent
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Project assets must remain inside the project folder.")
    return path
