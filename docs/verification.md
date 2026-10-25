# Verification: what each check establishes

This release records file correctness, musical review and device behavior separately. No single green test establishes all three.

## Software acceptance

The automated suite covers canonical sample lengths, finite PCM, edges/peaks, decoding, manifest hashes, native asset references, three-column placement, corrupt stems, invalid selections, review invalidation, interrupted decode retry, pickup phase, multiple pulse groupings, tempo changes, phase edits and source-adjacent retiming. Generated fixtures are used for reproducible software checks, not as substitutes for song extraction.

The local app tests open the actual Streamlit script and build an audition pack through its draft-export control. The command-line fixture walkthrough exercises preparation from an explicitly declared already-separated source. A separate short real-audio inference check tests the checkpoint/runtime loader; it does not establish musical quality for an entire recording.

## Local release results — 25 October 2026

Environment: macOS Apple Silicon, CPython 3.13.9, FFmpeg available on PATH. Exact Python dependency versions are in `requirements/macos-arm64-py313.txt`.

| Check | Result |
| --- | --- |
| Isolated normal package installation, with app and separation extras | Passed; `pip check` reports no broken requirements |
| Automated suite including the actual Streamlit app | **33 passed** |
| Installed CLI `doctor` | Core ready; optional app and separation modules found |
| Generated project → draft export | Passed |
| Generated stem → prepare/analyze/propose → draft export | Passed using `--already-drums`; no claim of neural extraction for a generated fixture |
| Real eight-second audio → verified drum-specialist checkpoint → CPU separation | Passed; resulting stem retained only in the local test workspace |
| Wheel and source distribution build | Passed |
| Local Markdown links and skill frontmatter | Passed |

The eight-second model check uses actual supplied audio, not generated pulses, and verifies runtime compatibility. It is a short integration check, not full-song listening approval. Model weights were reused only after their full checksum was verified.

The setup script installs the package normally rather than in editable mode. During testing, this Mac's Python skipped the editable installation's hidden `.pth` file; normal wheel installation avoids that dependency on startup path-file handling.

## What remains a listening/device decision

| Claim | Status / evidence required |
| --- | --- |
| Correct pallavi/charanam labels for a new song | Human must check against that performance |
| Clean separation and appropriate fills | Human must hear the actual stem and repeated/transition demos |
| Every possible compound rhythm or improvised performance is resolved | Not claimed; automatic proposals are conservative |
| Desktop Remixlive import, playback, export and re-import | Pending for this toolkit release |
| iPhone/iPad import, playback and sharing | Pending; test the actual device |
| Intel Mac hardware execution | Pending; compatibility constraints are supplied |
| Perfect isolation or studio-quality reconstruction | Not claimed |

## Reproduce the offline checks

```bash
python -m pip install '.[app,dev]'
pytest -q
python -m build
python scripts/make_demo_project.py --out jobs/software-demo
worship-beats export jobs/software-demo/project.json --draft
worship-beats prepare jobs/software-demo/stems/drums.wav \
  --already-drums --job jobs/software-analysis --bpm 120 --pulses 4
worship-beats export jobs/software-analysis/project.json --draft
```

Lightweight GitHub Actions tests run core checks on Python 3.11 and 3.13, plus a Python 3.13 app job, without downloading neural models or songs. Installation itself needs network access; the tests use local generated fixtures.

Keep `validation.json` with each pack. Its technical `passed` field is separate from `human_listening_approved`, `actual_app_round_trip_verified` and `mobile_verified`. A draft export never claims listening approval.
