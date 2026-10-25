"""Safe subprocess I/O, source retention and source-range decoding."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlparse
import numpy as np
import soundfile as sf
from .project import save_json


def run(args: list[str], **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def time_seconds(value: str | float | None) -> float | None:
    if value is None:
        return None
    parts = str(value).split(":")
    if len(parts) > 3:
        raise ValueError("Use seconds, mm:ss or hh:mm:ss.")
    result = 0.0
    for part in parts:
        result = result * 60 + float(part)
    if not np.isfinite(result) or result < 0:
        raise ValueError("Time must be finite and nonnegative.")
    return result


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require_ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise RuntimeError("FFmpeg not found. On Mac: brew install ffmpeg")
    return executable


def ingest(
    source: str, job: Path, start: float = 0, end: float | None = None, progress=print
) -> dict:
    require_ffmpeg()
    job = Path(job)
    folder = job / "source"
    folder.mkdir(parents=True, exist_ok=True)
    state = folder / "source.json"
    if state.exists():
        old = json.loads(state.read_text())
        if (
            old["input"] == source
            and old["requested_start"] == start
            and old["requested_end"] == end
        ):
            if sha256(folder / "master.wav") != old["master_sha256"]:
                raise ValueError("Cached master changed; use a new job folder.")
            if sha256(job / old["original"]) != old["original_sha256"]:
                raise ValueError("Cached original changed; use a new job folder.")
            return old
        raise FileExistsError(
            "This job belongs to a different input/range; choose a new job folder."
        )
    if (
        not np.isfinite(start)
        or start < 0
        or end is not None
        and (not np.isfinite(end) or end <= start)
    ):
        raise ValueError("Use finite times; end must be after start.")
    url = urlparse(source)
    if url.scheme in ("http", "https"):
        if url.hostname not in (
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
            "music.youtube.com",
        ):
            raise ValueError(
                "Only YouTube URLs are accepted. Download other authorized media yourself and select a local file."
            )
        import yt_dlp

        progress("Downloading source audio (no browser cookies are collected).")
        try:
            with yt_dlp.YoutubeDL(
                {
                    "format": "bestaudio/best",
                    "noplaylist": True,
                    "outtmpl": str(folder / "original.%(ext)s"),
                    "writeinfojson": True,
                }
            ) as dl:
                info = dl.extract_info(source, download=True)
                original = Path(dl.prepare_filename(info))
        except Exception as exc:
            raise RuntimeError(
                "YouTube download unavailable. Supply an authorized local audio/video file; no access-control bypass is attempted."
            ) from exc
        title = info.get("title", "Song")
    else:
        local = Path(source).expanduser().resolve()
        if not local.is_file():
            raise FileNotFoundError(local)
        original = folder / ("original" + local.suffix.lower())
        shutil.copy2(local, original)
        title = local.stem
    progress("Decoding the requested range to stereo 44.1 kHz PCM.")
    target = folder / "master.wav"
    partial = folder / "master.partial.wav"
    args = [
        "ffmpeg",
        "-v",
        "error",
        "-nostdin",
        "-y",
        "-i",
        str(original),
        "-ss",
        str(start),
    ]
    if end is not None:
        args += ["-t", str(end - start)]
    run(args + ["-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(partial)])
    meta = sf.info(partial)
    if meta.frames < 44100:
        raise ValueError("Excerpt is too short or outside the source.")
    partial.replace(target)
    record = dict(
        input=source,
        title=title,
        requested_start=start,
        requested_end=end,
        duration_seconds=meta.duration,
        original="source/" + original.name,
        master="source/master.wav",
        master_sha256=sha256(target),
        original_sha256=sha256(original),
    )
    save_json(state, record)
    return record
