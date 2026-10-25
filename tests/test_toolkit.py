import json
import zipfile
import numpy as np
import pytest
from worship_beats.audio import time_seconds
from worship_beats.project import (
    approve,
    is_approved,
    validate_project,
    resolve_asset,
)
from worship_beats.analysis import fit_grid, recurrence, active_region
from worship_beats.render import export_project
from worship_beats.validate import validate_pack
from worship_beats.remixlive import validate_native


def test_time():
    assert time_seconds("1:02:03.5") == 3723.5
    for value in ("-1", "nan", "1:2:3:4"):
        with pytest.raises(ValueError):
            time_seconds(value)


def test_review_invalidated(project):
    p, _ = project
    approve(p, "Auditioned synthetic software fixture, not a real song.")
    assert is_approved(p)
    p["pads"][0]["source_start"] += 0.005
    assert not is_approved(p)


def test_export_round_trip(project, tmp_path):
    p, path = project
    with pytest.raises(ValueError, match="approve"):
        export_project(p, path)
    out = export_project(p, path, tmp_path / "out", draft=True)
    assert validate_pack(out)["passed"]
    with zipfile.ZipFile(out / "WORSHIP_BEATS.rmxl") as z:
        assert "samples/Song_8x6.song" in z.namelist()
        session = json.loads(z.read("8x6.json"))
        pads = next(g for g in session["grids"] if g["grid_type"] == 0)["pads"]
        assert {v["col"] for v in pads if v["sampleName"]} == {0, 1, 2}
    with pytest.raises(FileExistsError):
        export_project(p, path, out, draft=True)


def test_bad_route_and_fill(project, tmp_path):
    p, path = project
    p["pads"][1]["source_start"] += 0.02
    with pytest.raises(ValueError, match="route"):
        export_project(p, path, tmp_path / "bad", draft=True)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["pads"][0].update(source_start=-1),
        lambda p: p["pads"][0].update(cycles=100),
        lambda p: p["pads"][0].update(source_cycle_seconds=float("nan")),
        lambda p: p.update(columns=[[1], [2], [3]]),
        lambda p: p["pads"][0].update(source_start=21),
    ],
)
def test_invalid(project, change):
    p, _ = project
    change(p)
    with pytest.raises(ValueError):
        validate_project(p)


@pytest.mark.parametrize("pulses", [3, 4, 6, 7])
def test_pulse_groups_and_pickup(pulses):
    t = np.arange(0, 40, 0.005)
    o = np.zeros((3, len(t)))
    for i, s in enumerate(np.arange(0.173, 40, 0.5)):
        j = np.argmin(abs(t - s))
        o[:, j] = [3 if i % pulses == 0 else 0.5, 1, 1]
    g = fit_grid(t, o, 120, 1, 38, pulses)
    assert abs(g["bpm"] - 120) < 0.05 and abs(g["cycle_seconds"] - 0.5 * pulses) < 0.003
    assert (
        min(
            abs(g["phase_seconds"] - 0.173),
            abs(g["phase_seconds"] - 0.173 - 0.5 * pulses),
        )
        < 0.03
    )


def test_silence():
    with pytest.raises(ValueError, match="silent"):
        active_region(np.arange(100), np.zeros((3, 100)))


def test_recurrence_half_double():
    o = np.zeros((3, 8000))
    o[:, ::100] = 1
    r = recurrence(o)
    assert r and any(abs(v["seconds"] - 100 * 64 / 11025) < 0.01 for v in r)


def test_path_escape(project):
    _, path = project
    with pytest.raises(ValueError):
        resolve_asset(path, "../outside.wav")


def test_missing_native_asset(project, tmp_path):
    p, path = project
    out = export_project(p, path, tmp_path / "good", draft=True)
    with (
        zipfile.ZipFile(out / "WORSHIP_BEATS.rmxl") as src,
        zipfile.ZipFile(tmp_path / "bad.rmxl", "w") as dst,
    ):
        for n in src.namelist():
            if n != "samples/Song_8x6.song":
                dst.writestr(n, src.read(n))
    with pytest.raises(ValueError, match="Missing referenced"):
        validate_native(tmp_path / "bad.rmxl")


def test_stem_corruption(project, tmp_path):
    p, path = project
    (path.parent / "stems/drums.wav").write_bytes(b"not audio")
    with pytest.raises(ValueError, match="changed"):
        export_project(p, path, tmp_path / "bad", draft=True)
