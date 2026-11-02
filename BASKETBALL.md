# Photoreal basketball

A size-7 basketball built from a parametric surface, with a photographed-then-synthesised pebble leather
cover, real seam grooves cut into the mesh, and a full PBR texture stack (base colour / normal / ORM) that
survives the trip into a glTF viewer.

Everything is offline and free: no GPU, no service, no model weights. **Cost: $0.**

![the ball](basketball/renders/ball_00.png)

| | web tier | high tier |
|---|---|---|
| GLB | [`basketball/model.glb`](./basketball/model.glb) — **3.07 MB** | [`basketball_high/model.glb`](./basketball_high/model.glb) — **9.98 MB** |
| geometry | watertight closed shell (0 boundary edges), 241.9 mm | ditto, 4× denser |
| triangles | 20,480 | 81,920 |
| PBR maps | 2048² base colour + normal + ORM (JPEG q92/95) | 4096², same three |
| OBJ / MTL | `model.obj`, `model.mtl` (external maps) | — |
| print STL | `print_mm.stl`, 241.9 mm diameter, watertight | `print_mm.stl` |
| build time | 6 s | 22 s |
| renders | `basketball/renders/` — 5 views, contact sheet, `turntable.gif` | same, from the 4k maps |

## 1. Dimensions

| property | value |
|---|---|
| diameter | **241.9 mm** (spec 241.3–242.6 mm for a size 7) |
| circumference | 760.3 mm (spec 749–780 mm) |
| seam channel | 5.2 mm wide, **1.9 mm deep** — a real groove in the mesh, not a painted line |
| pebble pitch | 2.1 mm, 24,000 pebbles |
| pebble relief | 0.34 mm crease-to-crown, carried by the normal map |
| panels | 8, from four great circles through two antipodal pinch points |

## 2. Why it is built this way

The first attempt at a cover was "generate a macro photo of leather and tile it". That failed visibly, twice:

* tiled 17×8 around the ball, the photograph's own pebbles were 3× too coarse and the repeat seams met in
  visible strips — it read as **fabric**, not basketball leather;
* minified into a 2 k map, the grain collapsed into **moire**.

So the grain is *synthesised on the sphere* (`tools/pebble_field.py`): 24,000 jittered sites, one softly
domed bump each, with per-pebble variation in size, depth and flatness. Because it is defined in 3D it wraps
with no seam anywhere, and because it is a nearest-site field it stays isotropic even where the
equirectangular map stretches near the poles. The generated leather photograph still earns its place — it is
blurred to a soft tonal field and used only for slow colour variation, where nothing has to line up.

The seams are analytic: four great-circle planes through the pinch axis. The distance to the nearest plane
drives the groove depth in the *mesh*, the black rubber in the *albedo*, the channel shading in the *normal
map* and the contact darkening in the *AO* — one function, four maps, so they cannot drift out of register.

## 3. What makes it read as real

* **Specular response.** GGX with a roughness map, Fresnel-weighted, two lights plus a studio environment —
  this is what separates "brown sphere" from "ball". The `.glb` ships roughness/metallic/occlusion, so any
  PBR viewer gets the same response.
* **Relief.** Pebble crowns and seam channels are in the normal map; the seam channels are *also* in the
  geometry, so the silhouette at the seam is not perfectly round.
* **Studio lighting in the preview.** `tools/ball_render.py` ray-traces the displaced surface with a warm key,
  cool fill, rim, environment reflection, floor bounce and a contact shadow anchored on the ball's own
  silhouette.
* **Framing.** Shot across the equator, not down a pinch pole — down the pole the four seams meet at the dead
  centre and the pattern reads as a beach ball.

![turntable](basketball/renders/turntable.gif)

## 4. Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install numpy scipy pillow trimesh

.venv/bin/python tools/basketball.py --out basketball       --tier web    # 6 s
.venv/bin/python tools/basketball.py --out basketball_high  --tier high   # 22 s

.venv/bin/python tools/ball_render.py --maps basketball --out basketball/renders \
        --size 900 --ss 3 --views 5                                        # 40 s
```

`basketball_src/leather_tile.png` (macro leather) and `basketball_src/reference.png` (studio product shot)
are the generated source images; the first feeds the tonal variation, the second is the look reference.

## 5. Six bugs found while building this

1. **`np.run`-style striding bug in the UV split**: a per-face mask indexed a per-corner array without a
   `[:, None]`, so the seam split silently corrupted vertex mapping.
2. **Tiling a photographed macro** gave fabric-like stripes (see §2) — the single biggest visual defect, and
   the reason the grain is now synthesised.
3. **Albuming the pebble relief three times** (albedo × AO × normal) inked an outline around every pebble:
   at extreme zoom the cover looked like a diagram of cells. Fixed by softening the crease profile *and*
   keeping depth in the normal map, not in the colour.
4. **A hard wall/floor step** in the backdrop rendered as a grey bar across the frame; replaced with a
   smoothstep sweep.
5. **Uncompressed maps**: three 2 k PNGs made a 20 MB GLB. JPEG at q92/95 plus `img.format = "JPEG"` (trimesh
   re-encodes to PNG otherwise) brings it to **3.07 MB**.
6. **The 4096² bake was killed by the OOM reaper** in this 3.8 GB sandbox, silently producing an empty
   directory. The bake is now done in 512-row strips.
7. **The UV seam split left the ball open.** Duplicating the vertices either side of the u wrap is what makes
   the texture seam clean, but it also creates 320 boundary edges - the exported mesh was *not* watertight
   even though the welded sphere was. Fixed by letting `process=True` weld the duplicates back, then
   re-evaluating UVs from the final vertex positions (carrying them over by index instead silently pushed
   them past 1.0). Verified: 0 boundary edges either tier.

## 6. Honest limits

* The cover is **generated**, not a scanned ball: no brand, no printed logo, no worn patches. It is a clean,
  new, unbranded size-7 ball.
* The seam grooves are cut into the geometry but the ball is a single closed shell — a real ball's seams are
  rubber channels between separate leather panels, which needs a much denser mesh to resolve.
* Colour and roughness are authored to match the reference photograph, not measured from it.
