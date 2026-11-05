# Villa Garden — a playable APK of the villa model

A small first-person game built out of the villa itself. You start on the south lawn at
golden hour, eight collection orbs are scattered across the 87 × 84 m garden, and the clock
runs until you have walked all of them. No enemies, no tutorials, no ads, no permissions, no
network: it is a walk in a garden you (well, `villa_src/`) built.

**Download:** <https://github.com/mhammedamazil-hub/Testrepo/releases/tag/villa-garden-v2>
→ `villa-garden.apk` (≈ 28 MB, Android 5.0+ / `minSdk 21`, arm64-v8a + armeabi-v7a).
Or from any Actions run: *Artifacts* → `villa-garden-apk`.

## Install

1. On the phone or tablet, open the release link above and tap `villa-garden.apk`.
2. Android will say the file can't be installed from this app — allow **"install unknown
   apps"** for your browser/file manager, then tap the download again.
3. Launch **Villa Garden**. Landscape, full screen.

It is a **debug-signed** APK: Google Play Protect may show "unsafe app blocked" for a
sideloaded, self-signed package. Choose *install anyway*. There is no keystore in this
repository and there never will be — see *Honest limits*.

## Controls

| | |
|---|---|
| **Walk** | thumb down anywhere on the left half of the screen — a stick appears there |
| **Look** | drag anywhere on the right half |
| **Collect** | walk into an orb (they glow gold; the arrow at the top points at the nearest) |
| **Restart** | tap the win screen |

The stick is floating, so a phone held one-handed and a tablet lying flat both work.

## What is actually in it

![gameplay frames](../docs/game_frames.png)

Six frames from the desktop harness — the same renderer maths, the same level, the same
movement code the APK runs, rasterised in software at 512 × 288.

| | |
|---|---|
| Renderer | OpenGL ES **2.0**, one forward pass, no extensions, no float textures |
| Geometry | 88 draw calls, 609,862 triangles, 40 textures at 256 px (decoded on demand) |
| Lighting | one raking sun + hemisphere ambient + ACES tone curve + distance fog + grazing sheen |
| Sky | full-screen quad: gradient, sun disc and glow, procedural altocumulus — no sky texture |
| Gameplay | 8 objectives, wall sliding, 0.45 m step-up, 3.15 m/s walk, camera bob, timer |
| Audio | wind loop, footsteps, pickup chime — synthesised by `tools/game_audio.py` |
| Assets | `assets/model.vpk` 26 MB (from the 41.7 MB web GLB), `assets/level.bin` 397 kB |
| APK | ≈ 28 MB, `minSdk 21`, two ABIs, debug-signed |

## Why this, and not Unreal

The request was to use "Unreal Python" to make the game. Unreal's Python is editor
automation: it needs a workstation GPU, an installed Unreal Editor, and it cannot produce a
smooth APK in this sandbox (no GPU, no editor, no 100 GB toolchain). Blender *can* run
headless here and did — every asset in the game comes from the existing `villa_src/` build.

So the split is:

- **Blender** — the villa: 823 objects, 299,910 polys, procedural PBR textures (milestones 6–9).
- **`tools/villa_pack.py`** — flattens the GLB into `VPK1`: scene graph baked to world space,
  primitives merged per material, ≤ 65 535-vertex chunks so every index is 16-bit, positions
  quantised to `uint16`, textures kept as their original JPEG bytes.
- **`tools/game_level.py`** — bakes `LVL1`: rasterises the *triangles* to get thin walls and
  real doorways, floods reachability with the same body test the game uses, and places the
  objectives by farthest-point sampling.
- **`android/game/app/src/main/cpp/`** — ~1 400 lines of C++: the game, the GLES2 renderer,
  the JNI bridge. No third-party libraries.
- **`android/game/.../java/`** — ~600 lines: activity, touch, HUD drawn with Canvas, audio.

## How it is verified without a device

This sandbox has no Android SDK, no NDK, no GPU and no phone, so nothing here was run on
Android. What *was* run is real:

```bash
# the level, exactly as the game reads it
python tools/game_level.py villa_v2/villa_v2_lite.glb -o android/game/app/src/main/assets/level.bin

# the game, walked end to end by the real movement code with a BFS autopilot
g++ -O2 -std=c++17 tools/game_sim.cpp android/viewer/app/src/main/cpp/vpk.cpp \
    -Iandroid/viewer/app/src/main/cpp -Iandroid/game/app/src/main/cpp -o /tmp/gamesim
/tmp/gamesim play android/game/app/src/main/assets /tmp/shot 6
```

`PASS: collected 8/8 objectives in 117.8 s of game time (7069 frames, 371 m walked)`.

That harness compiles `game_core.h` and `level.h` unchanged, loads the real `model.vpk` with
the real loader, and rasterises the same shading maths — so it catches the failures that
matter: a route the body cannot fit through, an objective inside a wall, a body leaving
walkable ground, a broken pack. It found three real bugs during development (see *What went
wrong*, below).

The type check of the NDK sources against stub headers (`tools/android_stub/`) also runs in CI,
and the workflow then verifies the built APK actually contains `classes.dex`,
`lib/arm64-v8a/libvillagame.so`, `lib/armeabi-v7a/libvillagame.so`, `assets/model.vpk`,
`assets/level.bin` and the three `res/raw` sounds.

`.github/workflows/game-apk.yml` runs all of that before Gradle, so a green run means the
level is traversable and the pack is intact — not merely that the compiler exited 0.

## What went wrong on the way (kept, because the fixes are the design)

1. **Object AABBs as collision** turned the whole villa into solid rock: the walls of one
   elevation are a single joined mesh, so its bounding box covers the entire house. The fix
   is per-triangle rasterisation — thin walls, real doorways, correct terrace steps.
2. **A cell-level walkable mask is not a body-level one.** The player is a 0.52 m body, and
   the first autopilot run wedged in a hedge gap that the grid called passable. The bake now
   floods with a body-clearance mask and the harness verifies with the exact runtime rim test.
3. **"Erode until the body test always passes" can never terminate** — repeatedly eroding a
   bounded region always ends in the empty set. It shrank the garden from 46 000 to 4 000
   cells before the objectives ran out of room; the fix is one erosion pass plus a single
   verification pass that drops the few stragglers.
4. **A triangle that straddles the camera was dropped** by the software rasteriser (no
   near-plane clipping), so the lawn was invisible in the harness while the GPU would have
   drawn it. Worth keeping in mind: the harness and the device share maths, not a driver.
5. **Authoring the sky in display space** made it read as black; it is authored in linear
   light now, like the rest of the shading.

## Honest limits

- **Never run on Android.** No device, no emulator, no SDK in this sandbox. The APK builds
  in CI and its contents are verified, the game logic and the look are verified on the
  desktop, but the GLES2/JNI/EGL glue has only been compiled, not executed. If something is
  wrong it will be in that glue.
- **No shadows and no ambient occlusion**, because GLES2 forward rendering without a shadow
  map cannot do them. Outdoors it reads fine (hemisphere ambient plus fog); **interiors look
  flat and too white** — the sun is not occluded by the roof. This is the most visible
  difference from the Cycles stills.
- **Glass is not transparent.** glTF transmission is unavailable, so panes are a 35 % cool
  tint: you can see the dark of a room behind them, not the room.
- **Foliage is alpha-tested cards.** At 256 px they read as leaves at a distance and as flat
  sprites up close, and they are the brightest thing in the scene.
- **The camera cannot go upstairs or onto the roof**; the roof is excluded from the level.
- **The sound was measured, not auditioned.** I have no ears in this sandbox: the clips are
  checked for level, spectral content and a seamless wind loop, nothing more.
- **Debug-signed.** Signing a release keystore into a public repo would be theatre.
- 610 k triangles at 60 fps is comfortable on a 2018+ phone and should be fine on a 2015
  tablet; if an old device stutters, the lever is foliage cards (they are ~60 % of the
  triangles) — dropping them in `tools/villa_pack.py` needs no app change.

## Regenerate everything

```bash
python tools/game_level.py villa_v2/villa_v2_lite.glb \
    -o android/game/app/src/main/assets/level.bin --map docs/game_level_map.png
python tools/villa_pack.py villa_v2/villa_v2_web.glb \
    -o android/game/app/src/main/assets/model.vpk
python tools/game_audio.py android/game/app/src/main/res/raw
gradle -p android/game assembleDebug        # needs the Android SDK + NDK 26.1
```

`docs/game_level_map.png` is the baked level from above: blue is walkable, dark red is
blocked, gold the objectives, green the spawn.
