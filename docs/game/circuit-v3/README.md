# Circuit v3 — mobile controls, full-screen view and road repair

## What changed

- Actual CSS/SVG **three-spoke steering wheel**, with drag-around-rim input and return to center on release/cancel/focus loss.
- Switchable **polygon left/right buttons**. Quick switch below the wheel, or choose in Controls; preference persists locally. Walking keeps a separate joystick.
- Actual **ribbed pedal-shaped gas and brake controls**, independent multi-touch sources, explicit stopped-car **D/R selector**, separate safe exit and recover utilities. Pedal press changes are visibly animated. Keyboard remains supported.
- Gas no longer reduces available steering. Previously driving input was normalized together with throttle as though it were diagonal walking, reducing full steering to ~0.707 while gas was held.
- Compact race progress/timer, speed/gear, live route map and next-gate marker, bend direction/suggested speed, off-road/wrong-way guidance. Only the next checkpoint arch is visible.
- Responsive camera aspect and render dimensions fill the viewport instead of centering a fixed 16:9 canvas inside a portrait screen. No stretched world or large intentionally empty letterbox bands. Explicit Full (~2.07 MP), Balanced (~0.92 MP), and Performance (~0.52 MP) render pixel-budget settings; Full remains default. None is a phone FPS guarantee.

## Concrete track defect and correction

An audit of the previous terrain GLB against its 160 road center samples found **45 centers with terrain above tarmac**, reaching **0.6727 m** above it. A visible road was therefore not necessarily the surface seen by the wheel rays. Shared terrain and the original cinematic remain unchanged.

The custom edition now has:

- A separate hashed **graded terrain derivative** below the road corridor, smoothly blended into the surrounding landscape.
- A **640-point closed, arc-length-resampled circuit**, smoothed vertical profile and **10 m** driving surface. The original route still describes the same lakeside circuit, not an unrelated map.
- Identical road vertices for rendering and collision; triangle internal-edge collision correction, continuous edge lines/dashed center paint, physical guardrails, and trees/rocks/grass excluded from the road corridor.
- Ordered **forward swept checkpoint crossings**, with lateral/height bounds and an explicit finish gate. Passing a gate in reverse, parking near it, skipping sectors or driving outside the road does not earn progress. High-speed segment crossing is checked instead of requiring a frame to land within a small radius.
- **Nearest-safe-road recovery** that preserves the lap timer/progress, clears held controls/velocity, and cannot award a checkpoint by teleportation. Full circuit restart remains a separate pause-menu action. Off-track timeout and falling into the lake recover safely.
- Optional **road assist** (default on): eased torque request plus requested-torque reduction/service braking for estimated bend speeds. It does not assign position, orientation or velocity and is not a self-driving system or manufacturer ADAS model. Disable it in Controls.

## Validation result

**46 Python tests, 16 real Rapier tests, six viewport/control-mode DOM-input cases, and 17 WebGL/touch integration checks passed.** Browser errors: `[]`. Production build passed with the existing ~5 MB bundle-size warning; this is not hidden as a performance success. Captures use the explicitly selected Performance preset under software rendering, not a physical phone.

Actual captures: `landscape-wheel.png`, `landscape-arrows.png`, `portrait-wheel.png`, and `launcher-ui.png`. The actual launcher supplies the versioned `social/after-dark-circuit-v3.jpg`; selected AI concepts are never used as game/crawler screenshots.

## Reproduce and verify

- `node tools/game/build_track.mjs`
- `.venv/bin/python tools/game/grade_track_terrain.py` (requires NumPy; standard Python also works when dependencies are installed)
- `npm test --prefix engine`: actual Rapier tests include **960 center/wheel-lane road ray checks**, underlying-terrain clearance, correct spawn contacts, ordered gates, finish/lap and seam recovery, plus previous dynamics/walking regressions.
- `node engine/tests/circuit-drive.js [report.json]`: actual rigid-body endurance over the corrected terrain/road and runtime-matching guardrail proxies. A **test-only pursuit driver** supplies steering/throttle/brake inputs; it never changes body transforms or velocity after spawn. Actual result: **one full lap, 7,252 simulation steps / 120.867 s, maximum centerline deviation 0.722 m, minimum four wheel contacts**. This is a physical-path regression, not a user race time, real-time benchmark, or runtime autopilot feature. See `solver-lap.json`.
- `node tools/game/circuit_ui_test.cjs`: real Chromium DOM/CSS and actual `AlpineInput` touch handlers, wheel/buttons plus gas, brake, cancellation/blur and walking separation, non-overlapping controls at 360×800, 724×1280 and 932×430. Does not claim WebGL rendering.
- `node tools/game/circuit_browser_test.cjs`: actual WebGL/Rapier/touch integration and screenshots. For practical CPU readback, simulation is test-timer-stepped independently of rendering; the **Performance preset is explicitly selected**. Not real-time or physical-phone evidence.

## Images and limits

The two images in `docs/design/` are **AI-generated user-selected design references**, not screenshots or proof of rendering fidelity. PNGs captured here are actual game UI from Chromium. The new social JPEG is converted from the actual `launcher-ui.png`; provenance and hashes are in `social-preview.json`.

Original Roadster model: metarex.4d, CC-BY-4.0. Photographic night sky: Greg Zaal / Poly Haven, CC0-1.0. Existing source/rights records remain shipped. This is a playable custom-framework prototype, not photorealistic/AAA/Steam integration or certified Tesla physics. Physical-phone testing and 60 FPS remain unverified.
