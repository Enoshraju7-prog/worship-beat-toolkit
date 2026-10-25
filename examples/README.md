# Try the software without publishing a song

The repository includes **no song audio**. `scripts/make_demo_project.py` creates a deterministic, artificial pulse/noise fixture in a job folder for software testing. It is not a worship performance or a recommended musical pack.

```bash
source .venv/bin/activate
python scripts/make_demo_project.py --out jobs/software-demo
worship-beats export jobs/software-demo/project.json --draft
```

This demonstrates reviewable decisions, a three-column layout, repeated-loop demos, native archive packaging and exact file validation without downloading a model. It deliberately bypasses source separation because the fixture is generated for tests.

To exercise the complete **ingest → analyze → propose → export** path using that same declared fixture:

```bash
worship-beats prepare jobs/software-demo/stems/drums.wav \
  --already-drums --job jobs/software-analysis --bpm 120 --pulses 4
worship-beats export jobs/software-analysis/project.json --draft
```

Open the resulting project's actual `project.json` to see all fields with generated hashes. The following shortened snippet shows only the cut representation:

```json
{
  "target_bpm": 120.0,
  "pulses_per_cycle": 4,
  "notation_meter": null,
  "pads": [
    {
      "number": 1,
      "label": "Software-test main",
      "section": "Generated fixture",
      "role": "main",
      "mode": "Loop",
      "source_start": 4.02,
      "source_cycle_seconds": 2.0,
      "cycles": 2
    }
  ]
}
```

This snippet is an explanation, not a complete project. The generator creates a complete valid project including source references, hashes, layout and routes. Do not commit the resulting job, audio, exports or private source metadata.
