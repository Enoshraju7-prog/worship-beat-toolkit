#!/usr/bin/env python3
"""Generate an explicitly artificial software fixture, never a song substitute."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from worship_beats.audio import sha256
from worship_beats.project import save_json


def make_demo(folder: Path) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "stems").mkdir()
    sr = 44100
    audio = np.zeros((sr * 36, 2), np.float32)
    rng = np.random.default_rng(42)
    # Repeat a fixed two-second pattern; retain a small known pickup offset.
    motif = rng.normal(0, 1, 1200).astype(np.float32)
    motif *= np.exp(-np.arange(1200) / 150) * 0.12
    for i, time in enumerate(np.arange(0.02, 36, 0.25)):
        start = round(time * sr)
        length = min(len(motif), len(audio) - start)
        audio[start : start + length] += motif[:length, None] * (2 if i % 8 == 0 else 1)
    stem = folder / "stems/drums.wav"
    sf.write(stem, audio, sr, subtype="FLOAT")
    cuts = [
        (1, 4.02, 2, "Loop", "main"),
        (2, 8.02, 1, "One Shot", "fill"),
        (3, 8.02, 2, "One Shot", "fill_return"),
        (4, 12.02, 2, "Loop", "following_main"),
    ]
    pads = [
        dict(
            number=n,
            label="Software-test " + role,
            section="Generated fixture",
            role=role,
            mode=mode,
            source_start=start,
            source_cycle_seconds=2.0,
            cycles=cycles,
        )
        for n, start, cycles, mode, role in cuts
    ]
    digest = sha256(stem)
    project = dict(
        schema_version=1,
        name="GENERATED SOFTWARE FIXTURE - NOT A SONG",
        mode="drums",
        source=dict(
            input="generated-software-fixture",
            original="stems/drums.wav",
            master="stems/drums.wav",
            requested_start=0,
            requested_end=None,
            duration_seconds=36,
            master_sha256=digest,
            original_sha256=digest,
        ),
        stem="stems/drums.wav",
        stem_sha256=digest,
        target_bpm=120.0,
        pulses_per_cycle=4,
        notation_meter=None,
        grid=dict(phase_seconds=0.02, cycle_seconds=2.0),
        separation=dict(already_drums=True, generated_fixture=True),
        pads=pads,
        columns=[[1, 3, 4, 2, 0, 0], [1, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0]],
        routes=[[1, 2], [1, 3], [3, 4]],
        fill_pairs=[[2, 3]],
        demos={"01_OPENING_TWICE": [1, 1, 3, 4], "02_MAIN_REPEAT": [1, 1, 1]},
        sections=[],
        review={},
    )
    path = folder / "project.json"
    save_json(path, project)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    print(make_demo(parser.parse_args().out))
