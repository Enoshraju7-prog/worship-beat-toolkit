"""Render each timing family once, then cut every pad on canonical sample bounds."""

from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
import zipfile
import numpy as np
import soundfile as sf
import soxr
from scipy.signal import find_peaks
from .audio import run, sha256, require_ffmpeg
from .project import (
    SR,
    validate_project,
    resolve_asset,
    is_approved,
    fingerprint,
    save_json,
)
from .remixlive import write_pack


def _alignment(original, retimed, tempo):
    from .analysis import features

    t, _, o = features(original)
    tt, _, oo = features(retimed)
    p, _ = find_peaks(
        o[2], distance=10, prominence=max(float(np.percentile(o[2], 90)), 0.01)
    )
    q, _ = find_peaks(
        oo[2], distance=10, prominence=max(float(np.percentile(oo[2], 90)), 0.01)
    )
    new = tt[q]
    errors = []
    if not len(new):
        return 0.0, 0
    for expected in t[p][:: max(1, len(p) // 1500)] / tempo:
        j = np.searchsorted(new, expected)
        near = new[max(0, j - 1) : j + 2]
        error = float(near[np.argmin(np.abs(near - expected))] - expected)
        if abs(error) < 0.08:
            errors.append(error)
    return (float(np.median(errors)) if len(errors) >= 25 else 0.0), len(errors)


def render_audio(p, project_file):
    validate_project(p)
    require_ffmpeg()
    stem = resolve_asset(project_file, p["stem"])
    if sha256(stem) != p["stem_sha256"]:
        raise ValueError(
            "Stem changed since preparation. Re-analyze the changed source."
        )
    source, sr = sf.read(stem, dtype="float32", always_2d=True)
    if sr != SR or source.shape[1] != 2:
        raise ValueError("Stem is not stereo 44.1 kHz.")
    if not np.isfinite(source).all():
        raise ValueError("Stem contains non-finite samples.")
    bar = round(SR * 60 / p["target_bpm"] * p["pulses_per_cycle"])
    lead = float(p.get("cut_lead_seconds", 0.02))
    if not 0 <= lead <= 0.05:
        raise ValueError("Pre-attack must be between 0 and 50 ms.")
    cache = {}
    raw = {}
    bounds = {}
    methods = {}
    for pad in p["pads"]:
        period = pad["source_cycle_seconds"]
        rate = bar / period
        if period not in cache:
            change = SR / rate
            if abs(change - 1) < 1e-9:
                y = source
                method = "none"
                correction = 0.0
                matched = 0
            elif abs(change - 1) < 0.001:
                y = soxr.resample(source, SR, rate, quality="VHQ")
                method = "VHQ clock correction"
                correction = 0.0
                matched = 0
            else:
                folder = Path(project_file).parent / "cache"
                folder.mkdir(exist_ok=True)
                key = sha256(stem)[:12] + f"_{change:.12f}"
                path = folder / (key + ".wav")
                record = folder / (key + ".json")
                if not path.exists():
                    partial = path.with_suffix(".partial.wav")
                    run(
                        [
                            "ffmpeg",
                            "-v",
                            "error",
                            "-nostdin",
                            "-y",
                            "-i",
                            stem,
                            "-af",
                            f"atempo={change:.15g}",
                            "-ar",
                            str(SR),
                            "-ac",
                            "2",
                            "-c:a",
                            "pcm_f32le",
                            partial,
                        ]
                    )
                    partial.replace(path)
                if record.exists():
                    r = json.loads(record.read_text())
                    correction = r["correction"]
                    matched = r["matched_events"]
                else:
                    correction, matched = _alignment(stem, path, change)
                    save_json(
                        record, dict(correction=correction, matched_events=matched)
                    )
                y = sf.read(path, dtype="float32", always_2d=True)[0]
                method = "pitch-preserving atempo"
            cache[period] = y
            methods[period] = dict(
                method=method, correction_seconds=correction, matched_events=matched
            )
        phase = round(pad["source_start"] % period, 6)
        if abs(phase - period) < 1e-6:
            phase = 0.0
        cycle = round((pad["source_start"] - phase) / period)
        a = (
            round((phase - lead) * rate)
            + cycle * bar
            + round(methods[period]["correction_seconds"] * SR)
        )
        b = a + pad["cycles"] * bar
        y = cache[period]
        if b > len(y):
            raise ValueError(
                "Retimed pad exceeds available audio; shorten it or choose an earlier take."
            )
        clip = np.zeros((b - a, 2), np.float32)
        offset = max(0, -a)
        clip[offset:] = y[max(0, a) : b]
        raw[pad["number"]] = clip
        bounds[pad["number"]] = (a, b, period)
    peak = max(float(np.max(np.abs(v))) for v in raw.values())
    if peak < 1e-6:
        raise ValueError("Selected audio is silent.")
    gain = min(4.0, 10 ** (-1.5 / 20) / peak)
    rendered = {}
    edge = round(SR * 0.003)
    fade = np.sin(np.linspace(0, np.pi / 2, edge)) ** 2
    for n, x in raw.items():
        x = x * gain
        x[:edge] *= fade[:, None]
        x[-edge:] *= fade[::-1, None]
        rendered[n] = x
    for a, b in p.get("routes", []):
        if bounds[a][2] != bounds[b][2] or bounds[a][1] != bounds[b][0]:
            raise ValueError(
                f"Non-contiguous declared route {a:02d}->{b:02d}. Correct the source boundaries."
            )
    for a, b in p.get("fill_pairs", []):
        if len(raw[a]) > len(raw[b]) or not np.array_equal(
            raw[a], raw[b][: len(raw[a])]
        ):
            raise ValueError(
                "Separated fill is not the prefix of its combined fill/return."
            )
    return rendered, bounds, methods, gain


def export_project(p, project_file, out=None, draft=False):
    if not draft and not is_approved(p):
        raise ValueError(
            "Listen and approve this exact selection first, or explicitly export a draft."
        )
    audio, bounds, methods, gain = render_audio(p, project_file)
    parent = Path(project_file).parent
    out = (
        Path(out)
        if out
        else parent / "exports" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    out.mkdir(parents=True, exist_ok=False)
    manifest = []
    decoded = {}
    for pad in p["pads"]:
        n = pad["number"]
        path = out / f"{n:02d}.wav"
        sf.write(path, audio[n], SR, subtype="PCM_16")
        decoded[n] = sf.read(path, always_2d=True)[0]
        manifest.append(
            dict(
                number=n,
                pad=f"{n:02d}",
                wav=path.name,
                label=pad["label"],
                section=pad["section"],
                role=pad["role"],
                mode=pad["mode"],
                cycles=pad["cycles"],
                beats=pad["cycles"] * p["pulses_per_cycle"],
                bpm=p["target_bpm"],
                source_start_seconds=pad["source_start"]
                + p["source"]["requested_start"],
                source_cycle_seconds=pad["source_cycle_seconds"],
                duration_seconds=len(audio[n]) / SR,
                frames=len(audio[n]),
                sha256=sha256(path),
                shared_gain=gain,
                retiming=methods[pad["source_cycle_seconds"]],
                rendered_bounds=list(bounds[n][:2]),
            )
        )
    demos = out / "LISTEN_FIRST_DO_NOT_IMPORT"
    demos.mkdir()
    for name, seq in p.get("demos", {}).items():
        safe = "".join(c for c in name if c.isalnum() or c in "_-") or "demo"
        sf.write(
            demos / (safe + ".wav"),
            np.concatenate([decoded[n] for n in seq]),
            SR,
            subtype="PCM_16",
        )
    native = out / "WORSHIP_BEATS.rmxl"
    write_pack(
        native,
        p["name"],
        p["target_bpm"],
        p["pulses_per_cycle"],
        p["columns"],
        manifest,
        out,
    )
    save_json(out / "manifest.json", manifest)
    save_json(
        out / "project_export.json",
        {k: v for k, v in p.items() if k not in ("analysis",)},
    )
    status = (
        "DRAFT — listening approval required"
        if draft
        else "Selection approved by user; device checks separate"
    )
    lines = [
        p["name"],
        status,
        f"BPM: {p['target_bpm']:g}. Sampler pulses per cycle: {p['pulses_per_cycle']}. Not an inferred notation meter.",
        "Columns are vertical, counted left to right. Rows are horizontal, top to bottom.",
        "Row | Column 1 | Column 2 | Column 3",
    ]
    for r in range(len(p["columns"][0])):
        lines.append(
            str(r + 1)
            + " | "
            + " | ".join(f"{c[r]:02d}" if c[r] else "Empty" for c in p["columns"])
        )
    lines += ["", "PAD GUIDE:"] + [
        f"{m['pad']} — {m['label']} [{m['section']}], {m['mode']}, {m['cycles']} cycles"
        for m in manifest
    ]
    lines += ["", "ROUTES:"] + [f"{a:02d} -> {b:02d}" for a, b in p.get("routes", [])]
    lines += [
        "",
        "Use one COMPLETE drum/accompaniment pad at a time. Different columns can overlap.",
        "Loop for mains; One Shot for replacement fills. A One Shot does not recall the main automatically.",
        "Queue the following main during the final cycle of a fill/return. Check Multiple Mode OFF and Repeat OFF in your app.",
        "Keep main -> fill -> return within one column; stop the old column before a cross-column change.",
        "Do not import LISTEN_FIRST_DO_NOT_IMPORT as pads. WAV files are PCM16 stereo 44.1 kHz, under 20 seconds.",
        "Native format adapter is based on Remixlive 8.7.0. Check import, playback, export and re-import on your device.",
        "Technical validation is not a listening-quality or mobile-sharing guarantee. Separation can retain bleed/artifacts.",
        "Full backing-music pads contain chord progressions: do not interchange them based on BPM alone.",
    ]
    (out / "START_HERE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    from .validate import validate_pack

    report = validate_pack(out)
    report.update(
        draft=draft,
        human_listening_approved=is_approved(p) and not draft,
        review_fingerprint=fingerprint(p),
        source_sha256=p["source"]["master_sha256"],
        retiming_methods=list(methods.values()),
        mobile_verified=False,
        actual_app_round_trip_verified=False,
    )
    save_json(out / "validation.json", report)
    archive = out / "NUMBERED_WAV_PACK.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in out.rglob("*"):
            if path.is_file() and path not in (archive, native):
                z.write(path, path.relative_to(out))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            raise ValueError("WAV ZIP CRC error.")
    return out
