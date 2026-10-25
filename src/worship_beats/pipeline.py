from pathlib import Path
import shutil
import numpy as np
from .audio import ingest, sha256
from .separation import separate, MODELS
from .analysis import analyze, propose
from .project import save_json, SCHEMA_VERSION


def prepare(
    source,
    job,
    start=0.0,
    end=None,
    bpm=None,
    pulses=4,
    mode="drums",
    already_drums=False,
    shifts=1,
    threads=8,
    progress=print,
):
    job = Path(job).expanduser().resolve()
    job.mkdir(parents=True, exist_ok=True)
    project_file = job / "project.json"
    if project_file.exists():
        raise FileExistsError(
            "Project already exists. Review it or choose a new job; existing decisions are not overwritten."
        )
    source_info = ingest(source, job, start, end, progress)
    master = job / "source/master.wav"
    if already_drums:
        if mode != "drums":
            raise ValueError(
                "--already-drums cannot be combined with instrumental mode."
            )
        folder = job / "stems"
        folder.mkdir(exist_ok=True)
        stem = folder / "drums.wav"
        shutil.copy2(master, stem)
        progress(
            "Using explicitly declared already-isolated drums. No separation quality is claimed."
        )
    else:
        stem = separate(master, job, mode, shifts, threads, progress)
    progress("Analyzing timing, recurring motifs, drift and candidate transitions.")
    analysis, features = analyze(stem, bpm, pulses)
    save_json(job / "analysis.json", analysis)
    np.savez_compressed(job / "features.npz", **features)
    pads, columns, routes, pairs, demos = propose(analysis)
    p = dict(
        schema_version=SCHEMA_VERSION,
        name=source_info["title"],
        source=source_info,
        mode=mode,
        stem=str(stem.relative_to(job)),
        stem_sha256=sha256(stem),
        separation=dict(
            already_drums=already_drums,
            model_sha256=None if already_drums else MODELS[mode][1],
            shifts=shifts,
        ),
        target_bpm=round(analysis["grid"]["bpm"], 1),
        pulses_per_cycle=pulses,
        notation_meter=None,
        grid=analysis["grid"],
        analysis_file="analysis.json",
        sections=[],
        pads=pads,
        columns=columns,
        routes=routes,
        fill_pairs=pairs,
        demos=demos,
        review={},
    )
    save_json(project_file, p)
    progress("Draft ready. Listen and edit before approving/exporting.")
    return project_file
