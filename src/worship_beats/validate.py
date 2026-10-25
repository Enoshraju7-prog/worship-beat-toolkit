"""Strict exported-PCM, sample-count and container checks."""

from pathlib import Path
import json
import zipfile
import numpy as np
import soundfile as sf
from .audio import run, sha256, require_ffmpeg
from .project import SR
from .remixlive import validate_native


def validate_pack(folder):
    folder = Path(folder)
    require_ffmpeg()
    manifest = json.loads((folder / "manifest.json").read_text())
    if not manifest:
        raise ValueError("No performance pads.")
    if {p.name for p in folder.glob("*.wav")} != {m["wav"] for m in manifest}:
        raise ValueError("Manifest/file mismatch.")
    checks = []
    for m in manifest:
        if m["wav"] != f"{m['number']:02d}.wav":
            raise ValueError("Pads must use their two-digit numbered WAV filename.")
        p = folder / m["wav"]
        info = sf.info(p)
        x, sr = sf.read(p, always_2d=True)
        expected = m["cycles"] * round(SR * 60 / m["bpm"] * (m["beats"] / m["cycles"]))
        if (sr, info.channels, info.subtype, info.frames) != (
            SR,
            2,
            "PCM_16",
            expected,
        ):
            raise ValueError("Wrong PCM format or cycle length: " + p.name)
        if (
            info.frames != m["frames"]
            or abs(info.duration - m["duration_seconds"]) > 1 / SR
        ):
            raise ValueError("Manifest duration/frame mismatch: " + p.name)
        if (
            info.duration >= 20
            or not np.isfinite(x).all()
            or np.max(np.abs(x)) >= 1
            or np.max(np.abs(x[[0, -1]])) > 2 / 32768
        ):
            raise ValueError("Invalid duration, level or edge: " + p.name)
        if sha256(p) != m["sha256"]:
            raise ValueError("File hash mismatch.")
        run(["ffmpeg", "-v", "error", "-nostdin", "-i", p, "-f", "null", "-"])
        checks.append(
            dict(
                file=p.name,
                frames=info.frames,
                peak_dbfs=float(20 * np.log10(max(np.max(np.abs(x)), 1e-12))),
            )
        )
    for p in (folder / "LISTEN_FIRST_DO_NOT_IMPORT").glob("*.wav"):
        run(["ffmpeg", "-v", "error", "-nostdin", "-i", p, "-f", "null", "-"])
    native = validate_native(folder / "WORSHIP_BEATS.rmxl", manifest, folder)
    archive = folder / "NUMBERED_WAV_PACK.zip"
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            if z.testzip():
                raise ValueError("Archive CRC error.")
    return dict(
        passed=True, checks=checks, native=native, listening_quality_verified=False
    )
