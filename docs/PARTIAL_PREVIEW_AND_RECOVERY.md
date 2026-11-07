# Partial preview and production recovery note

## Partial preview

User requested a preview of finished footage without interrupting production. Workflow `alpine-partial-preview.yml`, run [42329503245](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42329503245), reads completed artifacts from production run 42202373037. It stream-copies only the continuous opening, verifies every decoded frame at native 1920×1080/60 fps, and publishes separately named `Alpine_Mirror_PARTIAL_1080p60.mp4` and `partial_preview_validation.json`. It does not modify or cancel any production job, render settings or final deliverable.

Five preview safety tests passed. An additional temporary two-clip codec test passed full decoding of 24 unique native full-HD 60-fps frames; its synthetic fixture was deleted and is never delivery footage.

At the initial snapshot, 61 production clips had succeeded. Clips 0–56 form 684 continuous native frames / 11.4 seconds. Some later completed clips are deliberately omitted instead of hiding gaps by jumping forward or fabricating frames. The actual published preview report records its source snapshot.

## Existing production failure discovered during this request

Production job `render (57)` (job/check ID 127841029740) had already been cancelled at 2026-11-07T02:09:15Z, before the preview request/workflow. Its check annotation explicitly states: **“The job has exceeded the maximum execution time of 5h50m0s.”** Other production jobs remain running/queued under `fail-fast: false`.

This missing clip covers frames **685–696**. No production cancellation or restart was requested by the preview workflow. The original final assembly depends on the whole render matrix succeeding, so it will need recovery; a partial preview must not be described as final completion.

For targeted recovery, preserve all successful original artifacts. Prefer splitting only the missing clip into two six-frame renders (685–690 and 691–696) rather than repeating the same twelve-frame timeout risk. Use the **exact original production scene artifact** (`alpine-scene`, artifact ID 13493529971, run 42202373037), not a rebuilt Blender file with a different hash. Preserve original 128 samples / .03 noise / min 24 / native resolution / 60 fps. Reunite the twelve raw frames before using the existing chunk encoder for chunk 57, or supply rigorously equivalent segment metadata. Final assembly must account for recovered clips from a separate run if the original matrix remains cancelled. Check for any further timeouts before assembling; do not rerun all successful clips unnecessarily.

No recovery render was launched as part of the preview request.
