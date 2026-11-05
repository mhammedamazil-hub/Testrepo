# Alpine Mirror — production brief

## Reference analysis
- Subject: photoreal alpine lake, centered pyramidal glaciated mountain, dense conifer forest, rock-and-wildflower foreground. Reference is `reference/alpine-lake.png`.
- Composition: mountain summit near (50%, 12%); distant shore near 55% image height; dark forest frames both sides; lake reflection occupies lower center; right bank curves into frame.
- Camera: level wide environmental lens, approximately 28–35 mm full-frame equivalent. Deep focus, no theatrical lens blur. Slow forward/lateral drift for 20 seconds; preserve summit and reflection.
- Silhouette: asymmetric central pyramidal peak with stepped sedimentary rock faces; secondary crags to left/right; tapering spruce silhouettes, irregular boulders.
- Light: clear blue morning; warm sun from camera left; blue sky fill; brighter snow, dark but readable forest.
- Materials: rough layered gray/brown limestone, slope-dependent snow/ice, dark evergreen foliage, damp stones, green groundcover, violet lupine accents, low-roughness dielectric water with subtle animated normals.
- Palette: sky #428fc0; snow #e5eef1; rock #777674; shadow #35454e; spruce #152c23; ground #465a30; flower #6266b0.

## Pipeline
Downloaded and installed the 94-skill MIT pack from https://github.com/arjun988/blender-skills at revision `8f778d2405a214b508d4c7d80742be8e43acdd52`, under `.claude/skills`. Applied director, reference-image-match, environment-artist, vegetation-artist, realistic-style, camera-cinematography, rendering and QA guidance. Direct headless bpy execution substitutes for MCP; no MCP endpoint is installed.

1. Audit CPU/RAM/dependencies.
2. Seeded procedural 3D scene: multi-scale mountain relief, stratified PBR rock/snow, forest mesh instances, shore terrain, boulders, grass, wildflowers, reflective water.
3. CPU Cycles preview; inspect framing, silhouettes and light before final run.
4. Save editable Blender scene and resumable render scripts.
5. Render native 1920×1080 sequence; encode 24 fps / 480 frames / 20 seconds H.264.
6. Verify frame count, dimensions, duration, and first/mid/last frames. Record actual quality and limitations; never label an unreviewed render production-approved.

## Hardware audit
- Intel Xeon virtual CPU, 2 available logical CPUs; approximately 3.8 GiB memory, no swap; approximately 20 GiB initial disk free.
- No exposed `/dev/dri` or NVIDIA device. Use Cycles CPU only.
- Blender not initially installed. Installed `bpy==4.2.23` (Blender 4.2 LTS), Pillow, NumPy, imageio-ffmpeg from PyPI.
- Debian package mirror inaccessible under outbound allowlist. bpy's linked display libraries are missing. Headless-only no-op UI link shims permit background CPU Cycles; not suitable for interactive Blender/Eevee. Actual Cycles test render succeeded. See bootstrap script for details.
- GitHub Actions administrative permissions endpoint returned HTTP 403. Subsequent workflow list/read calls and a source push succeeded; the distributed CPU workflow has been started. Real OS display-link libraries are installed on runners; sandbox UI shims are not used remotely.

## Delivery standards
Native 1080p, no reference-photo projection, actual 3D reflections and camera parallax. All procedural geometry/materials editable and no external commercial asset dependencies. This is an artistic reconstruction, not a photogrammetric or pixel-exact reproduction.
