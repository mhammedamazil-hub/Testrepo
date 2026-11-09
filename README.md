# Alpine: After Dark — Roadster Expedition

## Play the custom Alpine game

**[Play free in your browser](https://mhammedamazil-hub.github.io/Testrepo/)** · [Compatibility /alpine/ URL](https://mhammedamazil-hub.github.io/Testrepo/alpine/) · [Runtime and controls](engine/README.md)

The custom **Three.js + Rapier WASM** edition is now the primary game. Drive the supplied Roadster beneath real Milky Way photography, or explore on foot. Includes a premium-PC-game-inspired launcher, functional garage/controls/pause panels, touch controls, checkpoints, recovery, day/night and headlights. Static Open Graph/Twitter cards use the actual first-screen capture.

- **Actual dynamic vehicle:** four raycast suspension contacts, force-driven AWD, load-limited tire grip, body inertia, collision and gravity. The original user-uploaded `roadster_lite.glb` is unchanged; its compiled derivative has independent wheel pivots.
- **Research, not invented factory data:** mass/power/suspension/tire/aero estimates are disclosed. Measured simulation: **2.43 s 0–60 mph, 29.09 m braking from 26.95 m/s**; not manufacturer-certified real-car results. [Sources, assumptions and limits](docs/research/roadster-physics-and-night.md).
- **Night sky:** Satara Night, actual star/Milky Way photography by Greg Zaal / Poly Haven, CC0. Roadster model by metarex.4d, CC-BY-4.0. [Credits](game/CREDITS.md).
- **Desktop:** WASD/arrows, drag to look, E enter/exit, Space jump/brake, Shift run, R recover, N day/night, H headlights, Escape pause.
- **Phones:** landscape recommended; independent joystick/look/pedals/actions. Chromium mobile emulation is tested; physical-phone performance remains unverified.
- Native **1920×1080** rendering and fixed **60 Hz physics**. **60 FPS is a target, not achieved/certified device coverage.** This is a playable prototype, not photorealistic/AAA/Unreal parity.
- [Validation/publication workflow](https://github.com/mhammedamazil-hub/Testrepo/actions/workflows/game-build.yml) builds only the custom game to root and `/alpine/`. Godot sources remain in [`game/`](game/README.md) as a legacy edition; they are no longer the primary release or part of this build.

The original completed cinematic below is preserved separately and is not changed by the game upgrade.

## Completed 20-second 1080p60 cinematic delivery

- `output/Alpine_Mirror_1080p_20s.mp4` — **1920×1080, 60 fps, 1,200 native rendered frames, exactly 20 seconds**, H.264, silent.
- `output/Alpine_Mirror_1080p.png` — original revision-2 full-HD 384-sample hero still.
- `output/Alpine_Mirror.blend` — the exact packed, editable Blender 4.2 LTS scene used by all clips.
- `output/delivery_validation.json`, `output/independent_verification.json`, `output/recovery_validation.json` — full-decode, native-frame and recovery provenance reports.

[Successful recovery and final assembly](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42446280821). Preserved 88 completed clips byte-for-byte and recovered only 144 missing frames in small jobs. No upscaling, retiming, interpolation or fabricated frames. Final assembly stream-copies compatible clips, without another lossy encode.

**Visual disclosure:** technical verification is not a photorealism certification. This remains a procedural 3D reconstruction with an art-directed CC0 photographic sky and ray-traced volumetric mist; separate artistic review is required.

The earlier full-render workflow hit worker time limits. Use the recovery workflow for this recovery, not an unnecessary restart of all completed clips. Before any future fresh full render, reduce the original workflow's twelve-frame chunks using measured worst-case frame times.

[Historical 11.4-second preview](https://github.com/mhammedamazil-hub/Testrepo/raw/93d4d430e2ad68b066694489e079a61ef31f04e0/output/Alpine_Mirror_PARTIAL_1080p60.mp4) remains downloadable from its original commit. Its redundant working-tree copy is removed only after the verified full movie is archived, to keep the delivery within storage limits.

## Rebuild locally

Use Blender 4.2 LTS with its Python environment, or Python 3.11 on Linux:

```bash
pip install -r requirements.txt
python scripts/prepare_revision_base.py
python scripts/revise_scene.py --preview
python scripts/validate_scene.py
python scripts/render_frames.py --start 1 --end 1200 --samples 128 --threads 4
python scripts/render_frames.py --only 1200 --still --samples 384 --noise .02 --min-samples 32 --threads 4
python scripts/encode_verify.py
python scripts/verify_delivery.py
```

Install the normal OS dependencies for the PyPI `bpy` module: `libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libice6 libgl1`.

In this network-restricted, display-less sandbox only, `python scripts/bootstrap_headless.py` supplies uncalled display-link shims. Then prefix rendering commands with:

```bash
LD_LIBRARY_PATH=$HOME/tools/headless-libs OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python scripts/build_scene.py --preview
```

Those shims are **not** for UI, Eevee, OpenGL or GPU use. GitHub runners use real OS libraries, not shims.

## Rendering and recovery

`render_frames.py` validates and skips already-complete PNGs; interrupted frames are written to temporary filenames and are not considered finished. All animation frames are rendered at native resolution; no upscaling, frame duplication or optical-flow interpolation is used. Cycles CPU, adaptive sampling, OpenImageDenoise, AgX color management, dielectric water and geometric instancing keep the scene within a small RAM budget.

Run the isolated codec smoke tests with `python -m unittest discover -s tests -v`. Synthetic test colors are temporary test fixtures, never delivery footage.

The workflow `.github/workflows/alpine-render.yml` first checks the explicit full-render approval flag and upgrades the original delivered scene in place once, distributes 1,200 frames over 100 twelve-frame CPU jobs (at most 20 in parallel), renders the hero still separately, encodes each native 60-fps segment once, then stream-copies the segments into the final MP4 and fully decodes it for verification. It publishes compact requested deliverables only on `arena/f0bb5c2d-testrepo`; raw PNG sequences stay on the temporary workers; compact encoded segments are short-retention Actions artifacts, not Git files. The workflow is intentionally restricted to this session branch.

Final output binaries are normally ignored. The publishing job explicitly adds only the requested compact `.blend`, PNG, MP4 and small validation manifests for durable delivery; raw sequences, caches and logs never enter Git.

## Art and provenance

See [production brief and hardware audit](docs/PRODUCTION_BRIEF.md) and [QA notes](docs/QA.md).

The MIT-licensed **94 Blender skills** from [`arjun988/blender-skills`](https://github.com/arjun988/blender-skills), revision `8f778d2405a214b508d4c7d80742be8e43acdd52`, are installed in `.claude/skills`; license retained in `.claude/BLENDER_SKILLS_LICENSE`. Direct `bpy` execution is used because no Blender MCP endpoint is available.

The environment uses seeded procedural geometry/materials, including hydraulic erosion, actual mesh needles and linked spruce instances. No commercial assets, generated-image substitutes, landscape backplates or hidden reference-photo projections are used. Revision 2 adds a packed **CC0 photographic sky environment** for more natural distant clouds and water reflections; nearby mist remains volumetric. See [asset credits](assets/CREDITS.md).
