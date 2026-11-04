# Villa viewer — a tiny C++-era Android viewer for the villa model

The exported GLB is 40–52 MB of glTF with 723 nodes, 1019 primitives and 110 separate
images. That is fine in a desktop browser and miserable on a cheap tablet: a glTF viewer has
to parse a JSON scene graph, then the driver has to cope with hundreds of tiny draw calls.
So the model is **converted at build time** into a flat binary the tablet can slurp, and the
app is deliberately primitive.

| | |
|---|---|
| Renderer | OpenGL ES **2.0**, fixed-function-era feature set only |
| Code | ~600 lines Java + GLSL, no third-party libraries in the APK, no NDK |
| Draw calls | **87** (the GLB has 1019 primitives) |
| Geometry | one VBO, one index buffer, **16-bit** indices only, 20-byte vertices |
| Lighting | per-vertex sun + sky/ground ambient (no half-float, no shadows) |
| Textures | 40 textures at 256 px, mipmapped |
| Asset | `assets/model.vpk`, **25.8 MB** (from a 37.7 MB GLB) |
| APK | ~26 MB, `minSdk 21`, lands on anything from 2014 onwards |
| Controls | drag = orbit, pinch = zoom |

## Build it (GitHub Actions)

Nothing needs to be installed locally — push and let the workflow build it:

1. Actions → **Build villa viewer APK** → *Run workflow* (or just push to `android/**`).
2. Open the finished run → **Artifacts** → `villa-viewer-apk` → `villa-viewer.apk`.
3. On the tablet: allow "install unknown apps" for your browser/files app, then open the APK.

The same workflow also uploads `pack-preview` (`front.png`, `garden.png`, `pack.json`) so you
can see what the packed model looks like **without installing anything**.

## Why there is a pack step

`tools/villa_pack.py` reads the GLB and rewrites it as `VPK1`:

- bakes the scene graph into world space (no node tree at runtime);
- merges primitives **per material**, then splits into chunks of ≤ 65 535 vertices so every
  index is 16-bit — no `OES_element_index_uint` needed on old drivers;
- quantises positions to `uint16` inside each chunk's bbox and normals to `int8`
  (20 bytes/vertex instead of ~32–44);
- keeps the original JPEG texture bytes inline, so the app only decodes what it draws;
- records a "framing box" from the building only, so the camera does not frame a 92 m garden.

52 MB GLB → 37.7 MB (256 px textures) → **25.8 MB packed**, same 599,282 triangles.

## Verifying without a tablet

`tools/vpk_preview.cpp` compiles the **same `vpk.cpp` loader and the same shading/camera
maths** (`cpp/shade.h`) for the host and rasterises in software:

```bash
g++ -O2 -std=c++17 tools/vpk_preview.cpp \
    android/viewer/app/src/main/cpp/vpk.cpp \
    -Iandroid/viewer/app/src/main/cpp -o /tmp/vpkpreview
/tmp/vpkpreview android/viewer/app/src/main/assets/model.vpk out.ppm 0 10 40
```

`yaw_deg pitch_deg dist_m` — yaw 0 looks at the south elevation, 210° the garden corner.
If that image looks right, the packing, quantisation, indexing, textures, alpha cutouts and
lighting are right; only driver behaviour is left untested. CI runs it on every build.

## Honest limits

- **This was written and reviewed in a sandbox with no Android SDK and no `javac`, so the
  first GitHub Actions run is the first real compile.** The pack format, the loader and the
  image have been verified (above); the Java/GL glue has not been executed yet.
- **No transmission.** glTF `KHR_materials_transmission` cannot be done on GLES2, so glass
  is drawn last as a dark 62 %-opaque tint. It reads as glazing; it is not see-through.
- **No shadows, no reflections, no ambient occlusion** beyond the sun/ambient split. The
  renders in `villa_v2/` look richer than the app will.
- **Per-vertex lighting** means large flat surfaces (roof, walls) get smooth normals but no
  specular variation. That is the price of running on weak hardware.
- Triangles are not decimated: 599 k is fine for a 2018+ tablet, tight-but-playable on 2014
  hardware. If it stutters, the next lever is dropping foliage cards in the packer, not
  shrinking textures.
- The viewer shows the model, not the scene: no sky texture, no clouds, no people.

## Regenerating the asset

```bash
# 256 px lite GLB (committed) -> packed asset
python tools/villa_pack.py villa_v2/villa_v2_lite.glb \
    -o android/viewer/app/src/main/assets/model.vpk --json-out /tmp/pack.json
python tools/verify_pack.py /tmp/pack.json
```

To build the lite GLB from scratch you need Blender (see `VILLA_V2.md`), then:

```bash
.venv/bin/python tools/bpy_run.py villa_src/export_v2.py -- --out villa_v2 --tex 256 --name villa_v2_lite.glb
```
