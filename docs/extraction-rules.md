# Musical rules behind a useful loop pack

These are reusable decisions learned while making live worship packs. They apply to different songs; no song's BPM, timestamps, pad numbers or lyrics are universal defaults.

## Preserve the opening people recognize

Audit the first audible repeated figure separately from later sections. A global similarity search can prefer a clean later groove and lose the original opening feel. Compare the opening attack pattern with the later candidate. Preserve a distinctive opening as its own pad.

A pickup is a note before the expected phrase start. A rotated pattern begins at a different point within the same rhythmic cycle. Decide where the intended repeat begins by listening. If the opening pickup cannot repeat naturally, keep it as a one-shot entrance leading into a repeating main. Do not silently replace it with another groove.

## Count the same music more than one way

A song may support half-time, double-time or 2:3-related tempo candidates. Try counting over several phrases. Compare recurring whole patterns and local grid error, rather than accepting a single BPM detector. Keep notation meter separate from sampler pulse grouping.

Look for tempo changes and edits. A fit that is excellent early on can drift later. Use local cycle durations and phases when needed. Do not create a fake correction by independently snapping both endpoints of one cut: move one exact-length window instead.

## A repeating pattern can contain variation

A two-cycle groove may have deliberately different first and second cycles. Internal uniformity is not the test. Compare the whole two-cycle block with other whole two-cycle blocks. Check whether alternate cycles repeat more strongly than neighboring cycles before shortening the pattern.

The current automatic selector uses single-cycle descriptors to propose cuts. It does not fully resolve every multi-cycle A/B structure. The two-cycle repeated listening demo is therefore part of the review, and you can extend or move a cut.

## Match the fill to its neighbors

Prefer the main immediately before the fill, the complete fill, its natural return, and the following main. Equal BPM does not guarantee a matched mix or intensity. Check declared handoffs numerically and by listening.

Offer a one-cycle fill and a two-cycle fill/return when both are useful. The short fill should begin at the same source location and share the same processed raw audio as the combined version. Short edge fades mean the final few milliseconds of separately exported clips are intentionally attenuated.

## Keep levels and edges musical

Use one shared gain for the selected family. Independently maximizing every pad can make a quiet fill louder than a strong main. Apply short edge fades to reduce clicks without removing the first attack. The renderer uses a 20 ms pre-attack by default, adjustable from 0–50 ms, and a 3 ms edge fade.

Audit the head of every loop. A long unintended gap can make it feel late even when the duration is exact. Do not treat a genuine musical rest as a software error; decide whether that rest suits a repeating performance pad.

## Keep the performance simple

Start with a small core: recognizable opening, useful main, matched fill/return, following main. Add variations when they have a clear role. Leave unused grid cells empty.

Use three vertical columns and five or six horizontal rows as this toolkit's default performance layout. Keep paired replacement routes within a column where possible. Filename `07.wav` identifies the button; the guide explains its role.

A full drum fill replaces a full drum main. Playing both together doubles the drums. Optional subtractive overlays require exact phase, gain and playback settings; they are outside this release's ordinary replacement workflow.

## Explain what the evidence proves

- Timing and recurrence suggest candidates; listening establishes musical suitability.
- A file decoder establishes readability; it does not establish clean separation.
- A complete `.rmxl` archive establishes included references; it does not establish device compatibility.
- A user approval applies to the exact reviewed selection, not later edits.
- Lyrics-to-pad advice is a suggested arrangement unless the performance has actually been transcribed.
