# Targeted recovery — launched 2026-11-08

Run: https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42446280821

Status observed at 2026-11-08T04:20Z: source preservation/planning succeeded; 20 single-frame jobs actively rendering and 124 queued; no recovery failures at that check. This is a timestamped progress note, not a completion claim. The live workflow and eventual `RECOVERY_COMPLETE.md` / delivery reports supersede it.

## Preserved work

- Original run: 42202373037, attempt 2.
- 88 original clips / 1,056 native frames are validated and preserved byte-for-byte.
- Frozen original scene and completed original 384-sample still are reused, not rebuilt.
- Recovery source archive: artifact 13603871195 (`alpine-recovery-source`), 114,817,292 bytes, retained until 2026-11-22T04:19:09Z. This protects completed work from the original three-day clip expiration.

## Missing work only

Missing encoding chunks: 61, 65, 68, 77, 79, 85, 88, 91, 94, 95, 98, 99.

144 missing native frames are split into 144 independent one-frame jobs, at most 20 concurrent. Each retains original 1920×1080 / 60 fps / 128 samples / adaptive .03 / minimum 24 quality settings and the identical frozen Blender file. Single-frame jobs prevent another twelve-frame timeout; earlier partial attempts can be validated and resumed on retry.

After all missing frames succeed, the workflow automatically reunites each missing twelve-frame clip, encodes only those 12 clips, stream-copies all 100 clips into the full movie, performs two full-decode/provenance checks, runs all tests, archives and publishes the final scene/still/MP4/reports on the same session branch. It then cleans only its redundant raw-frame artifacts. A redundant partial-preview MP4 is removed from the final working tree only after final archival, while an immutable historical download link is retained in README.

Implementation tests: 13 passed locally; workflow syntax and exact 144-frame no-overlap coverage validated. Original full-render workflow was NOT restarted. No paid compute provisioned and no sampling/resolution/frame-rate reduction.
