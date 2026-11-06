# Villa Garden — a playable APK of the villa model

A small first-person game built out of the villa itself. You start on the south lawn in
mid-afternoon sun, eight collection orbs are scattered across the 87 × 84 m garden, and the
clock runs until you have walked all of them. No enemies, no tutorials, no ads, no
permissions, no network: it is a walk in a garden you (well, `villa_src/`) built.

**Download:** <https://github.com/mhammedamazil-hub/Testrepo/releases/tag/villa-garden-v8>
→ `villa-garden.apk` (≈ 29 MB, Android 5.0+ / `minSdk 21`, arm64-v8a + armeabi-v7a).
Or from any Actions run: *Artifacts* → `villa-garden-apk`.

> **v7 failed to build** with `CMake can not determine linker language for target:
> native_app_glue` — the NDK glue is a C file and the CMake project only enabled C++. v8
> enables both and compiles the glue straight into the .so. Use v8, not v7.
>
> **v7 is native-only: there is no Java in the APK at all.** The window, EGL, touch and the
> HUD are `cpp/main_android.cpp` + `cpp/hud.cpp`; the launcher activity is
> `android.app.NativeActivity` and the entry point is `android_main()`. The HUD is drawn in
> GL from a baked font atlas (`tools/hud_font.py`), so text is crisp without a Canvas.
>
> **v6 fixed a shader compile error the on-screen diagnosis caught** (`S0033: no default
> precision defined for function 'aces_fit'` — the shared tone-curve chunk was injected ahead
> of the `precision` statement). That is the reason v5 was still black.
>
> **v5 renders the scene in display space, so post-processing can never black it out again,
> and it puts its own diagnosis on screen.** If the picture is wrong, the panel at the bottom
> left now lists the GPU, the shader precision, which programs linked, an off-screen-target
> self-test, and pixel probes of the scene and the final frame. Please screenshot that panel
> rather than the sky.
>
> **v1 was a black screen, and v3 ran, but badly.** See *What went wrong*, items 6–10.
> Everything found on a real phone is now covered by two static gates that run before Gradle:
> `tools/gles_shader_check.py` (GLSL) and `tools/game_device_check.py` (the device-only
> contracts: post-process UVs, camera basis, attribute slots, texture units, input signs).
> Their logs ship with every run as `shaders.log` and `device.log`.

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
| **Walk** | thumb down anywhere on the left half of the screen — a stick appears there; push it the way you want to go |
| **Look** | drag anywhere on the right half; drag up to look up |
| **Collect** | walk into an orb (they glow gold; the arrow at the top points at the nearest) |
| **Restart** | tap the win screen |

The stick is floating, so a phone held one-handed and a tablet lying flat both work.

## What is actually in it

![gameplay frames](../docs/game_frames.png)

Four frames from the desktop harness at 1920 × 1080 — the same renderer maths, the same
level, the same movement code the APK runs, rasterised in software. What you see is the
intent: midday sky with cloud rows, mown lawn, baked tree shade, reflected glazing, an
interior lit only by the sky through the openings.

| | |
|---|---|
| Language | **C++ only.** No Java: NativeActivity + android_native_app_glue (v7) |
| Renderer | OpenGL ES **2.0**, one forward pass + a 4-pass post chain, no extensions, no float textures |
| Internal resolution | renders at the surface size up to **1920 × 1080**, draws through RGBA8 HDR-ish targets |
| Post | soft-knee bright pass → 2 × separable blur → 40-step god rays → ACES + gamma + dither |
| Geometry | 88 draw calls, 1.24 M vertices, 609 862 triangles, 40 textures at 256 px |
| Lighting | one raking sun, hemisphere ambient, **baked per-vertex AO and sun visibility** |
| Wind | the whole tree canopy sways from a per-vertex phase; foliage cards get a stronger gust |
| Water | the pool gets animated normals, a sky mirror, Fresnel, a tight sun glint and a body colour |
| Glass | Fresnel sky reflection over a dim room — a mirror, not transmission |
| Sky | full-screen quad: gradient, sun disc + glow, procedural altocumulus, no sky texture |
| Ground | procedural patches, grain, fine noise and mown stripes in world space, fading with distance |
| Gameplay | 8 objectives, wall sliding, 0.45 m step-up, 3.15 m/s walk, camera bob, timer |
| HUD | drawn in GL from `assets/hud_font.png` (95 glyphs, 16×6 cells): counter, timer, fps, crosshair, compass chevron, thumb stick, boot screen, diagnostics |
| Audio | **none since v7** — the Java AudioTrack player was removed with the rest of the Java. The wav files are still in `res/raw` for whoever writes the AAudio/OpenSL player |
| Assets | `assets/model.vpk` 30.2 MB, `assets/level.bin` 406 kB |
| APK | ≈ 29 MB, `minSdk 21`, two ABIs, debug-signed |

## Why this, and not Unreal

The request was to use "Unreal Python" to make the game. Unreal's Python is editor
automation: it needs a workstation GPU, an installed Unreal Editor, and it cannot produce a
smooth APK in this sandbox (no GPU, no editor, no 100 GB toolchain). Blender *can* run
headless here and did — every asset in the game comes from the existing `villa_src/` build.

So the split is:

- **Blender** — the villa: 823 objects, 299 910 polys, procedural PBR textures (milestones 6–9).
- **`tools/villa_pack.py`** — flattens the GLB into `VPK1`: scene graph baked to world space,
  primitives merged per material, ≤ 65 535-vertex chunks so every index is 16-bit, positions
  quantised to `uint16`, textures kept as their original JPEG bytes. It also **bakes the
  lighting**: per vertex, a cone-march towards the sun (three jittered rays for a soft
  penumbra) and eight hemisphere rays for occlusion, over a sparse voxel grid of the whole
  villa and garden. The two bytes ride in what used to be vertex padding, so the stride stays
  20 B and the loader did not change.
- **`tools/game_level.py`** — bakes `LVL1`: rasterises the *triangles* to get thin walls and
  real doorways, floods reachability with the same body test the game uses, marks the pool as
  blocked (you cannot walk on water), and places the objectives by farthest-point sampling.
- **`android/game/app/src/main/cpp/`** — ~2 700 lines of C++, and that is the whole app:
  `game.cpp` (renderer, post chain, engine entry points), `main_android.cpp` (EGL, input,
  frame loop, boot screen), `hud.cpp` (GL HUD), plus the shared `vpk.cpp`. No Java, no JNI,
  no third-party libraries.
- **`tools/hud_font.py`** — bakes the HUD atlas the renderer draws text with.

## How it is verified without a device

This sandbox has no Android SDK, no NDK, no GPU and no phone, so nothing here was run on
Android. What *was* run is real:

```bash
# the level, exactly as the game reads it
python tools/game_level.py villa_v2/villa_v2_lite.glb \
    -o android/game/app/src/main/assets/level.bin --map docs/game_level_map.png
# → PLAYABLE: all 8 objectives reachable, farthest 84.9 m of walking

# the game, walked end to end by the real movement code with a BFS autopilot
g++ -O2 -std=c++17 tools/game_sim.cpp android/viewer/app/src/main/cpp/vpk.cpp \
    -Iandroid/viewer/app/src/main/cpp -Iandroid/game/app/src/main/cpp -o /tmp/gamesim
/tmp/gamesim play android/game/app/src/main/assets /tmp/shot 6
# → PASS: collected 8/8 objectives in 117.8 s of game time (7069 frames, 371 m walked)

# the shaders and the device-only contracts, before any phone sees them
python tools/gles_shader_check.py     # → PASS: 13 shader stages, 8 programs
python tools/game_device_check.py     # → PASS: 34 device contracts hold
```

That harness compiles `game_core.h` and `level.h` unchanged, loads the real `model.vpk` with
the real loader, and rasterises the same shading maths at 1080p — so it catches the failures
that matter: a route the body cannot fit through, an objective inside a wall, a body leaving
walkable ground, a broken pack, and (since v3) a frame that comes out black.

The type check of the NDK sources against stub headers (`tools/android_stub/`) also runs in CI,
and the workflow then verifies the built APK actually contains `classes.dex`,
`lib/arm64-v8a/libvillagame.so`, `lib/armeabi-v7a/libvillagame.so`, `assets/model.vpk`,
`assets/level.bin` and the three `res/raw` sounds.

`.github/workflows/game-apk.yml` runs all of that before Gradle, so a green run means the
level is traversable, the pack is intact, the shaders link and a 1080p frame is not black —
not merely that the compiler exited 0. Every run uploads `game_1080p.png`,
`game_playthrough.png`, `game_level_map.png`, `level.json`, `play.log` and `shaders.log` as
the `game-evidence` artifact.

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
6. **v1 shipped black.** One uniform, `u_eye`, was `mediump` in the vertex shader and
   `highp` in the fragment shader. GLSL ES requires a shared precision for every name that
   crosses the stage boundary; the driver refused to link, `glLinkProgram` failed, and the
   app happily drew nothing. The harness never caught it because it never links GLSL. The
   fix was to write `XPREC` on every shared declaration and add
   `tools/gles_shader_check.py`, a static linker that parses the shader sources, resolves the
   default precisions and fails on any mismatch — now a CI gate, along with a rendered
   1080p frame and a "is the mean luma above zero" assertion.
7. **The bake had five separate bugs** before it was believable: rays starting inside their
   own voxel; out-of-grid samples clamping to the boundary layer and shadowing the whole
   garden (98 % of it, silently); alpha-cutout foliage treated as solid walls; lawn-edge
   normals firing rays straight into the ground; and a 70 m lawn slab with four vertices, so
   per-vertex lighting had nowhere to live. Each is commented in `tools/villa_pack.py`.
8. **A white facade is not white.** With a 3.3-unit sun, a white wall clips to a blank 255
   sheet. Albedo is now capped at 0.75 — real paint is not a perfect reflector — and vertical
   surfaces get world-space plaster grain so a sunlit wall has tonality instead of glare.

9. **v3.0 rendered, and looked like the mesh was corrupted.** Three defects stacked:
   the post-process quad passed *clip* space (-1..1) straight into `texture2D`, so every
   sample with a negative coordinate clamped to the edge texel and half of each frame was a
   smear of one column; `draw_sky`/`draw_orbs` built their camera basis as
   `(cos yaw, 0, -sin yaw)`, which is the *negative* of the view matrix's right axis, so
   `up = right × fwd` came out as `(0,-1,0)` and the skybox rendered upside down (the grey
   "below the horizon" haze ended up above the horizon); and `draw_model` uploaded its
   textures on whatever texture unit the post chain had left active — unit 2 — while the
   shader sampled unit 0, which still held the *previous frame's scene target*. Every
   surface was therefore textured with the last frame's screenshot at model UVs. That is what
   "the mesh is broken" looked like.
10. **The controls were doubly inverted.** `GameSurface` reported the stick as
   `y = -dy/r` (correct: drag up = forward) and `GameRenderer` then passed `-jy` into the
   movement code, so forward and back swapped; the look drag added `dy` straight into pitch
   (screen y is down, pitch is up), so looking ran backwards too. Both are fixed at their
   source, and `game_device_check.py` asserts the two signs.
11. **The skybox had its own copy of the sky gradient** and it was three stops darker than
   `sky_at()` in the model shader — so the glass and the pool reflected a bright midday sky
   while the sky itself was dusk. One set of constants now, asserted equal.

12. **v4.0 was a black screen with a live HUD**, which is a different fault from v3.0 and is
   the reason this build exists: the tone curve lived in the *composite* pass, so anything
   that went wrong in the last full-screen pass (an off-screen target the driver would not
   render into, a dropped uniform, a link failure in one of the four post programs) blacked
   the whole frame while the Java HUD happily kept drawing. Fixed structurally rather than
   guessed at: **exposure + ACES + sRGB now happen in the pass that knows the light**
   (`kCommonGlsl`, prepended to every fragment shader), so post is purely additive. If it
   fails, the frame is simply unbloomed. On top of that the renderer now *tests itself*:
   frame 1 clears the off-screen target to magenta and reads the pixel back, frame 3 probes
   the scene and the final frame, post switches itself off if it turns a non-black scene
   black, and every measurement is printed in the HUD panel.

## Honest limits

- **Never run on Android.** No device, no emulator, no SDK in this sandbox. The APK builds
  in CI and its contents are verified, the game logic and the look are verified on the
  desktop, but the GLES2/JNI/EGL glue has only been compiled, not executed. If something is
  wrong it will be in that glue.
- **The HDR chain is fake HDR.** GLES2 without extensions has no float or half-float colour
  attachment, so bloom and god rays work on 8-bit targets over a scene that is already
  clamped to 0..1 per channel. It looks right; it is not physically linear all the way
  through. A device with `OES_texture_half_float` + `EXT_color_buffer_half_float` could get
  a real float chain, and this renderer is one `Target` change away from it.
- **The sun bake is baked.** The villa and the sun are static, so this is exact — but if the
  sun ever moves it must be re-baked; nothing updates it at runtime.
- **Glass is not transparent.** glTF transmission is unavailable, so panes are a Fresnel sky
  reflection over a flat dark room colour: you see a mirror, not the room.
- **Foliage is alpha-tested cards.** At 256 px they read as leaves at a distance and as flat
  sprites up close.
- **The camera cannot go upstairs or onto the roof**; the roof is excluded from the level.
- **The sound was measured, not auditioned.** I have no ears in this sandbox: the clips are
  checked for level, spectral content and a seamless wind loop, nothing more.
- **The render resolution adapts, and that is why it is sharp for some and soft for others.**
  The frame-rate governor in `game.cpp` drops to 0.7× and then 0.5× of the (1080p-capped)
  surface if the average frame takes longer than 45 ms, and climbs back when there is
  headroom. A mid-range phone will settle around 0.7×; a recent one stays at 1.0×.
- **I still cannot see your screen.** v5's HUD panel is the substitute: it reports what the
  renderer can measure about itself. It cannot report a driver bug that silently draws wrong
  pixels with no GL error, and it cannot tell you why a *specific* pixel is the wrong colour.
- **The device bugs found in v3.0 were found from a screenshot, not a debugger.** The host
  harness and the device share the game, the level, the pack and the shading maths — but not
  the GLES driver, the texture units, or the post-process rectangles. Items 8–10 below were
  all in that gap; the static gate in `tools/game_device_check.py` now pins them, but it can
  only pin bugs that are already understood.
- **Debug-signed.** Signing a release keystore into a public repo would be theatre.

## Regenerate everything

```bash
python tools/game_level.py villa_v2/villa_v2_lite.glb \
    -o android/game/app/src/main/assets/level.bin --map docs/game_level_map.png
python tools/villa_pack.py villa_v2/villa_v2_web.glb \
    -o android/game/app/src/main/assets/model.vpk          # ~2 min: this is the AO/sun bake
python tools/game_audio.py android/game/app/src/main/res/raw
python tools/gles_shader_check.py                          # must PASS before Gradle
gradle -p android/game assembleDebug                       # needs the Android SDK + NDK 26.1
```

`docs/game_level_map.png` is the baked level from above: blue is walkable, dark red is
blocked, gold the objectives, green the spawn.
