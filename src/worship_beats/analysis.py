"""Multiband/onset timing and recurrent motif proposals, never lyric inference."""

from __future__ import annotations
import numpy as np
import soundfile as sf
import soxr
from scipy.signal import find_peaks

FS = 11025
HOP = 64


def features(path):
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    y = soxr.resample(y.mean(1), sr, FS, quality="VHQ")
    n = 512
    window = np.hanning(n)
    freq = np.fft.rfftfreq(n, 1 / FS)
    masks = [
        (freq >= a) & (freq < b) for a, b in ((35, 180), (180, 1500), (1500, 5200))
    ]
    starts = np.arange(0, len(y) - n, HOP)
    if len(starts) < 20:
        raise ValueError("Audio is too short to analyze.")
    energy = np.empty((3, len(starts)), np.float32)
    for first in range(0, len(starts), 5000):
        ids = starts[first : first + 5000, None] + np.arange(n)[None, :]
        power = np.abs(np.fft.rfft(y[ids] * window, axis=1)) ** 2
        for band, mask in enumerate(masks):
            energy[band, first : first + len(ids)] = np.sqrt(power[:, mask].sum(1))
    onset = np.maximum(0, np.diff(energy, axis=1, prepend=energy[:, :1]))
    return (starts + n / 2) / FS, energy, onset


def recurrence(onset, minimum=0.25, maximum=12):
    v = onset - onset.mean(1, keepdims=True)
    v /= np.maximum(np.sqrt(np.mean(v * v, axis=1, keepdims=True)), 1e-9)
    n = v.shape[1]
    size = 1 << (2 * n - 1).bit_length()
    z = np.fft.rfft(v, n=size, axis=1)
    c = np.fft.irfft(z * z.conj(), n=size, axis=1)[:, :n].sum(0)
    c /= np.arange(n, 0, -1)
    if c[0] <= 1e-12:
        return []
    c /= c[0]
    peaks, _ = find_peaks(c)
    peaks = [i for i in peaks if minimum <= i * HOP / FS <= maximum]
    rows = []
    for i in sorted(peaks, key=lambda k: c[k], reverse=True)[:16]:
        offset = 0.5 * (c[i - 1] - c[i + 1]) / (c[i - 1] - 2 * c[i] + c[i + 1])
        rows.append(dict(seconds=float((i + offset) * HOP / FS), score=float(c[i])))
    return rows


def active_region(t, energy):
    level = np.sqrt(np.mean(energy**2, axis=0))
    if level.max() < 1e-5:
        raise ValueError("No usable signal: silence or nearly silent drum stem.")
    threshold = max(float(np.percentile(level, 90)) * 0.08, 1e-5)
    ids = np.flatnonzero(level > threshold)
    return float(t[ids[0]]), float(t[ids[-1]])


def fit_grid(t, o, bpm, start, end, pulses=4):
    active = (t >= start) & (t < end)
    if active.sum() < 20:
        raise ValueError("Not enough active audio for grid fitting.")
    period = 60 / float(bpm)
    scaled = o / np.maximum(
        np.percentile(o[:, active], 97, axis=1, keepdims=True), 1e-8
    )
    score = np.minimum(scaled, 3).sum(0)
    phases = np.linspace(0, period, 1600, endpoint=False)
    scores = []
    for phase in phases:
        ns = np.arange(
            np.ceil((start - phase) / period), np.floor((end - phase) / period) + 1
        )
        ix = np.clip(np.searchsorted(t, phase + ns * period), 1, len(t) - 2)
        scores.append(
            float(np.mean(np.maximum.reduce([score[ix - 1], score[ix], score[ix + 1]])))
        )
    phase = float(phases[np.argmax(scores)])
    ns = np.arange(
        np.ceil((start - phase) / period), np.floor((end - phase) / period) + 1
    )
    observed = []
    strength = []
    for expected in phase + ns * period:
        ix = np.flatnonzero(np.abs(t - expected) <= min(0.06, period * 0.15))
        j = ix[np.argmax(score[ix])]
        observed.append(t[j])
        strength.append(score[j])
    observed = np.asarray(observed)
    strength = np.asarray(strength)
    keep = strength >= np.percentile(strength, 35)
    if keep.sum() < 4:
        raise ValueError("Insufficient recurring transients.")
    for _ in range(4):
        period, phase = map(float, np.polyfit(ns[keep], observed[keep], 1))
        res = observed - (phase + period * ns)
        center = np.median(res[keep])
        mad = np.median(np.abs(res[keep] - center))
        new = keep & (np.abs(res - center) <= max(0.018, 3.5 * mad))
        if new.sum() < 4:
            break
        keep = new
    down = []
    for off in range(pulses):
        use = keep & ((ns.astype(int) - off) % pulses == 0)
        ix = np.clip(np.searchsorted(t, phase + period * ns[use]), 0, len(t) - 1)
        down.append(float(np.median(scaled[0, ix])) if len(ix) else 0.0)
    offset = int(np.argmax(down))
    return dict(
        bpm=60 / period,
        beat_seconds=period,
        phase_seconds=(phase + offset * period) % (period * pulses),
        cycle_seconds=period * pulses,
        pulses_per_cycle=pulses,
        fit_mad_ms=float(1000 * np.median(np.abs(res[keep] - np.median(res[keep])))),
        fit_beats=int(keep.sum()),
        onset_score=float(max(scores)),
        interval=[start, end],
    )


def analyze(path, bpm=None, pulses=4):
    if type(pulses) is not int or not 1 <= pulses <= 16:
        raise ValueError("Sampler pulses must be a whole number from 1 to 16.")
    if bpm is not None and (not np.isfinite(bpm) or not 20 <= bpm <= 300):
        raise ValueError("Starting BPM must be finite and between 20 and 300.")
    t, e, o = features(path)
    start, end = active_region(t, e)
    duration = float(sf.info(path).duration)
    if end - start < 8:
        raise ValueError("At least eight seconds of usable rhythm are needed.")
    scan = []
    for s in np.arange(start, max(start + 1, end - 15), 40):
        use = (t >= s) & (t < min(s + 30, end))
        scan.extend(recurrence(o[:, use]))
    candidates = {}
    for r in scan:
        for divisor in (1, 2, 3, 4, 6, 8):
            v = 60 * divisor / r["seconds"]
            if 45 <= v <= 180:
                key = round(v * 2) / 2
                candidates[key] = candidates.get(key, 0) + r["score"] / np.sqrt(divisor)
    guesses = sorted(candidates, key=candidates.get, reverse=True)[:8]
    if bpm is not None:
        guesses = [float(bpm)] + [v for v in guesses if abs(v - float(bpm)) > 0.3]
    grids = []
    for v in guesses:
        try:
            grids.append(fit_grid(t, o, v, start, min(end, start + 240), pulses))
        except (ValueError, IndexError):
            continue
    if not grids:
        raise ValueError(
            "No stable grid found. Try a cleaner excerpt or specify --bpm."
        )
    # Onset support ranks candidates; a metrical interpretation still needs review.
    grids.sort(
        key=lambda g: g["onset_score"] / (1 + g["fit_mad_ms"] / 15), reverse=True
    )
    grid = min(grids, key=lambda g: abs(g["bpm"] - float(bpm))) if bpm else grids[0]
    local = []
    for s in np.arange(start, max(start + 1, end - 30), 60):
        try:
            local.append(
                fit_grid(t, o, grid["bpm"], float(s), min(float(s + 40), end), pulses)
            )
        except (ValueError, IndexError):
            pass
    warnings = [
        "Tempo and downbeat are proposals. Check the opening, middle and later sections by listening.",
        "Automatic role names do not identify chorus/charanam lyrics. Set section labels yourself.",
    ]
    if any(
        abs(g["bpm"] / grid["bpm"] - 1) > 0.004 or g["fit_mad_ms"] > 10 for g in local
    ):
        warnings.append(
            "Local drift/phase ambiguity detected. Use a section-specific period/phase; do not force one grid across edits."
        )
    for item in local:
        beat = grid["beat_seconds"]
        a, b = item["interval"]
        mask = (t >= a) & (t < b)
        times = t[mask]
        strength = o[:, mask].sum(0)
        if not len(strength):
            continue
        peaks, _ = find_peaks(strength, distance=max(1, round(beat * FS / HOP * 0.55)))
        peaks = peaks[strength[peaks] >= np.percentile(strength, 90)]
        residual = ((times[peaks] - grid["phase_seconds"] + beat / 2) % beat) - beat / 2
        item["global_grid_offset_ms"] = (
            float(1000 * np.median(residual)) if len(residual) else None
        )
    if any(abs(g.get("global_grid_offset_ms") or 0) > 35 for g in local):
        warnings.append(
            "A local phase discontinuity or edit may be present. Inspect those source times and adjust their pad boundaries independently."
        )
    # 32-band log-mel motif descriptors preserve more timbre detail than 3-band timing alone.
    import librosa

    y, sr = sf.read(path, dtype="float32", always_2d=True)
    y = soxr.resample(y.mean(1), sr, FS)
    mel = np.log1p(
        librosa.feature.melspectrogram(
            y=y, sr=FS, n_fft=1024, hop_length=128, n_mels=32, fmin=35, fmax=5200
        )
        * 100
    )
    mt = librosa.frames_to_time(np.arange(mel.shape[1]), sr=FS, hop_length=128)
    period = grid["cycle_seconds"]
    phase = grid["phase_seconds"]
    rows = []
    flat = []
    for i in range(max(0, int((end - phase) / period))):
        s = phase + i * period
        if s < start - period:
            continue
        q = s + np.arange(96) / 96 * period
        block = np.stack([np.interp(q, mt, v) for v in mel])
        block /= max(float(np.linalg.norm(block)), 1e-9)
        use = (t >= s) & (t < s + period)
        total = o[:, use].sum(0)
        rel = t[use] - s
        rows.append(
            dict(
                index=i,
                start=s,
                level=float(np.sqrt(np.mean(e[:, use] ** 2))),
                last_beat_ratio=float(
                    total[rel >= period - grid["beat_seconds"]].sum()
                    / max(total.sum(), 1e-9)
                ),
            )
        )
        flat.append(block.ravel())
    flat = np.asarray(flat)
    if len(rows) < 6:
        raise ValueError("Too few complete cycles. Choose a longer excerpt.")
    distances = np.sqrt(np.maximum(0, 2 - 2 * flat @ flat.T))
    for k, row in enumerate(rows):
        d = distances[k].copy()
        d[max(0, k - 2) : k + 3] = 99
        near = np.argsort(d)[:4]
        row["nearest"] = [
            dict(index=rows[j]["index"], distance=float(d[j])) for j in near
        ]
        row["novelty"] = float(np.mean(d[near]))
        row["needs_listening_review"] = True
    return dict(
        active_region=[start, end],
        duration_seconds=duration,
        grid=grid,
        tempo_candidates=grids,
        local_grids=local,
        warnings=warnings,
        cycles=rows,
    ), dict(times=t, energy=e, onset=o)


def propose(analysis):
    rows = analysis["cycles"]
    g = analysis["grid"]
    period = g["cycle_seconds"]
    end = analysis["duration_seconds"]
    pads = []

    def add(start, cycles, label, role, mode="Loop"):
        if start < 0 or start + cycles * period > end:
            return None
        n = len(pads) + 1
        pads.append(
            dict(
                number=n,
                label=label,
                section="Unassigned",
                role=role,
                mode=mode,
                source_start=float(start),
                source_cycle_seconds=period,
                cycles=cycles,
            )
        )
        return n

    if 2 * period >= 20:
        raise ValueError(
            "Two cycles would exceed the sampler limit. Choose a smaller pulse grouping or a suitable faster pulse interpretation."
        )
    opening = next(
        r
        for r in rows
        if r["level"] > 0 and r["start"] >= analysis["active_region"][0] - 0.03
    )
    add(opening["start"], 2, "Opening candidate — check first hit", "opening")
    main = min(rows[2:-4] or rows, key=lambda r: r["novelty"])
    add(main["start"], 2, "Recurring main candidate", "main")
    if 4 * period < 20:
        add(main["start"], 4, "Long recurring main", "long_main")
    routes = []
    pairs = []
    choices = sorted(
        rows, key=lambda r: r["last_beat_ratio"] + 0.15 * r["novelty"], reverse=True
    )
    for r in choices:
        s = r["start"]
        if s < analysis["active_region"][0] + 4 * period or s + 4 * period > end:
            continue
        if r["last_beat_ratio"] < 0.30:
            continue
        a = add(s - 2 * period, 2, "Main before proposed fill", "paired_main")
        b = add(
            s,
            1,
            "Phrase-end candidate — audition before using",
            "fill_candidate",
            "One Shot",
        )
        c = add(
            s,
            2,
            "Proposed fill plus natural return",
            "fill_return_candidate",
            "One Shot",
        )
        d = add(s + 2 * period, 2, "Following main", "following_main")
        routes.extend([[a, b], [a, c], [c, d]])
        pairs.append([b, c])
        break
    # Sparse conservative default; no quota, no invented ending.
    col = [
        p["number"]
        for p in pads
        if p["role"]
        in ("paired_main", "fill_return_candidate", "following_main", "fill_candidate")
    ]
    primary = [p["number"] for p in pads if p["number"] not in col]
    columns = [(primary + [0] * 6)[:6], (col + [0] * 6)[:6], ([2] + [0] * 5)]
    demos = {"01_OPENING_TWICE": [1, 1, 2, 2], "02_MAIN_REPEAT": [2, 2, 2]}
    if routes:
        demos["03_MAIN_FILL_RETURN"] = [a, a, c, d, d]
    return pads, columns, routes, pairs, demos
