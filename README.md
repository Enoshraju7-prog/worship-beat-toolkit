# Worship Beat Toolkit

Turn a song you supply into **drums-only loops and fills for live worship**. Run locally on your computer, listen to the proposed cuts, adjust them, and export numbered WAV pads plus a self-contained Remixlive project.

No Codex, paid AI API, subscription, or cloud audio upload is required. Internet is needed for installation, the first model download, and optional YouTube downloads. Once dependencies and a model are cached, local-file processing can run offline.

**Prepare → listen and adjust → export.** Automatic BPM, first-beat and fill suggestions need your ears. The program cannot reliably infer pallavi, charanam or lyric cues from drums alone. It does not promise a perfect studio stem from a mixed live recording.

## Start here if this is new to you

You have a recording containing singing and instruments. You want buttons on your phone that play **the real drum groove from that recording**, including a fill when a sung phrase ends. This toolkit makes those audio pieces and a project that arranges them into buttons. It keeps the full original and the full separated drums so you can revise the cuts later.

| Term | Simple meaning |
| --- | --- |
| Stem | An estimated separated part of the recording, such as mostly drums |
| Loop | A short audio piece that repeats |
| Fill | A short drum change, often near the end of a sung phrase |
| Return | The crash/groove immediately after the fill |
| Pad | A sampler button that plays one audio piece |
| BPM | The speed of the pulses you count along with the music |
| Draft | A proposal you still need to hear and correct |

```mermaid
flowchart LR
    A["Your song"] --> B["Separate drums"]
    B --> C["Suggest loops and fills"]
    C --> D["You listen and correct"]
    D --> E["Export numbered pads"]
    E --> F["Play in Remixlive"]
```

The **local app** gives you buttons, audio players and editable tables. The **command line** runs the same engine using typed commands. You can use the app for everyday work; commands are also documented for repeatable processing and troubleshooting.

Read in this order:

1. **[Installation and first song](#1-install-on-a-mac)** — get the app running.
2. **[Picture-by-picture architecture](docs/architecture.md)** — follow the song, files and pad handoffs.
3. **[Listening and corrections](#3-listen-and-correct)** — understand what needs your judgment.
4. **[Export and import](#6-export-a-pack)** — move the reviewed result into the sampler.
5. **[Troubleshooting](docs/troubleshooting.md)** — start from what you hear or see.

If you have never used Terminal, open the macOS app named **Terminal**, paste one command block at a time, and wait for it to finish before the next. Text such as `/path/to/song.m4a` is a placeholder: replace it with your real file path, keeping the quotes if the path contains spaces. You can drag a file from Finder into Terminal to insert its path.

## 1. Install on a Mac

Install [Homebrew](https://brew.sh/) if needed. Open Terminal, then:

```bash
git clone https://github.com/Enoshraju7-prog/worship-beat-toolkit.git
cd worship-beat-toolkit
bash scripts/setup_mac.sh
```

The script creates `.venv` inside this folder and installs FFmpeg, the processing engine, the local app and separation dependencies. It uses Python 3.13 on Apple Silicon and Python 3.11 on Intel. CPU processing is the baseline. Installation may take several minutes and separation may take longer than the song's playback duration.

After setup, double-click **Launch.command**, or run:

```bash
.venv/bin/worship-beats app
```

The app runs at `http://127.0.0.1:8501`. Keep Terminal open. Press Control-C in Terminal to stop it. Keep this folder together; do not move only the launcher.

The Apple Silicon Python 3.13 environment is covered by the recorded release checks. The Intel setup uses compatible older Torch pins; it has not been executed on Intel hardware. See [verification](docs/verification.md) for the exact boundaries of testing.

### Manual installation / other systems

With Python 3.11–3.13, FFmpeg on PATH, and libsndfile available:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install '.[app,separation,dev]'
worship-beats doctor
```

Use `-c requirements/macos-arm64-py313.txt` for the pinned Apple Silicon environment, or `-c requirements/macos-intel-py311.txt` for the Intel compatibility constraints. Do not apply one platform's constraints to the other. Manual Linux installation is exercised by lightweight CI; the Mac launcher is macOS-specific.

## 2. Prepare your first song

In the app, expand **Prepare a new song**. Paste a YouTube link, enter a local audio/video path, or upload a file. Choose a new job folder, such as `jobs/my-song`. Leave mode as **drums**. Leave starting BPM at 0 to request proposals. Press **Prepare draft**.

The program preserves the original, decodes a stereo 44.1 kHz working master, separates the complete drum stem, analyzes the rhythm, and saves editable decisions. Watch Terminal for detailed separation progress.

For the command line:

```bash
source .venv/bin/activate
worship-beats prepare '/path/to/song.m4a' --job jobs/my-song
```

For YouTube, replace the example URL with the performance you are authorized to use:

```bash
worship-beats prepare 'https://www.youtube.com/watch?v=VIDEO_ID' --job jobs/my-song
```

Only YouTube URLs are accepted directly. For other services, supply an accessible local file. No browser cookies are collected. If a download is unavailable, use your own authorized local copy; see [troubleshooting](docs/troubleshooting.md).

### Work on a timestamp excerpt

```bash
worship-beats prepare '/path/to/long-service.mp4' \
  --job jobs/song-excerpt --start 17:25 --end 30:32 --bpm 97
```

Times accept seconds, `mm:ss` or `hh:mm:ss`. End is an absolute time in the original source. Pad source boundaries in `project.json` are relative to the excerpt; exported source timestamps include the excerpt's starting offset.

### Pulse grouping is a musical choice

The default sampler cycle is four pulses. That is **not** a claim that every song is in 4/4. For a suitable grouping:

```bash
worship-beats prepare '/path/to/song.wav' --job jobs/compound --bpm 90 --pulses 6
```

Decide what your BPM counts before selecting 3, 4, 6, 7 or another pulse grouping. Half-time, double-time and 2:3 interpretations can all appear plausible. Count along over multiple phrases and compare timing candidates. Keep `notation_meter` separate from `pulses_per_cycle`.

## 3. Listen and correct

```bash
worship-beats review jobs/my-song/project.json
```

1. Hear the source and the separated stem. Check for vocal or keyboard leakage.
2. Inspect tempo candidates and local timing diagnostics. Listen at the beginning, middle and end. A tempo change or edit may need a local cycle period.
3. Check the first audible repeated motif independently. A later, cleaner groove may have a different opening feel. Listen for pickups and rotated patterns.
4. Use the editable pad table to change `source_start`, `source_cycle_seconds`, whole `cycles`, `section`, `label`, `role` and `mode`. Names are proposals; a drum cluster does not establish a lyric section.
5. Build a draft and audition repeated pads and main → fill → return demos. Do not judge a loop from a single playback.
6. Correct boundaries and remove unhelpful duplicates. Keep the main, its fill and its natural return from adjacent source material when possible.
7. Save edits, rebuild previews and listen again before approving.

Changing the analysis phase alone does not move existing pad cuts. Use **Shift all existing pad starts** or edit each actual source start. Changing project BPM changes output timing, while each pad's source cycle period identifies the performance's original timing.

For a source at 64 BPM exported at 63 BPM, the engine processes the timing family together, compensates measured transient offset where supported, and cuts canonical sample lengths. It does not stretch every small piece independently. Very small clock corrections use high-quality resampling and can introduce a correspondingly tiny pitch change; larger corrections use FFmpeg's pitch-preserving `atempo`.

Approval is saved against the exact selection. Changing selected boundaries, layout, timing, source identity or stem identity invalidates it. **Approval is a statement you make after listening**, not a result inferred from software tests.

## 4. Understand mains, fillers and returns

| Pad type | Typical length | Playback | Purpose |
| --- | --- | --- | --- |
| Main | 2 cycles | Loop | Continue under singing |
| Long main | 4 cycles, when under 20 seconds | Loop | Retain natural variation |
| Short fill | 1 cycle | One Shot | Replace a main at a phrase ending |
| Fill + return | 2 cycles | One Shot | Keep the original fill and following return together |
| Following main | 2 cycles | Loop | Continue after that return |

These are defaults, not quotas. The selector proposes one conservative family. Add another only when the source and your playing needs justify it. It cannot guarantee that an automatic fill candidate is musically a fill.

For a route `main → fill+return → following main`, launch the fill at the intended phrase boundary, then queue the following main during the fill pad's final cycle. A One Shot **does not automatically restart the main**. Use one complete drum pad at a time. Full drum pads layered together double the hits.

Numbered files are deliberately short: `01.wav`, `02.wav`, etc. The pad number stays readable on a phone; the guide contains the names.

## 5. Set the three-column layout

Columns run vertically, left to right. Rows run horizontally, top to bottom. The default is **three columns × six rows**; five rows are also accepted. Empty slots remain empty. Repeated numbers place the same sound in multiple convenient locations.

Keep a main and its replacement fill/return within one column. Different Remixlive columns can sound together, so stop the previous column when changing routes. The native session contains an eight-column backing grid for format compatibility, with performance audio assigned only to the first three columns.

In the app, edit the layout table; use 0 for an empty cell. Every selected pad must appear somewhere in the layout.

## 6. Export a pack

Use the app's listening checkbox and review note, then **Approve selection and export final pack**. Command-line equivalent:

```bash
worship-beats review jobs/my-song/project.json --approve \
  --note 'I listened to repeated loops and both transition demos; corrected the opening.'
worship-beats export jobs/my-song/project.json
```

To audition before approval:

```bash
worship-beats export jobs/my-song/project.json --draft
```

Exports use a new timestamped folder under the job's `exports/`. An explicit `--out` must name a new folder; previous exports are preserved.

| File | Use |
| --- | --- |
| `01.wav`, `02.wav`, … | Importable stereo PCM-16, 44.1 kHz pads, each under 20 seconds |
| `WORSHIP_BEATS.rmxl` | Native Remixlive archive, including its referenced Song asset |
| `NUMBERED_WAV_PACK.zip` | WAVs, guide, decisions, validation and demos; native project is separate |
| `START_HERE.txt` | Pad names, positions, routes and playback advice |
| `manifest.json` | Exact frames, hashes, source times, roles and gain |
| `project_export.json` | Export-time decision snapshot; keep the original job for editing |
| `LISTEN_FIRST_DO_NOT_IMPORT/` | Repeated-loop and transition demos, not sampler pads |
| `validation.json` | Technical checks and separate listening/device status |

```bash
worship-beats validate jobs/my-song/exports/YOUR_EXPORT_FOLDER
```

The validator checks PCM, canonical sample counts, finite samples, peaks, edges, full FFmpeg decoding, hashes, archive CRC and referenced native assets. Source-adjacent declared routes and separate-fill/combined-fill consistency are checked during rendering.

## 7. Import into Remixlive and transfer to a phone

1. Keep the `.rmxl` intact. Import it with the app's project import/open facility. Alternatively, unpack the WAV ZIP and import only the numbered WAVs.
2. Verify project BPM and quantization match the intended pulse grouping. Check **Repeat Off** and **Multiple Mode Off** for ordinary replacement playing.
3. Play the opening repeatedly. Test every main/fill/return route. Check Loop versus One Shot and compare the pad sounds with the supplied demos.
4. Export the project from Remixlive, import that export again, and check playback before relying on sharing.
5. Transfer the archive using Files, AirDrop or your preferred file transfer, then repeat the checks on the actual iPhone/iPad.

The adapter was reconstructed from a clean Remixlive 8.7.0 blank export and includes the small Song-mode asset that older hand-built packs omitted. File validation alone does not establish compatibility with every app version. Desktop import/playback/export/re-import and iPhone/iPad checks remain **pending** until performed; the release does not label them as passed.

## 8. Models, caching and interrupted jobs

The default is a drum-specialist checkpoint from Demucs `htdemucs_ft`. Optional accompaniment mode uses its vocal-specialist checkpoint and subtracts the vocal estimate from the master:

```bash
worship-beats prepare '/path/to/song.m4a' --job jobs/backing --mode instrumental
```

Accompaniment mode retains the instruments together; it cannot selectively remove a particular live musician. Full backing music contains chords, so equal BPM does not make two sections interchangeable.

The first separation downloads a pinned official checkpoint of about 84 MB and verifies its full SHA-256 before loading. Models normally live in `~/.cache/worship-beats/models`. To choose another location:

```bash
export WORSHIP_BEATS_MODEL_CACHE="$PWD/model-cache"
```

See [model details and notices](THIRD_PARTY_NOTICES.md). No model weights are committed here. A verified existing Torch cache can be reused.

Repeat a failed `prepare` with the same source/range/job to reuse completed verified stages. A completed source decode and completed matching separation are cached. **Partially completed neural inference is restarted**; it is not resumed from an internal audio chunk. Once `project.json` exists, review it or use a new job name. Preparation will not overwrite your decisions.

```text
jobs/my-song/
  source/          original media, master.wav, source hashes
  stems/           complete separated stem and provenance
  analysis.json    tempo candidates, local grids, cycle recurrence
  features.npz     onset/energy features for review
  project.json     editable portable decisions and review
  cache/           timing-corrected working audio
  exports/         preserved export versions
```

Move the complete job folder to preserve relative asset references. The export snapshot alone does not include the original master or stem. Do not publish a job folder as a code example: it can contain songs, paths and source metadata.

## 9. Update and diagnose

```bash
git pull --ff-only
bash scripts/setup_mac.sh
.venv/bin/worship-beats doctor
```

Keep song jobs outside tracked source. Back them up before changing dependencies. A constraints file pins the tested environment without shipping a virtual environment or machine-specific package URLs.

For clicks, off-grid pads, wrong tempo, separation bleed, downloads, installation failures and missing native assets, read [troubleshooting](docs/troubleshooting.md).

## 10. Reusable rules, skill and developer notes

- [Musical extraction rules](docs/extraction-rules.md): opening motifs, recurrence, compound pulse ambiguity, source-adjacent fills and gain.
- [Transposing audio explained](docs/transposition.md): why chords survive key changes and how recorded tone can change.
- [Architecture and project fields](docs/architecture.md).
- [All commands](docs/commands.md).
- [Verification and remaining limitations](docs/verification.md).
- [Portable Codex skill](skills/extract-worship-beat-loops/SKILL.md): optional; the application works without it.
- [Sanitized project example](examples/README.md): metadata and a generated software fixture, no song audio.

Run software checks with:

```bash
python -m pip install '.[dev]'
pytest -q
python -m build
python scripts/make_demo_project.py --out jobs/software-demo
worship-beats export jobs/software-demo/project.json --draft
```

The fixture tests file handling and timing; it is **not a requested song, a listening-approved loop pack, or a replacement for extracted drums**.

## Rights

Original toolkit code and documentation are MIT licensed. Dependencies and separation models retain their own terms. Songs, performances, lyrics and generated stems do not become MIT licensed because this tool processed them. Supply and use media you have permission to use. See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
