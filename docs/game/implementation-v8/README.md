# v8 — approved UI in the playable runtime

This is an implementation pass, not another reference-gallery release. The generated concepts remain in `../mountain-v7/references/`; the PNGs here are browser captures of the actual custom Three.js/Rapier game.

## Implemented

- Graphite/ivory/amber guest entry, live full uploaded Roadster model, six working paint choices and live guest-name label. Drag to orbit the preview; the preview renderer is disposed before loading the game.
- Actual room lobby, invitation/copy, racer ready states and host start controls. Chat lives in the scrollable room column instead of covering the car.
- Race dashboard, standings, speed/nitro meter, minimap, desktop keyboard help, portrait/landscape touch wheel or arrows and pedals.
- Circuit-map overlay with eight checkpoints and four pickup markers; settings with persisted steering, motion and touch preferences. Graphics are chosen before a session, not changed by silently disconnecting it.
- Online menu releases driving controls without pretending to pause the shared race. Modal keyboard focus handling, results and room-ended UI retain their real actions.
- Matching solo theme applied to the existing solo menu, garage, settings, race HUD and finite-hop interface. Original solo content and cinematic are preserved.

## Mountain work and remaining gap

The Blender builder now creates seven warped, terraced limestone massifs with talus aprons and eroded crowns, rather than an enclosing regular dome. The playable valley uses lower nonperiodic foothills and a route-flattened surface. Rock colour/AO/height data is adapted from pinned MIT-licensed source textures; originals, licence and checksums are retained. This uses **texture data only**, not Godot code or an engine change. Snow shelves are altitude/slope blended in the runtime material.

Terrain is divided into 64 tiles plus 16 skyline sectors, each with three authored LODs. Forest instances use 180 m spatial groups, detailed nearby trees and cheaper distant cards/silhouettes. Camera-frustum/distance culling only affects rendering: physics colliders stay active. High has more forest instances, but not fully detailed far scenery.

The builder regenerates terrain samples from `engine/src/online/map.js` before export. The manifest records that source hash, and a regression test rejects stale terrain exports.

**The actual scene does not yet match the generated mountain reference.** Close cliff geology, erosion, snow distribution, roadside dressing and lighting still differ. These screenshots are evidence of the current implementation, not photorealism approval. No physical-phone FPS or cross-NAT connectivity claim is made.

## Evidence and reproducibility

- `guest-desktop.png`, `guest-mobile.png`: real full-model preview/name/paint.
- `race-desktop-high.png`, `race-touch-portrait.png`: actual local practice world and physics, software WebGL.
- `settings.png`, `race-menu.png`, `track-map.png`: actual interactive overlays.
- `lobby.png`, `results.png`: synthetic session snapshots used **only** to exercise these UI states; not proof of an online race finishing.
- `browser-validation.json`: actual implementation browser assertions.
- `ui-validation.json`: eight viewport/steering layout checks. Preview module is stubbed only in this layout suite; actual rendering is tested separately.
- `physics-lap.json`: force-driven automated circuit lap, not a cinematic or browser performance measurement.
- `webrtc/`: independent browser clients with a real local PeerJS server and WebRTC exchange. Not public internet/cross-NAT certification.
- `graphics/`: Low/Balanced/High preset assertions; software render settings, not device benchmarks.
- `culling/`: five-view geometry comparisons and collider/transform invariance.

Commands (from repository root):

```sh
npm test --prefix engine
.venv/bin/python -m unittest discover -s tests
npm run build --prefix engine
node tools/game/implementation_browser_test.cjs
QA_OUTPUT=docs/game/implementation-v8/webrtc node tools/game/multiplayer_browser_test.cjs
QA_OUTPUT=docs/game/implementation-v8/graphics node tools/game/multiplayer_quality_test.cjs
QA_OUTPUT=docs/game/implementation-v8/culling node tools/game/mountain_browser_test.cjs
```

Browser suites require the cached Playwright/software-graphics tooling and a local game server. Multiplayer suites additionally require local signalling, configured at Vite build time. `GAME_URL` (or `GAME_BASE` for the culling suite) can target a static production build, avoiding development hot reload during captures. Browser RAF is disabled and frames are advanced explicitly for deterministic visual evidence; these runs cannot certify real-time performance.

Blender authoring: run `tools/game/build_mountain.py` with Blender 4.3's Python/bpy, NumPy and Pillow available. It prepares shared terrain input automatically, exports the GLB/material/manifest and retains the editable `.blend` source.

## Verified results for this pass

- Node: **59 passed**; Python: **63 passed**; production Vite build passed.
- Actual implementation browser: **12 passed**, no runtime/shader errors.
- Independent local WebRTC clients: **22 passed**, no runtime exceptions.
- Low/Balanced/High: **3 passed** (800×450 / 1280×720 / 1920×1080 render budgets).
- Multiplayer responsive layout: **8 passed**; existing solo layout/multitouch: **12 passed**.
- Input-only physics lap: **8 gates**, 357.3677 s simulated finish; maximum route distance 1.2087 m, minimum four wheel contacts, zero rejected snapshots.

The graphics and browser runs used software rendering. Their runtimes are not performance measurements. The generated reference and actual vista remain visibly different; the UI implementation is the stronger part of this release.

Five-view culling comparison: **5 checks passed**; submitted triangles reduced by **55.7–87.2%** relative to the all-full-detail test mode. Collider count and car transform remained unchanged. This is a geometry submission comparison, not an FPS improvement claim.
