# Offline Three.js cinematic — 1080p60 proof of concept

This is a **video export**, not a claim that the game runs at 1080p60 on a low-end device. Pre-rendered footage suits intro screens, trailers, cutscenes or exported replays; it cannot replace arbitrary real-time driving, steering and camera input. Three.js renders an authored camera path through the actual Roadster/alpine scene, Playwright/Chrome DevTools captures lossless full-resolution PNG frames, and FFmpeg encodes them as an H.264 MP4. No AI-generated footage, frame interpolation or upscaling.

## Deliverables

- `output/alpine-roadster-1080p60.mp4` — 1920×1080, 60 fps, 180 source frames / 3 seconds, silent.
- `output/alpine-roadster-1080p60.json` — actual export settings, errors and full decode validation.
- `output/alpine-roadster-credits.txt` — full source/license/modification notices, also embedded in the MP4 comment metadata.
- Source frames / temporary previews: `.cache/offline-cinematic/` (not Git).

At the user’s request, the finished **3-second proof MP4** is also committed at [offline-cinematic/alpine-roadster-1080p60.mp4](offline-cinematic/alpine-roadster-1080p60.mp4), with [full credits](offline-cinematic/credits.txt), so it can be accessed directly from GitHub. No 10-second version has been rendered. Other large reproducible render products follow the repository’s existing ignored `output/` and `.cache/` conventions. The original Blender cinematic, source Roadster GLB, terrain and normal gameplay settings are untouched.

## Export-only art direction

- Smooth eased three-quarter camera orbit around a parked Roadster beside the actual lake. This is an authored cinematic, not a gameplay driving/flight recording.
- Native 1920×1080 render target, fixed time `frame / 60`, FXAA at final resolution, ACES and existing photographic environment.
- Red **MeshPhysicalMaterial** clearcoat override for the car paint. Source model/material files remain unchanged. This corrects the common mistake of assigning a `clearcoat` property to a standard material that does not implement that BRDF.
- 2048² directional shadows and current-camera 1024² planar water reflection. Static shadow maps can be reused because the parked car, lights and shadow-casting geometry do not move; reflected view and shader water/wind time still change each frame.
- A soft artistic contact-occlusion decal grounds the parked hero. It is disclosed as an art technique, not ray-traced global illumination.
- Minimal motion-design title/credits overlay. No letterbox bars, AI replacements or resolution-upscaled source footage.

The initial 4× MSAA trial and the final native-resolution FXAA pipeline both took roughly ten seconds per frame after warmup on this sandbox's **software renderer**. This is why the first proof is three seconds, not a real-time capture or long trailer. Offline 60 fps describes the video's sampling/playback rate, not export speed.

## Reproduce in the existing QA environment

1. Run `npm run dev --prefix engine` (Vite binds `0.0.0.0:3001`).
2. Ensure the optional Chromium/Playwright QA dependencies and shared libraries used by the WebGL browser tests are installed in `.cache/browser`, `.cache/browser-runtime` and `.cache/software-graphics`.
3. Ensure `.venv` has `imageio-ffmpeg` (or supply the `FFMPEG` environment variable with a compatible FFmpeg binary).
4. Run `node tools/game/render_cinematic.cjs`. `--benchmark` exports only three preview stills and timing metadata. `FILM_SECONDS=6` requests 360 actual frames; expect substantially longer processing on software rendering.
5. `--resume` skips intact PNGs only when the saved settings and cinematic source hash match. It refuses mismatched/missing manifests rather than mixing different camera paths or durations.
6. The encoder uses H.264 CRF 17, YUV420p, BT.709 tags and fast-start MP4. The script decodes the complete result again, checks frame count/size/rate and records a video SHA-256 before reporting success.

`GAME_URL` can point at another dev-server address. Browser-facing game asset URLs remain relative; this tool's loopback address is only the automation controller inside the sandbox.

## Visual and performance limits

This improves cinematic presentation, anti-aliasing and material/reflection quality, but the scene still contains the project's existing stylized terrain, billboard trees and game assets. It is **not ultra-photorealistic path tracing**, a validated OEM vehicle render, or proof of real-time/physical-tablet 60 FPS. Extra offline quality is opt-in and is not imported by `main.js`, so it cannot silently increase the game's low-end workload.

Roadster model: metarex.4d, CC-BY-4.0, modified for runtime/export presentation. Environment/material sources: Poly Haven / project credits. See [full source, license and modification notices](../../game/CREDITS.md).
