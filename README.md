# Alpine Mirror

A CPU-rendered, procedural Blender reconstruction of the supplied alpine-lake reference. The photograph is used for art direction only: mountains, forest, shore, water, boulders, grass and lupines are 3D geometry with procedural materials.

## Requested delivery

- `output/Alpine_Mirror_1080p_20s.mp4` — **1920×1080, 24 fps, 480 natively rendered frames, 20 seconds**, H.264, silent.
- `output/Alpine_Mirror_1080p.png` — higher-sample full-HD hero still.
- `output/Alpine_Mirror.blend` — editable Blender 4.2 LTS scene, including camera and ripple animation.
- `output/delivery_validation.json` — full-movie decode validation, created **only after the render and encode succeed**.

**The source and workflow existing do not mean the full animation has finished.** Check the Actions run and the actual deliverable files. Technical validation does not certify photorealism or exact reference matching; artistic review is a separate gate.

## Rebuild locally

Use Blender 4.2 LTS with its Python environment, or Python 3.11 on Linux:

```bash
pip install -r requirements.txt
python scripts/build_scene.py --preview
python scripts/validate_scene.py
python scripts/render_frames.py --start 1 --end 480 --samples 64 --threads 4
python scripts/render_frames.py --only 240 --still --samples 192 --threads 4
python scripts/encode_verify.py
```

Install the normal OS dependencies for the PyPI `bpy` module: `libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libice6 libgl1`.

In this network-restricted, display-less sandbox only, `python scripts/bootstrap_headless.py` supplies uncalled display-link shims. Then prefix rendering commands with:

```bash
LD_LIBRARY_PATH=$HOME/tools/headless-libs OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python scripts/build_scene.py --preview
```

Those shims are **not** for UI, Eevee, OpenGL or GPU use. GitHub runners use real OS libraries, not shims.

## Rendering and recovery

`render_frames.py` validates and skips already-complete PNGs; interrupted frames are written to temporary filenames and are not considered finished. All animation frames are rendered at native resolution; no upscaling, frame duplication or optical-flow interpolation is used. Cycles CPU, adaptive sampling, OpenImageDenoise, AgX color management, dielectric water and geometric instancing keep the scene within a small RAM budget.

The workflow `.github/workflows/alpine-render.yml` builds the scene once, distributes 480 frames over 48 ten-frame CPU jobs (at most 20 in parallel), renders the hero still separately, then assembles and fully decodes the MP4 for verification. It publishes compact requested deliverables only on `arena/f0bb5c2d-testrepo`; temporary PNG sequences remain short-retention Actions artifacts, not Git files. The workflow is intentionally restricted to this session branch.

Final output binaries are normally ignored. The publishing job explicitly adds only the requested compact `.blend`, PNG, MP4 and small validation manifests for durable delivery; raw sequences, caches and logs never enter Git.

## Art and provenance

See [production brief and hardware audit](docs/PRODUCTION_BRIEF.md) and [QA notes](docs/QA.md).

The MIT-licensed **94 Blender skills** from [`arjun988/blender-skills`](https://github.com/arjun988/blender-skills), revision `8f778d2405a214b508d4c7d80742be8e43acdd52`, are installed in `.claude/skills`; license retained in `.claude/BLENDER_SKILLS_LICENSE`. Direct `bpy` execution is used because no Blender MCP endpoint is available.

The environment uses seeded procedural geometry/materials, including hydraulic erosion, actual mesh needles and linked spruce instances. No commercial assets, external textures, generated-image substitutes, reference backplates or hidden photo projections are used.
