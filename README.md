# Alpine Mirror

**Revision 2 is in visual review:** 20 seconds, 1920×1080, **60 fps / 1,200 native frames**, rising lake-drone flight, backlit morning, deeper foliage, breezy water and distant birds. The full animation is gated on look approval; see [revision brief](docs/REVISION_2.md). Until the new render completes, the existing MP4 and delivery report are the previously delivered **24-fps revision 1**, not a completed 60-fps revision.

A CPU-rendered, procedural Blender reconstruction of the supplied alpine-lake reference. The photograph is used for art direction only: mountains, forest, shore, water, boulders, grass and lupines are 3D geometry with procedural materials.

## Previously completed revision-1 delivery (24 fps)

- `output/Alpine_Mirror_1080p_20s.mp4` — **1920×1080, 24 fps, 480 natively rendered frames, 20 seconds**, H.264, silent.
- `output/Alpine_Mirror_1080p.png` — higher-sample full-HD hero still.
- `output/Alpine_Mirror.blend` — editable Blender 4.2 LTS scene, including camera and ripple animation.
- `output/delivery_validation.json` — full-movie decode validation, created **only after the render and encode succeed**.

**Render completed:** [successful CPU render run](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42077709412). All delivery files above are present. An independent sandbox decode verified 480 unique decoded frame hashes, 1920×1080, 24 fps, exactly 20.0 seconds, and a scene SHA-256 matching the delivered Blender file. See `output/independent_verification.json`.

**Quality disclosure:** the result is a procedural CG reconstruction, not an ultra-photoreal/AAA-approved match to the supplied photograph. Foliage, geology, snow and composition still differ; technical completion is not artistic approval.

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
