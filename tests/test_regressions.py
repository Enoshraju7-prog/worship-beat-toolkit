"""Behavioral regression checks for cached jobs, approval and timing corrections."""

from __future__ import annotations

import json

import numpy as np
import pytest
import soundfile as sf

from worship_beats.audio import ingest
from worship_beats.analysis import analyze, fit_grid
from worship_beats.project import approve, is_approved, validate_project
from worship_beats.render import export_project


@pytest.mark.parametrize(
    "field,value",
    [
        ("stem", "stems/another.wav"),
        ("stem_sha256", "changed"),
        ("cut_lead_seconds", 0.04),
        ("notation_meter", "6/8"),
    ],
)
def test_audio_identity_and_cut_settings_invalidate_review(project, field, value):
    p, _ = project
    approve(p, "Listened to declared software fixture.")
    p[field] = value
    assert not is_approved(p)


def test_fractional_pulses_are_rejected(project):
    p, _ = project
    p["pulses_per_cycle"] = 4.5
    with pytest.raises(ValueError, match="whole number"):
        validate_project(p)


def test_retry_decode_and_verify_retained_original(tmp_path):
    original = tmp_path / "input.wav"
    sf.write(original, np.zeros((44100 * 3, 2), np.float32), 44100)
    job = tmp_path / "job"
    (job / "source").mkdir(parents=True)
    (job / "source/master.partial.wav").write_bytes(b"interrupted decode")
    first = ingest(str(original), job, 0, 2, progress=lambda _: None)
    assert sf.info(job / "source/master.wav").frames == 88200
    assert ingest(str(original), job, 0, 2, progress=lambda _: None) == first
    (job / first["original"]).write_bytes(b"changed source")
    with pytest.raises(ValueError, match="original changed"):
        ingest(str(original), job, 0, 2, progress=lambda _: None)


def test_draft_does_not_claim_listening_approval(project, tmp_path):
    p, path = project
    approve(p, "Listened to synthetic fixture only.")
    out = export_project(p, path, tmp_path / "draft", draft=True)
    report = json.loads((out / "validation.json").read_text())
    assert report["draft"] and not report["human_listening_approved"]


def test_retimed_source_adjacent_phrase_exports(project, tmp_path):
    p, path = project
    p["target_bpm"] = 117.0
    out = export_project(p, path, tmp_path / "retimed", draft=True)
    manifest = json.loads((out / "manifest.json").read_text())
    by_number = {item["number"]: item for item in manifest}
    assert by_number[1]["rendered_bounds"][1] == by_number[3]["rendered_bounds"][0]
    assert by_number[3]["rendered_bounds"][1] == by_number[4]["rendered_bounds"][0]
    assert by_number[1]["retiming"]["method"] == "pitch-preserving atempo"
    assert by_number[1]["frames"] == 2 * round(44100 * 60 / 117 * 4)


def test_local_grids_follow_a_tempo_change():
    t = np.arange(0, 90, 0.005)
    onset = np.zeros((3, len(t)))
    for time in np.concatenate(
        (np.arange(0.173, 40, 0.5), np.arange(40.173, 90, 60 / 121))
    ):
        onset[:, np.argmin(abs(t - time))] = [3, 1, 1]
    early = fit_grid(t, onset, 120, 1, 35, 4)
    late = fit_grid(t, onset, 121, 45, 85, 4)
    assert abs(early["bpm"] - 120) < 0.1
    assert abs(late["bpm"] - 121) < 0.1


def test_local_grids_reveal_an_edited_phase():
    t = np.arange(0, 80, 0.005)
    onset = np.zeros((3, len(t)))
    for time in np.concatenate((np.arange(0.17, 40, 0.5), np.arange(40.31, 80, 0.5))):
        onset[:, np.argmin(abs(t - time))] = [3, 1, 1]
    early = fit_grid(t, onset, 120, 1, 35, 4)
    late = fit_grid(t, onset, 120, 45, 75, 4)
    offset = (late["phase_seconds"] - early["phase_seconds"]) % 0.5
    assert abs(offset - 0.14) < 0.03


@pytest.mark.parametrize("bpm,pulses", [(float("nan"), 4), (120, 0), (120, 4.5)])
def test_analysis_rejects_invalid_interpretations_before_loading_audio(bpm, pulses):
    with pytest.raises(ValueError):
        analyze("does-not-exist.wav", bpm=bpm, pulses=pulses)
