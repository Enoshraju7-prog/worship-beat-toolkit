"""Streamlit UI. All processing stays local; Terminal shows model-level progress."""

from __future__ import annotations
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import streamlit as st
from worship_beats.project import (
    load_project,
    save_json,
    approve,
    validate_project,
    resolve_asset,
)
from worship_beats.pipeline import prepare
from worship_beats.render import export_project
from worship_beats.audio import time_seconds

st.set_page_config(page_title="Worship Beat Toolkit", layout="wide")
st.title("Worship Beat Toolkit")
st.caption(
    "Prepare → listen and adjust → export. Local processing; no Codex or paid API required."
)
st.info(
    "Automatic timing and fill labels are proposals, not proof of musical correctness. Only one complete drum pad should play at a time."
)
default = sys.argv[1] if len(sys.argv) > 1 else ""
path = st.sidebar.text_input(
    "Project JSON to review", value=st.session_state.get("project_path", default)
)
with st.expander("Prepare a new song", expanded=not bool(path)):
    url = st.text_input("YouTube link or local media path")
    upload = st.file_uploader(
        "Or upload audio/video",
        type=["wav", "mp3", "m4a", "flac", "aif", "aiff", "webm", "mp4", "mov"],
    )
    job = st.text_input("New/resumable job folder", value="jobs/my-song")
    col1, col2, col3 = st.columns(3)
    start = col1.text_input("Start (seconds / mm:ss / hh:mm:ss)", value="0")
    end = col2.text_input("End (blank = source end)")
    bpm = col3.number_input("Starting BPM (0 = propose)", 0.0, 300.0, 0.0, 0.1)
    pulses = st.number_input("Sampler pulses per cycle (not notation meter)", 1, 16, 4)
    mode = st.selectbox("Output audio", ["drums", "instrumental"])
    shifts = st.selectbox(
        "Separation quality/time", ["1 shift — standard", "2 shifts — slower averaging"]
    )
    if st.button("Prepare draft", type="primary"):
        try:
            source = url
            if upload:
                folder = Path(job).expanduser().resolve()
                folder.mkdir(parents=True, exist_ok=True)
                name = Path(upload.name).name
                dest = folder / ("uploaded_" + name)
                if dest.exists():
                    raise FileExistsError(
                        "Upload already exists; use the local file path or a different job."
                    )
                dest.write_bytes(upload.getbuffer())
                source = str(dest)
            if not source:
                raise ValueError("Choose a source.")
            with st.status("Preparing…", expanded=True) as status:
                project = prepare(
                    source,
                    Path(job),
                    time_seconds(start),
                    time_seconds(end) if end else None,
                    bpm or None,
                    pulses,
                    mode,
                    False,
                    int(shifts[0]),
                    progress=st.write,
                )
                status.update(label="Draft ready", state="complete")
            st.session_state["project_path"] = str(project)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

if not path:
    st.write("Choose a song above, or enter an existing project.json in the sidebar.")
    st.stop()
try:
    project_file = Path(path).expanduser().resolve()
    p = load_project(project_file)
except Exception as exc:
    st.error(str(exc))
    st.stop()
st.subheader(p["name"])
st.caption(
    "Source timing is relative to the selected excerpt. Originals and stems are retained in the job folder."
)
analysis = (
    json.loads((project_file.parent / p["analysis_file"]).read_text())
    if p.get("analysis_file") and (project_file.parent / p["analysis_file"]).exists()
    else {}
)
for warning in analysis.get("warnings", []):
    st.warning(warning)
if analysis.get("tempo_candidates"):
    with st.expander("Tempo candidates and local timing diagnostics"):
        st.dataframe(pd.DataFrame(analysis["tempo_candidates"]), hide_index=True)
        st.dataframe(pd.DataFrame(analysis.get("local_grids", [])), hide_index=True)
features = project_file.parent / "features.npz"
if features.exists():
    z = np.load(features)
    t = z["times"]
    e = z["energy"]
    st.line_chart(
        pd.DataFrame(e[:, ::8].T, index=t[::8], columns=["Low", "Mid", "High"]),
        height=170,
    )
with st.expander("Listen to source excerpt and separated audio"):
    st.audio(str(resolve_asset(project_file, p["source"]["master"])))
    st.audio(str(resolve_asset(project_file, p["stem"])))
c1, c2, c3 = st.columns(3)
new_bpm = c1.number_input("Project BPM", 20.0, 300.0, float(p["target_bpm"]), 0.1)
new_pulses = c2.number_input("Pulses per cycle", 1, 16, int(p["pulses_per_cycle"]))
new_phase = c3.number_input(
    "Analysis phase (seconds)",
    0.0,
    value=float(p["grid"]["phase_seconds"]),
    step=0.005,
    format="%.6f",
)
st.caption(
    "Per-pad source_start controls the actual cut. Changing the analysis phase alone does not move existing pads; use the shift control below."
)
shift = st.number_input(
    "Shift all existing pad starts by seconds", value=0.0, step=0.005, format="%.6f"
)
st.write(
    "Edit numbered pads: section, role, source boundary, local cycle period, length and mode. Delete unwanted rows; add only genuine source patterns."
)
table = st.data_editor(
    pd.DataFrame(p["pads"]),
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "mode": st.column_config.SelectboxColumn(options=["Loop", "One Shot"])
    },
)
st.write("Placement: rows run top to bottom; columns are vertical. Use 0 for empty.")
layout = st.data_editor(
    pd.DataFrame({f"Column {i + 1}": c for i, c in enumerate(p["columns"])}),
    hide_index=True,
)
sections = st.text_area(
    "Section landmarks JSON (labels plus source times; optional)",
    json.dumps(p.get("sections", []), ensure_ascii=False, indent=2),
)
routes = st.text_area("Source-adjacent routes JSON", json.dumps(p.get("routes", [])))
pairs = st.text_area(
    "Separate-fill / combined-fill pairs JSON", json.dumps(p.get("fill_pairs", []))
)
demos = st.text_area("Demo sequences JSON", json.dumps(p.get("demos", {}), indent=2))


def edited():
    q = json.loads(json.dumps(p))
    q.update(target_bpm=new_bpm, pulses_per_cycle=int(new_pulses))
    q["grid"]["phase_seconds"] = new_phase
    q["pads"] = json.loads(table.to_json(orient="records"))
    for item in q["pads"]:
        if float(item["number"]) != int(item["number"]) or float(item["cycles"]) != int(
            item["cycles"]
        ):
            raise ValueError("Pad numbers and cycles must be whole numbers.")
        item["number"] = int(item["number"])
        item["cycles"] = int(item["cycles"])
        item["source_start"] = float(item["source_start"]) + shift
    q["columns"] = []
    for c in layout:
        values = layout[c].fillna(0)
        if any(float(v) != int(v) for v in values):
            raise ValueError("Layout values must be whole pad numbers or 0.")
        q["columns"].append([int(v) for v in values])
    q["sections"] = json.loads(sections)
    q["routes"] = json.loads(routes)
    q["fill_pairs"] = json.loads(pairs)
    q["demos"] = json.loads(demos)
    validate_project(q)
    return q


if st.button("Save edits (invalidates earlier approval when selection changes)"):
    try:
        q = edited()
        save_json(project_file, q)
        st.success("Saved. Reload before making further changes.")
        st.rerun()
    except Exception as exc:
        st.error(str(exc))
if st.button("Build listening previews / draft pack"):
    try:
        q = edited()
        result = export_project(q, project_file, draft=True)
        st.session_state["last_pack"] = str(result)
    except Exception as exc:
        st.error(str(exc))
result = st.session_state.get("last_pack")
if result:
    st.write("Latest generated pack: " + result)
    for f in sorted((Path(result) / "LISTEN_FIRST_DO_NOT_IMPORT").glob("*.wav")):
        st.write(f.stem)
        st.audio(str(f), loop=False)
    files = sorted(Path(result).glob("[0-9][0-9].wav"))
    if files:
        f = st.selectbox(
            "Audition one pad repeatedly", files, format_func=lambda v: v.name
        )
        st.audio(str(f), loop=True)
checked = st.checkbox(
    "I listened to repeated loops and transition demos and approve these exact settings."
)
note = st.text_input("Listening review note")
if st.button("Approve selection and export final pack", disabled=not checked):
    try:
        q = edited()
        approve(q, note)
        save_json(project_file, q)
        result = export_project(q, project_file)
        st.session_state["last_pack"] = str(result)
        st.success("Approved export complete. Test on your actual Remixlive device.")
    except Exception as exc:
        st.error(str(exc))
if result:
    for name in ("WORSHIP_BEATS.rmxl", "NUMBERED_WAV_PACK.zip", "START_HERE.txt"):
        f = Path(result) / name
        if f.exists():
            st.download_button("Download " + name, f.read_bytes(), file_name=name)
st.caption(
    "Editing anything after approval invalidates it. Musical quality, desktop round-trip and iPhone/iPad verification are separate checks."
)
