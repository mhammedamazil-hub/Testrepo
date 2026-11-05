# Alpine Mirror — QA ledger

## Status
**Artistic verdict: NOT YET APPROVED as an ultra-photoreal reference match.**
**Technical verdict: see generated `output/scene_validation.json` and, after encoding, `output/delivery_validation.json`.**

Neither a running render nor a workflow definition is a completed movie. The 20-second delivery is complete only when all 480 native full-HD frames exist, the encoder succeeds, and the full movie decodes to the expected frame count and duration.

## Reference comparison / iteration record

1. Initial CPU preview: foreground terrain occluded the lake; sky over-bright; mountains had excessively regular stripes. Rejected.
2. Corrected lake opening and world shader; changed rock/snow masks, displaced and warped the massif, moved camera to 28 mm environmental framing. Rejected regular terrain and foliage patterns.
3. Added hydraulic erosion, preserved primary summit with a low erosion blend, increased terrain sampling, added multiscale rock normals, hid an artificial-looking standalone glacier sheet. Added steep-slope forest belt and better boulder fracture planes.
4. Added modeled needle silhouettes, dense interior spruce shoots, foreground meadow density and lupines. Corrected a display-link dependency problem without replacing any Cycles renderer functions.
5. Replaced overlapping flank/shore sheets with one continuous valley terrain to eliminate open undersides and shadow artifacts. Lowered the back valley floor, completed the far-shore forest belt, and checked first/mid/last framing at preview resolution.
6. Passed isolated 1080p segment-encode/concatenate/full-decode tests and missing-frame rejection tests. Synthetic codec fixtures are created only in temporary test directories and deleted; none are delivery footage.

## Implemented technical gates

- Scene must be 1920×1080 at 100%, 24 fps, frames 1–480.
- Cycles CPU, denoising, AgX; actual dielectric lake surface.
- More than 2,500 linked tree instances and substantial mountain geometry.
- No external image texture projections/backplates.
- Actual camera translation and animated water normals.
- Resumable frame rendering with scene SHA-256 and quality-settings sidecars.
- Every encoded source PNG verified at full HD; each ten-frame segment is decoded and SHA-256 checked. Segment assembly is stream copy, not a second lossy encode. All chunks must match the delivered scene SHA-256.
- Entire encoded MP4 decoded, checking dimensions, 24 fps, 480 decoded frames and 20-second duration.

## Remaining artistic limitations to disclose

- This is a seeded procedural reconstruction, not scanned geology or a pixel-matched digital twin.
- Summit contours, relative valley widths, exact snow distribution and foreground boulder placement differ from the source.
- Procedural foliage and rock materials do not automatically reach scanned-asset/AAA photorealism simply by increasing samples.
- Low-sample previews are not final denoising or temporal-flicker reviews. Final first/mid/last frames and playback need visual inspection before production approval.
- No audio was requested; the movie is silent.

## Provenance and delivery

94 MIT-licensed skills installed and used for pipeline guidance. All scene generation/render/verification source is supplied. The image reference is retained for art direction only. Large raw PNG sequences stay out of Git; only compact requested deliverables may be published by the render workflow.
