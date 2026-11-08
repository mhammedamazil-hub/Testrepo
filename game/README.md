# Alpine Mirror — Lakeside Escape

A **real Godot 4.4.1 3D walking/driving prototype**, built from the Alpine Blender landscape in this repository. Not a prerecorded video or a JavaScript imitation of Godot.

## What you can play

- Explore the original mountain-and-lake environment on foot.
- Enter a non-branded car, drive the roughly **965 m lakeside loop**, brake and get out.
- Follow four mint-colored checkpoints to complete a lap; best lap is saved locally.
- Orbit the follow camera, look behind, pause and recover at the overlook.
- Native **1920 × 1080** rendering; real FPS counter. **60 FPS is a target, not a guarantee or an achieved result implied by the cap.** See `docs/game/` at repository root for actual verification results.
- Balanced lighting is default. Optional enhanced real-time shadows retain the same native resolution. Distant trees use original-scene billboard impostors to keep geometry cost down.

This is a playable vertical slice, **not a complete GTA-style open-world game or photorealism sign-off**. The character/car art is simplified; there is no traffic, combat, multiplayer or mission system. Performance on hardware graphics must be measured separately from this sandbox's CPU-only graphics tests.

## Controls

| Key | Action |
|---|---|
| WASD / arrows | Walk or drive; A/D steer while driving |
| Shift | Run on foot |
| Space | Jump on foot / brake while driving |
| E | Enter nearby car / exit when stopped and door space is clear |
| Left click, then mouse | Capture cursor and orbit camera |
| Mouse wheel | Camera distance |
| Q | Look behind |
| R | Recover at the overlook, reset lap progress |
| Escape | Pause/resume and release cursor |
| F | Fullscreen, subject to browser/iframe permission |
| F2 | Balanced / enhanced shadows (neither lowers 1080p render resolution) |
| F8 | Reset the real wall-clock frame-time measurement window |
| M | Mute/unmute |

Desktop keyboard/mouse **and mobile multi-touch controls** are implemented. Use landscape orientation on a phone; portrait mode displays rotation guidance. A modern WebGL 2-capable browser is needed. Chromium mobile emulation is tested; physical Android/iOS device coverage and 60 FPS are not certified. Open the preview in its own tab if the embedded frame will not allow fullscreen or pointer capture.

## Mobile controls

Open **https://mhammedamazil-hub.github.io/Testrepo/** in a modern phone browser
and rotate to **landscape**. No installation or paid service is required.

- **Left stick:** move on foot; steer while driving.
- **Drag the empty right side:** orbit the camera, independently of movement.
- **ENTER / EXIT:** get into the nearby car, or out after stopping.
- **GAS / REVERSE / BRAKE:** drive; **JUMP / RUN:** on-foot actions.
- **PAUSE / RECOVER:** pause/resume through the large menu button, or reset.
- Releasing/canceling touches releases input. Changing tabs or losing focus
  pauses and clears active controls; tap **Resume escape** when returning.
- **T** toggles the touch overlay when testing with a desktop keyboard.

Mobile rendering stays at the declared **1920 × 1080**, with no hidden resolution
reduction. Both desktop and mobile GPU texture formats are exported. Rendering
speed and memory use depend on the physical browser/device; no all-phone or
60 FPS guarantee is implied. The first download can take a while.

## Visual realism pass

The current revision adds licensed photo-derived grass detail, close-range
material normals, a smoothly lofted 12.6k-triangle unbranded touring car,
spatial needle-bough card spruce LODs near the road, instanced meadow tufts and
rocks, and a static reflection panorama captured from the actual terrain.
Distant trees remain billboards. Nearby branch-card LODs deliberately disable
automatic simplification: it otherwise removes thin/disconnected foliage.
The character is still simplified; car physics are arcade/kinematic. Water
uses a **baked reflection approximation**, not real-time planar reflection or
SSR. This is a visible realism improvement, **not a photoreal/AAA sign-off**.
Assets: `tools/game/build_detail.py`, `assets/detail_manifest.json` and
`assets/grass_surface.provenance.json`; license attribution is in CREDITS.md.

## Run / edit the source

Open this folder's `project.godot` in official **Godot 4.4.1**. The converted game assets are already included; Blender is not needed to play or edit the Godot game.

On a normal machine with Godot and its matching export templates installed:

```bash
godot --headless --path game --editor --import
python3 tools/game/export_game.py --godot /absolute/path/to/godot
python3 tools/game/serve.py --port 3000
```

Run commands from repository root. The static server binds to `0.0.0.0`; game browser requests are relative to its own origin. Web release files and the downloadable `Alpine_Mirror_Web.zip` are produced under `.exports/`, outside Git. The ZIP includes `PLAY.txt` with standalone launch instructions. Opening the HTML with `file://` is not supported; serve the extracted folder over HTTP(S), for example with `python3 -m http.server 8080` from inside that folder, then open `http://localhost:8080` on the same machine.

The exporter builds into a fresh staging directory, rejects failed/incomplete exports and validates the archive before replacing the previous playable preview.

### Restricted Linux sandbox bootstrap

```bash
python3 tools/game/setup_toolchain.py
python3 tools/game/export_game.py
python3 tools/game/serve.py --port 3000
```

The helper restores the checksummed official Linux engine and single-threaded Web templates from a pinned, temporary transport commit already in this branch's history. It switches no branches, installs no system packages and uses no paid resources. Provenance: `docs/GODOT_TOOLCHAIN_PROVENANCE.json`. Other operating systems should use the official matching release for their platform.

### Rebuild Blender assets (optional, much larger dependencies)

```bash
python3 -m venv .venv
.venv/bin/pip install bpy==4.2.23 numpy==1.26.4 Pillow moderngl==5.13.0 glcontext==3.1.0
.venv/bin/python tools/audit_software_graphics.py
.venv/bin/python tools/game/build_assets.py
.venv/bin/python tools/game/build_audio.py
```

The generator reads the existing original `.blend`, resamples its actual eroded heightfields, grades a new road, CPU-bakes the original terrain materials, renders the original spruce impostor, and builds the vehicle and articulated hiker in Blender. It checks that the original `.blend` hash did not change. The inherited embedded-bpy native cleanup bug remains explicitly disclosed: the short-lived authoring worker exits only after validated writes. That workaround is not part of Godot's gameplay runtime.

Godot extracts embedded GLB images next to the models during import. Those generated `terrain_*.png` / `road_asphalt.png` files and `.godot/` caches are reproducible and ignored. Do not manually edit ignored extracts as your only asset source.

## Verification

Headless tests exercise **actual Godot physics/state**, but are not rendering benchmarks:

```bash
.cache/godot/Godot_v4.4.1-stable_linux.x86_64 --headless --path game --fixed-fps 60 --script res://tests/physics_smoke.gd
```

For optional rendered browser verification, install the test-only browser packages under `.cache/browser` and provide the real NSS/NSPR libraries documented in `docs/game/browser-os-provenance.json`. Then run `node tools/game/browser_test.cjs` for keyboard controls or `node tools/game/mobile_browser_test.cjs` for actual Chromium CDP multi-touch events against the running game server. This uses CPU SwiftShader in the sandbox, not a hardware GPU. Actual native viewport/canvas dimensions, real keyboard state transitions, motion and wall-clock frame times are recorded; neither 60 Hz physics nor `Engine.max_fps=60` counts as a rendering result.

See `docs/GAME_BUILD_BRIEF.md`, `docs/GAME_SKILL_USAGE.md`, and `docs/game/` for acceptance gates and measured evidence. See [CREDITS.md](CREDITS.md) for assets and licenses.

## GitHub Pages hosting

This single-threaded Web export is compatible with **free GitHub Pages**: it uses
relative asset URLs, WebGL 2 and HTTPS, and does not require cross-origin isolation
headers, a backend or a paid server. The published page opens the actual game.
Hosting does not change the outstanding 60 FPS verification requirement.

Expected URL after successful deployment:
**https://mhammedamazil-hub.github.io/Testrepo/**

The repository's `Alpine game validation and Web build` workflow validates and
exports the game, uploads a `github-pages` artifact, then publishes it using the
`github-pages` environment. Pushes affecting game/build files on
`arena/f0bb5c2d-testrepo` automatically rebuild and redeploy. It does not use or
create a separate publishing branch and leaves cinematic workflows unchanged.
The site excludes precompressed `.gz` sidecars because Pages manages its own
HTTP compression, and includes `.nojekyll` for direct static-file hosting.

**One-time repository setting:** under **Settings → Pages → Build and deployment**,
select **GitHub Actions** as the source. The current Arena GitHub connection cannot
enable Pages itself (GitHub returns HTTP 403). No credentials should be pasted
into chat or committed. Once enabled, rerun the failed deployment job from the
workflow's Actions page. If GitHub restricts the `github-pages` environment's
deployment branches, allow `arena/f0bb5c2d-testrepo` under Settings → Environments.

A successful build/artifact upload alone does not mean the public site is live;
the **Publish playable game to GitHub Pages** job must succeed too.
