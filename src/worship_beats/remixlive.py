"""Minimal 8x6 adapter derived from a blank Remixlive 8.7.0 export.

No stock-pack audio/template is required. Empty Song asset is intentionally included.
"""

from __future__ import annotations
import json
from pathlib import Path
import uuid
import zipfile
from urllib.parse import quote


def empty_pad(col: int, row: int) -> dict:
    return dict(
        reverse=0,
        beatsOverrided=-1,
        waveFadeOutMs=0,
        cutStart=0,
        biFilter=0,
        waveFadeInMs=0,
        repeat=0,
        playMode=0,
        waveEnd=-1,
        chokeGroup=-1,
        waveAttack=-1,
        meta="",
        bpmOverrided=-1,
        waveDecay=-1,
        waveStart=-1,
        line=row,
        waveSustain=-1,
        linkGroup=-1,
        mixerChannel=col,
        pan=0.5,
        col=col,
        gain=1,
        cutEnd=1,
        waveRelease=-1,
        sampleName="",
        quantize=-1,
        linkLauncher=0,
        pitch=0,
        replaySequenceQuantize=0,
    )


def write_pack(
    path: Path,
    title: str,
    bpm: float,
    quantize: float,
    columns: list,
    manifest: list,
    folder: Path,
) -> None:
    title = title.replace("/", "_").replace("\\", "_").strip()[:100] or "Worship Beats"
    project = dict(
        drumQuantize=0,
        productId="com.mixvibes.user.iPad."
        + quote(title, safe="")
        + "."
        + str(uuid.uuid4()).upper(),
        sessions=["8x6.json"],
        version="",
        long_description="",
        short_description="",
        author="",
        author_url="",
        key="",
        audio_preview_url="",
        video_preview_url="",
        bpm=bpm,
        quantize=quantize,
        about_this_bank_url="",
        user=1,
        name=title,
        copyright="",
    )
    session = dict(
        effect_name="Delay",
        column_number=8,
        row_number=6,
        effect_y=0,
        bi_filter=0,
        effect_x=0,
        song={"sampleName": "Song_8x6.song"},
        effect_lock=0,
        tracks=[
            dict(
                col=c,
                effect_name="Delay",
                filter=0,
                effect_y=0,
                eq_mid=0,
                level=1,
                effect_x=0,
                eq_bass=0,
                eq_treb=0,
                colorId=-1,
                effect_lock=0,
            )
            for c in range(8)
        ],
        grids=[
            dict(
                grid_type=k, pads=[empty_pad(c, r) for c in range(8) for r in range(6)]
            )
            for k in (2, 0, 1)
        ],
    )
    grid = next(g for g in session["grids"] if g["grid_type"] == 0)
    positions = {(p["col"], p["line"]): p for p in grid["pads"]}
    lookup = {m["number"]: m for m in manifest}
    for c, col in enumerate(columns):
        for r, n in enumerate(col):
            if n:
                m = lookup[n]
                positions[c, r].update(
                    sampleName=m["wav"],
                    playMode=1 if m["mode"] == "One Shot" else 0,
                    beatsOverrided=float(m["beats"]),
                    bpmOverrided=-1,
                    repeat=0,
                    meta='{"voices":0,"grooveAmount":0}',
                )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(title + ".json", json.dumps(project, ensure_ascii=False, indent=2))
        z.writestr("8x6.json", json.dumps(session, indent=2))
        z.writestr(
            "samples/Song_8x6.song",
            json.dumps(dict(notes=[], lengthInBeats=240.0), indent=2),
        )
        for m in manifest:
            z.write(folder / m["wav"], "samples/" + m["wav"])
            meta = dict(
                attack=0,
                start=0,
                releas=0,
                mediaTypeId=1,
                type="loop",
                instrumentId=11,
                beats=m["beats"],
                key="",
                decay=0.5,
                bpm=bpm,
                sustain=1,
                duration=m["duration_seconds"],
                end=1,
                user=1,
                displayName=f"{m['number']:02d}",
                name=m["wav"],
            )
            z.writestr(f"samples/{m['number']:02d}.json", json.dumps(meta, indent=2))
    validate_native(path, manifest, folder)


def validate_native(
    path: Path, manifest: list | None = None, folder: Path | None = None
) -> dict:
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            raise ValueError("Native archive CRC error.")
        for n in z.namelist():
            if n.startswith("/") or ".." in Path(n).parts:
                raise ValueError("Unsafe native archive member.")
        roots = [
            n
            for n in z.namelist()
            if n.endswith(".json") and "/" not in n and n != "8x6.json"
        ]
        if len(roots) != 1:
            raise ValueError("Native project root must be unambiguous.")
        project = json.loads(z.read(roots[0]))
        session = json.loads(z.read("8x6.json"))
        for name in project["sessions"]:
            if name not in z.namelist():
                raise ValueError("Missing native session.")

        def check_refs(obj):
            if isinstance(obj, dict):
                if (
                    obj.get("sampleName")
                    and "samples/" + obj["sampleName"] not in z.namelist()
                ):
                    raise ValueError("Missing referenced asset: " + obj["sampleName"])
                for v in obj.values():
                    check_refs(v)
            elif isinstance(obj, list):
                for v in obj:
                    check_refs(v)

        check_refs(session)
        if manifest:
            import hashlib

            expected = {m["wav"]: m for m in manifest}
            grid = next(g for g in session["grids"] if g["grid_type"] == 0)
            populated = [p for p in grid["pads"] if p.get("sampleName")]
            if {p["sampleName"] for p in populated} != set(expected):
                raise ValueError("Native pad/manifest mismatch.")
            for pad in populated:
                m = expected[pad["sampleName"]]
                if not 0 <= pad["col"] < 3 or not 0 <= pad["line"] < 6:
                    raise ValueError(
                        "Native performance layout must use the first three columns."
                    )
                if pad["beatsOverrided"] != m["beats"] or pad["playMode"] != (
                    1 if m["mode"] == "One Shot" else 0
                ):
                    raise ValueError("Native pad beat count/mode mismatch.")
            for m in manifest:
                if (
                    hashlib.sha256(z.read("samples/" + m["wav"])).hexdigest()
                    != m["sha256"]
                ):
                    raise ValueError("Embedded WAV differs from export.")
                meta = json.loads(z.read(f"samples/{m['number']:02d}.json"))
                if (
                    meta["beats"] != m["beats"]
                    or meta["bpm"] != m["bpm"]
                    or project["bpm"] != m["bpm"]
                ):
                    raise ValueError("Native tempo/beat metadata mismatch.")
                if abs(meta["duration"] - m["duration_seconds"]) > 1 / 44100:
                    raise ValueError("Native duration metadata mismatch.")
        return dict(
            crc=True,
            all_sample_references_present=True,
            embedded_hashes=bool(manifest),
            app_round_trip_verified=False,
        )
