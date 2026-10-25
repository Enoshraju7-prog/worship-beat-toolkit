from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


def launch_app(project=None):
    if not importlib.util.find_spec("streamlit"):
        raise RuntimeError('Install the UI extra: python -m pip install ".[app]"')
    script = Path(__file__).with_name("app.py")
    args = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script),
        "--server.address=127.0.0.1",
        "--browser.gatherUsageStats=false",
    ]
    if project:
        args += ["--", str(Path(project).resolve())]
    return subprocess.call(args)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Local review-first worship drum loops. No Codex/API account required."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "doctor", help="Check runtime and optional capabilities without downloading."
    )
    p = sub.add_parser(
        "prepare", help="Retain source, separate and propose editable pads."
    )
    p.add_argument("source")
    p.add_argument("--job", required=True, type=Path)
    p.add_argument("--start", default="0")
    p.add_argument("--end")
    p.add_argument("--bpm", type=float)
    p.add_argument("--pulses", type=int, default=4)
    p.add_argument("--mode", choices=["drums", "instrumental"], default="drums")
    p.add_argument("--already-drums", action="store_true")
    p.add_argument("--shifts", type=int, choices=[1, 2, 3, 4], default=1)
    p.add_argument("--threads", type=int, default=8)
    p = sub.add_parser(
        "review", help="Open editor, or approve after your own listening review."
    )
    p.add_argument("project", type=Path)
    p.add_argument("--approve", action="store_true")
    p.add_argument("--note", default="")
    p = sub.add_parser("export")
    p.add_argument("project", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--draft", action="store_true")
    p = sub.add_parser("validate")
    p.add_argument("pack", type=Path)
    sub.add_parser("app", help="Launch the localhost-only app.")
    a = parser.parse_args(argv)
    try:
        if a.command == "doctor":
            report = dict(
                python=sys.version.split()[0],
                ffmpeg=shutil.which("ffmpeg"),
                modules={
                    m: bool(importlib.util.find_spec(m))
                    for m in (
                        "numpy",
                        "scipy",
                        "soundfile",
                        "soxr",
                        "librosa",
                        "yt_dlp",
                        "torch",
                        "demucs",
                        "streamlit",
                    )
                },
                note="CPU baseline. Device/app musical validation is separate. No paid API is used.",
            )
            required = ("numpy", "scipy", "soundfile", "soxr", "librosa", "yt_dlp")
            report["core_ready"] = bool(report["ffmpeg"]) and all(
                report["modules"][m] for m in required
            )
            print(json.dumps(report, indent=2))
            return 0 if report["core_ready"] else 1
        if a.command == "prepare":
            from .pipeline import prepare
            from .audio import time_seconds

            print(
                prepare(
                    a.source,
                    a.job,
                    time_seconds(a.start),
                    time_seconds(a.end),
                    a.bpm,
                    a.pulses,
                    a.mode,
                    a.already_drums,
                    a.shifts,
                    a.threads,
                )
            )
            return 0
        if a.command == "review":
            if not a.approve:
                return launch_app(a.project)
            from .project import load_project, approve, save_json

            p = load_project(a.project)
            approve(p, a.note)
            save_json(a.project, p)
            print("Approved exact selection. Subsequent edits invalidate approval.")
            return 0
        if a.command == "export":
            from .project import load_project
            from .render import export_project

            print(export_project(load_project(a.project), a.project, a.out, a.draft))
            return 0
        if a.command == "validate":
            from .validate import validate_pack

            print(json.dumps(validate_pack(a.pack), indent=2))
            return 0
        return launch_app()
    except (
        ValueError,
        RuntimeError,
        FileNotFoundError,
        FileExistsError,
        subprocess.CalledProcessError,
    ) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
