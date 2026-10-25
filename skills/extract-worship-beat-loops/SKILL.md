---
name: extract-worship-beat-loops
description: Extract actual drum grooves and matched fills from a supplied song, review the opening and repeating grid, and export numbered live sampler pads with the local worship-beat-toolkit. Use for song-to-loop and Remixlive pack requests; full-mix key transposition is a separate operation.
---

# Extract worship beat loops

Use the local toolkit as a processing engine, with human listening decisions between preparation and final export. The CLI works independently of Codex. Read `../../docs/extraction-rules.md` for musical decisions and `../../docs/commands.md` for exact commands when using this repository checkout. If installing this skill elsewhere, retain a toolkit checkout and read the equivalent files there.

- Preserve the actual source and complete separated stem. Inspect existing job state before downloading, installing or separating again.
- Use supplied/authorized media. Never substitute generated drums for a requested song; the bundled fixture is for software tests only.
- Audit the opening motif independently. A cleaner later recurring groove can lose the opening's first attack, pickup or rotation. Include two opening repetitions in an audition.
- Test competing pulse interpretations and local timing across the performance. Keep notation meter separate from sampler cycle grouping. A BPM estimate is a proposal.
- Compare repeating whole patterns; internal A/B variation can be intentional. Do not invent a new pad for every stem-leak difference.
- Prefer source-adjacent main → fill → return → following-main cuts. A short fill and its combined fill/return should share the same processed raw prefix. Never snap the two endpoints independently.
- Apply canonical sample lengths, short edge fades and one shared gain. Review the first intended attack and several repeats. Technical file validation is separate from listening suitability.
- Default to three vertical columns with five or six horizontal rows, leaving spare cells empty. Name importable files only by two-digit number. Put roles, source times and routes in the guide/manifest.
- Keep full-groove replacement routes within a column when possible. One Shot does not automatically recall a main. Different columns can overlap; do not promise mutual exclusion without checking the app.
- Export drafts for audition; record approval only from an actual listening decision. Changing cuts, asset identity, timing or layout invalidates it. Do not label automatic proposals listening-approved.
- Retain every referenced native archive asset, including the empty Song-mode file. Report import/playback/export/re-import and mobile-device status separately from ZIP validation.
- Keep song-specific BPMs, lyrics and timestamps in that job's metadata. Reusable lessons belong in the guide; they do not authorize publishing songs or changing unrelated settings.

For this release's scope and test status, read `../../docs/verification.md`. Treat automatic role names and section labels as provisional until checked against the actual performance.
