import numpy as np
import pytest
import soundfile as sf
from worship_beats.audio import sha256
from worship_beats.project import save_json


@pytest.fixture
def project(tmp_path):
    folder = tmp_path / "stems"
    folder.mkdir()
    sr = 44100
    y = np.zeros((sr * 22, 2), np.float32)
    rng = np.random.default_rng(4)
    for t in np.arange(0.02, 22, 0.25):
        a = round(t * sr)
        n = min(800, len(y) - a)
        y[a : a + n] = (rng.normal(size=n) * np.exp(-np.arange(n) / 160) * 0.12)[
            :, None
        ]
    f = folder / "drums.wav"
    sf.write(f, y, sr, subtype="FLOAT")
    pads = []
    for n, s, b, mode in [
        (1, 4.02, 2, "Loop"),
        (2, 8.02, 1, "One Shot"),
        (3, 8.02, 2, "One Shot"),
        (4, 12.02, 2, "Loop"),
    ]:
        pads.append(
            dict(
                number=n,
                label="Test only",
                section="Unassigned",
                role="test",
                mode=mode,
                source_start=s,
                source_cycle_seconds=2.0,
                cycles=b,
            )
        )
    p = dict(
        schema_version=1,
        name="Synthetic software test only",
        mode="drums",
        source=dict(requested_start=0, duration_seconds=22, master_sha256=sha256(f)),
        stem="stems/drums.wav",
        stem_sha256=sha256(f),
        target_bpm=120.0,
        pulses_per_cycle=4,
        grid=dict(phase_seconds=0.02, cycle_seconds=2),
        pads=pads,
        columns=[[1, 3, 4, 2, 0, 0], [1, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0]],
        routes=[[1, 2], [1, 3], [3, 4]],
        fill_pairs=[[2, 3]],
        demos={"TEST_MAIN_FILL_RETURN": [1, 1, 3, 4]},
        sections=[],
        review={},
    )
    path = tmp_path / "project.json"
    save_json(path, p)
    return p, path
