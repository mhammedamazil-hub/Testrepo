# Modern Villa — fully furnished, procedurally built in Blender

A 19.0 × 12.5 m single-storey modern villa: 3 bedrooms + 2 bathrooms, open-plan
living / dining / kitchen, fully furnished and styled, rendered with real path
tracing, exported as a walkaround GLB plus 121 individually named, pivoted
furniture GLBs.

Everything is generated from source — no downloaded models, no paid services, no
GPU. Total cost **$0**.

---

## Deliverables

| File | What it is |
|---|---|
| `villa/villa.blend` | Editable Blender scene (all geometry, materials packed, lights, cameras) |
| `villa/villa.glb` | Whole-house walkaround model, PBR materials, 1024² textures |
| `villa/furniture/*.glb` | **121 pieces**, one file each, named by room + piece, pivot at the footprint centre on the floor, front facing **−Y** |
| `villa/manifest.json` | Every piece with its kind, pivot and rotation; room rectangles; scene counts |
| `villa/renders/*.png` | 12 hero stills, 1280 × 720, Cycles + OIDN (+ `contact_sheet.png`) |
| `villa/walkthrough.mp4` | 10 s camera fly-through, entry → foyer → kitchen → dining → living (512×288, 15 fps, + `walkthrough.gif`) |
| `villa/tex/` | The generated PBR texture set (regenerable, see below) |

### Numbers

| | |
|---|---|
| Footprint / height | 19.0 × 12.5 m · 3.0 m ceilings · 237.5 m² under roof |
| Rooms | 14 spaces (see plan) |
| Scene | 484 objects · 121,770 polygons · 40 materials |
| Furniture | 121 placed pieces from 41 parametric builders |
| Textures | 77 procedural maps (albedo + normal + roughness), 1024², tileable |
| Whole-house GLB | 20.2 MB, 1024² textures |
| Furniture GLBs | 121 files, 25.8 MB total, 512² textures |
| Stills | 12 × 1280 × 720 @ 32 spp, ~2.5 min each on 2 vCPU |
| Collision check | 0 furniture/furniture or furniture/wall intersections |

## The plan

```
y=12.2 ┌──────────┬──────┬──────────┬────────┬──────┬─────────┐
       │  MASTER  │robe/ │ BEDROOM 2│laundry/│BED 3 │  STUDY  │
y= 7.85│  BED     │ensui.│          │ bath 2 │      │         │
       ├──────────┴──────┴──────────┴────────┴──────┴─────────┤
y= 6.55│                  CORRIDOR                            │
       ├──────────────────────────┬───────────┬──────────────┤
       │   LIVING    │   DINING   │  KITCHEN  │ utility/foyer│
y=  0  └─────────────┴────────────┴───────────┴──────────────┘
        x=0                                           x=19.0
```

* 3.0 m ceilings, flat roof with a 1.8 m south overhang and a black fascia band.
* 12 m of full-height sliding glazing to the south terrace; fixed windows to the
  north bedrooms; a west picture window.
* Rooms: living, dining, kitchen, utility, foyer, corridor, master suite
  (bedroom + walk-in robe + ensuite), bedroom 2, laundry, family bathroom,
  bedroom 3, study.

## How it is built

| Module | Responsibility |
|---|---|
| `villa_src/tex_gen.py` | Procedural PBR textures with numpy — wood (planks, veneer, walnut), plaster, micro-cement, marble with warped iso-line veining, large-format limestone, bathroom tile, linen/bouclé/velvet weaves, leather, wool rugs with a woven border, foliage, lawn, brushed metals, and four abstract art prints. Output: albedo + normal + roughness, 1024², tileable. |
| `villa_src/mats.py` | Material library. Every material is a Principled BSDF fed by those images, so **Cycles and glTF show the same thing** (glTF cannot carry procedural shader nodes). |
| `villa_src/kit.py` | Geometry toolkit — bmesh primitives, edge bevels, lathes, extrusions, leaf blades, meters-based box UV projection, join-with-baked-transform, origin control. |
| `villa_src/shell.py` | Floor plan → walls with openings, glazing + black aluminium frames, doors, per-room floors, ceiling, roof, site (terrace, lawn, pool, drive). |
| `villa_src/furniture.py` | 39 parametric pieces: sofa, armchair, dining chair, stool, tables, desk, sideboard, console, TV unit, bookshelf, wardrobe, shelving, bed, bench, nightstand, kitchen runs, island, wall cabinets, tall unit, hood, vanity, toilet, shower, bath, mirror, washer/dryer, rug, art, vase, bowl, books, candle, plants, trees, curtains, pendants and lamps. |
| `villa_src/layout.py` | Places all 120 pieces, room by room. |
| `villa_src/lighting.py` | Physical sky (multiple-scattering), a matched sun lamp, recessed ceiling downlights with emissive lenses, soft fill lights, exterior planting. |
| `villa_src/diagnose.py` | Automated AABB collision report (furniture↔furniture, furniture↔wall, out-of-envelope). Used to drive the layout to **0 collisions**. |
| `villa_src/render_stills.py` | Renders the 12 stills. |
| `villa_src/walkthrough.py` | Catmull-Rom camera path → PNG frames → ffmpeg MP4/GIF. |
| `villa_src/export.py` | `.blend`, whole-house GLB, per-piece GLBs (textures downscaled to 512² for the piece set). |

### Texture and UV conventions

Every texture repeats over a fixed physical size (e.g. oak floor = 2.4 m per tile),
and every face gets a box-projected UV in metres, so grain and stone scale are
correct across the whole house and in every exported GLB.

### Rebuild

```bash
python3 -m venv .venv
.venv/bin/pip install bpy numpy pillow trimesh imageio-ffmpeg      # bpy 5.0.1
python3 tools/blender_stub.py                                     # headless X/GL stubs
.venv/bin/python villa_src/tex_gen.py                             # 74 texture maps (~30 s)
LD_LIBRARY_PATH=$PWD/.glstub .venv/bin/python villa_src/build_all.py
LD_LIBRARY_PATH=$PWD/.glstub .venv/bin/python villa_src/render_stills.py
LD_LIBRARY_PATH=$PWD/.glstub .venv/bin/python villa_src/walkthrough.py
```

`tools/blender_stub.py` builds the no-op X11/GL shim that lets the `bpy` wheel run
in a container with no X libraries — only X/GL symbols are stubbed, because stubbing
everything makes Blender segfault.

## Technical notes

* **Renderer**: Cycles, CPU, 2 vCPU / 3.9 GB. Stills: 1280 × 720, 32 spp with
  adaptive sampling + OpenImageDenoise, AgX view transform.
* **Scale**: everything is in metres, 1:1, floor at z = 0, ceiling at z = 3.0.
* **Furniture pivots**: each piece is authored around the centre of its footprint
  on the floor, facing −Y, so it drops onto a floor plan without surprise offsets.
  `manifest.json` records the placed pivot and rotation.
* **Materials in glTF**: albedo + normal + roughness maps are exported as real
  textures; metallic/roughness factors and IOR/transmission come through as glTF
  material parameters, so the GLB matches the renders.
* **Emissive fixtures** (pendant bulbs, downlight lenses) are separate small
  emissive geometry, so they read correctly in any glTF viewer.
