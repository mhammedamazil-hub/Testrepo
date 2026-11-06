# Revision 2 — final brief and production render

## User decisions

- Keep 20 seconds and native 1920×1080; raise frame rate to **60 fps / 1,200 rendered frames**.
- Camera glides from shore out over the lake and rises, with meaningful parallax.
- Reveal a fixed sun behind the mountain using camera motion, not an accelerated astronomical sunrise.
- Clear morning, brighter/readable forest shadows, scattered clouds; final lighting clarification selected strong cinematic rays and localized thicker mist.
- Breezier water, traveling waves and sun reflections.
- A subtle distant flock of 5–8 birds; implemented as seven modeled, articulated birds.

## Implemented

- Upgrade the exact previously delivered Blender geometry from immutable commit `d95ac748d7cd08a5f359501323048047a0c2433e`; hash checked by `prepare_revision_base.py`. No branch switch or scene rebuild is required.
- Replace flat-looking spruce shoot fans with irregular curved branching and three-dimensional needle/shoot clusters; five linked canopy variants and per-instance color variation. 365 near trees have anchored wind sway.
- Curved meadow blades; conservative union-of-flight-frusta culling reduces file size without cutting visible grass.
- Approximately **117 m** drone translation, including 54 m lateral travel, 103 m forward travel and 9 m ascent. Fixed 28 mm lens, smooth gimbal aim, restrained motion blur.
- Search actual mountain BVH for a fixed sun direction that is ridge-occluded at the opening and revealed at the ending, with an unobstructed end-of-shot specular water point. Current tested base: azimuth −3.875° from forward, elevation 16°.
- Finite sun disc, directional backlight, physically modeled sky fill, height-decaying finite 3D mist and ray-traced shadows. Light shafts are actual scattering, not a painted overlay.
- Closed dielectric lake, true absorption, shallow bathymetry, five gravity-wave components driven by Geometry Nodes Scene Time, and advected fine wind normals.
- Seven bird bodies, tails and paired articulated wings; flight paths, independent flap/glide cycles, no static V decals.
- Rounded procedural cumulus tests were rejected. A credited **CC0 4k photographic cloud environment** now supplies distant sky detail and its water reflection; actual 3D mist supplies nearby atmospheric depth. The captured sky is art-directed alongside separately controlled morning lighting; see `assets/CREDITS.md`.

## Relevant installed skills

The 94-skill pack remains installed. Applied lighting, vegetation-artist, camera-cinematography, vfx-fx, materials, realistic-style, rendering, compositing and qa-review guidance. Direct bpy is used, not an unavailable MCP endpoint.

## Technical checks so far

- Revised scene gate: native full HD, revision 2, 60 fps, 1–1200, CPU Cycles, geometric water waves, absorption, packed photographic sky, finite mist, wind sway, seven bird roots, >100 m camera motion, fixed-sun reveal and unobstructed end water-light path.
- Native 60-fps codec smoke test: 100 × 12-frame segments, stream-copy assembly, full 1,200-frame decode and exact 20-second duration: PASS. Synthetic fixture frames exist only in temporary codec-test directories, never in the deliverable.
- Missing-frame rejection: PASS.
- Opening, midpoint and ending preview framing inspected. Low-resolution previews are **not** final delivery.

## Render approval and honesty

The final user clarification selected **strong cinematic rays**. After local opening/midpoint/ending lighting tests and technical/codec checks, the production render gate is enabled. No further creative approval is required to start rendering. The original delivered movie remains revision 1 until the new full render, assembly and independent verification complete. Full-resolution temporal review remains pending; the low-resolution tests do not certify final artistic quality.

Photorealism is a visual/artistic goal, not something that the fps, sample count or successful technical gates can certify. Remaining issues must be disclosed rather than hidden by a passed render check.

Full animation is divided into 100 twelve-frame CPU chunks, at most 20 concurrent, to keep individual jobs safely inside runner time limits without lowering resolution, frame rate or sample quality. H.264 uses two-pass analysis of original PNGs at 16 Mbps, High profile / level 4.2 for 1080p60 playback; segments are stream-copied, never lossy-reencoded at assembly.

## Final lighting decision

The user selected **strong cinematic god rays** in the final clarification. Three soft-bounded, advected, height-faded mist banks are added at the forest edges, the real solar backlight is strengthened, and optical fog-glow around the actual sun disc is increased. These are physically lit 3D participating media with actual tree/mountain shadows; there are no painted beam planes or composited Sun Beams overlays. This is intentionally more dramatic than strictly documentary haze.

Final local lighting QA rejected an isolated oval fog patch. The accepted setup uses wider overlapping shore mist, stronger directional backlight and a brighter optical halo. The mountain silhouette and most of the lake remain readable. Near-water mist is masked above the water surface. Bird spacing is irregular rather than a uniform line.
