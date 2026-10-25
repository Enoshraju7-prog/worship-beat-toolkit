"""Checksum-pinned specialist models, loaded lazily; no model weights in Git."""

from __future__ import annotations
from pathlib import Path
import json
import os
from importlib.metadata import version
import urllib.request
import numpy as np
import soundfile as sf
from .audio import sha256
from .project import save_json

MODELS = {
    "drums": (
        "f7e0c4bc-ba3fe64a.th",
        "ba3fe64ae8ef66ac9a4857222ce48efbdc5eb3ad375cb79dd13debee5aaa4066",
    ),
    "instrumental": (
        "04573f0d-f3cf25b2.th",
        "f3cf25b222c4eed7cd49dd8b2c9597d50c18bd154090f7b919cfa5f93cf22c49",
    ),
}


def model_path(mode: str, cache: Path | None = None, progress=print) -> Path:
    name, digest = MODELS[mode]
    root = Path(
        cache
        or os.environ.get(
            "WORSHIP_BEATS_MODEL_CACHE", Path.home() / ".cache/worship-beats/models"
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if not path.exists():
        # Reuse an existing official Torch cache, without depending on its presence.
        existing = Path.home() / ".cache/torch/hub/checkpoints" / name
        if existing.is_file() and sha256(existing) == digest:
            return existing
        progress("Downloading checksum-pinned official separation model (~84 MB).")
        partial = path.with_suffix(".download")
        urllib.request.urlretrieve(
            "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/" + name, partial
        )
        if sha256(partial) != digest:
            raise ValueError(
                "Model checksum failed; untrusted checkpoint will NOT be loaded."
            )
        partial.replace(path)
    if sha256(path) != digest:
        raise ValueError(
            "Model checksum failed; remove the damaged cache entry and retry."
        )
    return path


def separate(
    master: Path, job: Path, mode="drums", shifts=1, threads=8, progress=print
) -> Path:
    if mode not in MODELS:
        raise ValueError("Mode must be drums or instrumental.")
    folder = Path(job) / "stems"
    folder.mkdir(exist_ok=True)
    target = folder / (mode + ".wav")
    marker = folder / (mode + ".json")
    key = dict(
        master_sha256=sha256(master),
        model_sha256=MODELS[mode][1],
        shifts=shifts,
        overlap=0.5,
        segment=7.8,
    )
    if marker.exists() and target.exists():
        previous = json.loads(marker.read_text())
        if previous.get("parameters") == key and previous.get(
            "output_sha256"
        ) == sha256(target):
            progress("Reusing verified complete separation.")
            return target
    try:
        import torch
        from demucs.states import load_model
        from demucs.apply import apply_model
    except ImportError as exc:
        raise RuntimeError(
            'Install the separation extra: python -m pip install ".[separation]"'
        ) from exc
    checkpoint = model_path(mode, progress=progress)
    progress(
        f"Separating {mode}: {shifts} shift(s), CPU, 50% overlap. Detailed progress appears in Terminal."
    )
    # PyTorch pickle loading is permitted ONLY for the exact verified official digest above.
    previous_load_setting = os.environ.get("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD")
    os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    try:
        model = load_model(checkpoint).eval()
    finally:
        if previous_load_setting is None:
            os.environ.pop("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", None)
        else:
            os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = previous_load_setting
    torch.manual_seed(20261023)
    torch.set_num_threads(max(1, threads))
    y, sr = sf.read(master, dtype="float32", always_2d=True)
    if sr != 44100 or y.shape[1] != 2:
        raise ValueError("Separation requires the decoded stereo 44.1 kHz master.")
    x = torch.from_numpy(y.T.copy())
    ref = x.mean(0)
    mean = ref.mean()
    std = ref.std()
    if float(std) < 1e-8:
        raise ValueError("Source is silent.")
    with torch.inference_mode():
        result = apply_model(
            model,
            ((x - mean) / std)[None],
            device="cpu",
            shifts=shifts,
            overlap=0.5,
            segment=7.8,
            progress=True,
        )[0]
    name = "drums" if mode == "drums" else "vocals"
    isolated = (result[model.sources.index(name)] * std + mean).numpy().T
    if mode == "instrumental":
        sf.write(folder / "vocals_estimate.wav", isolated, sr, subtype="FLOAT")
        isolated = y - isolated
    if not np.isfinite(isolated).all():
        raise ValueError("Non-finite separation output.")
    sf.write(target, isolated, sr, subtype="FLOAT")
    save_json(
        marker,
        dict(
            parameters=key,
            output_sha256=sha256(target),
            listening_approved=False,
            versions={
                name: version(name) for name in ("demucs", "torch", "torchaudio")
            },
            checkpoint=checkpoint.name,
        ),
    )
    return target
