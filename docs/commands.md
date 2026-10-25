# Command reference

Activate the environment first with `source .venv/bin/activate`, or prefix every command with `.venv/bin/`.

| Command | What it does |
| --- | --- |
| `worship-beats doctor` | Reports runtime, FFmpeg and optional module availability without downloading a model |
| `worship-beats prepare SOURCE --job FOLDER` | Retains source, separates, analyzes and saves a draft project |
| `worship-beats review PROJECT` | Opens the local editor for that project |
| `worship-beats review PROJECT --approve --note TEXT` | Records your listening approval for the exact selection |
| `worship-beats export PROJECT` | Exports an approved project to a new timestamped folder |
| `worship-beats export PROJECT --draft` | Exports an explicitly unapproved audition pack |
| `worship-beats validate PACK_FOLDER` | Checks an exported pack's audio, hashes and native archive |
| `worship-beats app` | Opens the localhost app |

Use `worship-beats --help` or `worship-beats prepare --help` for the authoritative flags.

## Preparation options

| Option | Default | Meaning |
| --- | --- | --- |
| `--job` | Required | New job folder, or matching interrupted job with no project yet |
| `--start` | `0` | Excerpt start in the original source |
| `--end` | Source end | Excerpt end in the original source |
| `--bpm` | Propose | Starting pulse interpretation; refined grid still needs review |
| `--pulses` | `4` | Sampler pulses per cycle, distinct from notation meter |
| `--mode` | `drums` | `instrumental` subtracts estimated vocals from the master |
| `--already-drums` | Off | Explicitly skip separation for an existing drum-only source |
| `--shifts` | `1` | 1–4 separation averaging passes; more takes longer |
| `--threads` | `8` | CPU threads used by separation |

`--already-drums` is for an actual existing drum stem or the declared generated software fixture. It is not a way to claim that an ordinary full mix was separated. It cannot be used with instrumental mode.

```bash
worship-beats prepare '/path/to/drums.wav' --already-drums \
  --job jobs/from-stem --bpm 120 --pulses 4
```

## Export options and errors

`--out FOLDER` selects a new destination. Existing destinations are rejected. `--draft` bypasses listening approval while marking the result as a draft. A draft remains unapproved even if the underlying saved project previously had an approval record.

Exit code 0 means the operation completed. Code 1 is used by `doctor` for unavailable core capabilities. Code 2 reports a caught input or processing error. Unanticipated programming errors can produce a Python traceback; preserve it when filing an issue, after removing personal paths or private source links.

There is no transposition command in this release. [The transposition guide](transposition.md) explains the separate FFmpeg operation used for key changes.
