# Mountain / UI workshop — v7 work in progress

**This is an implementation-in-progress and reference review, not a finished
photorealism release.** The generated concepts are more realistic than the current
runtime. They are explicitly labelled in the workshop and are not used to fake
screenshots or as a mountain backdrop texture.

## Pages publication

The workshop is published at [design.html](https://mhammedamazil-hub.github.io/Testrepo/design.html).
The existing solo home remains the root page. The local mountain test-drive
entry is [multiplayer.html?practice=1](https://mhammedamazil-hub.github.io/Testrepo/multiplayer.html?practice=1).
The deployment workflow checks the workshop bundle, all ten references and the
Blender GLB hash after publication. These are static-host smoke checks, not a
public WebRTC or photorealism certificate.

## Open the live build

```sh
npm run signal --prefix engine       # only needed for actual local multiplayer
ALPINE_WORKSHOP=1 npm run dev --prefix engine -- --port 3003
```

The Arena preview on **3003** opens the Visual Workshop at `/`. Normal Vite on
3001 continues to open the existing solo game. Both also serve:

- `/design.html`: actual full-quality Roadster, live paint/name selection, orbit
  camera, and ten generated design references. No network/login required.
- `/multiplayer.html?practice=1`: choose graphics/name, then **EXPLORE MOUNTAIN
  BUILD** for a clearly labelled local solo test drive. It uses real Rapier and
  host gate rules but no signalling and no fake opponents. This is not a room.
- `/multiplayer.html`: the real create/join multiplayer flow remains available.

The workshop is a prototype of the guest/garage visual language. **The existing
race UI and the other game menus have not all been replaced.** Reference review
comes before a full UI rollout. No new flight mechanic is introduced; multiplayer
remains ground-only. The old solo world/cinematic have not been replaced.

## Reference coverage

All ten files are separately generated AI concept images, not screenshots.
Open an individual image from the workshop gallery for full size.

| File | Target |
|---|---|
| 01-mountain-world.jpg | Alpine limestone/cliffs/talus, layered mountain scale |
| 02-guest-live-car.jpg | Guest name, paint and actual live car preview |
| 03-room-lobby.jpg | Invitation, roster, ready/start, compact chat |
| 04-desktop-race.jpg | Minimal standings, timing, speed, nitro, minimap |
| 05-mobile-race.jpg | Portrait driving HUD and safe touch control zones |
| 06-track-map.jpg | Full circuit map and gate/pickup information |
| 07-race-results.jpg | Results, penalties, rematch/leave |
| 08-settings.jpg | Graphics, controls, audio/accessibility layout direction |
| 09-pause-connection.jpg | Online controls-released / connection treatment |
| 10-solo-home-garage.jpg | Solo launcher, garage and mode navigation |

**The image tool's ten-image per-turn limit was reached.** Separate loading,
room-ended/error, on-foot exploration and training references remain outstanding.
The settings concept is not a claim that all proposed settings already exist.
The original approved controls/hop behavior are not silently replaced by a mockup.

## What has actually changed

### Render-only spatial visibility and LOD

`engine/src/online/visibility.js` manages conservative bounds, camera-frustum
rejection and distance-based LOD with an 8% exit hysteresis. It runs **after** the
chase camera moves. Physics never belongs to this manager and cannot be disabled
by looking away.

- Terrain is divided into **64 tiles** (300 m each), with three authored levels.
- The background mountain ring has **16 sectors**, three authored levels each.
- Trees are instanced in 300 m cells. Nearby trees use the licensed authored pine
  geometry; middle-distance trees use crossed alpha-tested cards; far trees use
  unlit fogged silhouette cards. The detailed near tree is not drawn at distance.
- Grass uses bounded 100 m cells and a 160 m visibility range.
- Render geometry and physics are separate. The original road/rails and the
  128-segment graded ground collision mesh are unchanged. Track route, gates,
  spawn positions and network map ID stay compatible.

This first pass is on the **Grand Prix world**, not a claim that every legacy solo
object has been spatially chunked. Three.js's ordinary per-object frustum culling
continues. It is **not hardware occlusion culling**: objects behind a mountain but
inside the frustum can still render. All LOD levels are loaded into memory;
this is not asynchronous world streaming.

### Actual Blender authoring

Consulted repository skills: `environment-artist`, its composition guide,
`blender-modeler`, and `asset-optimization` / LOD strategies. No Blender MCP tool
is connected here, so the equivalent authoring operations run through **real bpy
4.3.0**, not a claim that an image generator made a Blender scene.

- Source: `game/assets/mountain/alpine-mountain.blend` (editable metre-space scene).
- Generator: `tools/game/build_mountain.py` and
  `engine/tests/build-mountain-input.js` (samples the shared route/ground).
- Runtime: `engine/public/world/mountain/alpine-massif.glb`, 240 meshes / three
  levels, with a hash/count manifest alongside it.
- Collections: `COL_Geo`, `COL_Reference`, including a 1.7 m scale reference.
- Tile border vertices remain locked at all levels to avoid open LOD cracks.
- Skyline inner edge overlaps the existing ground by 2 m horizontally and 5 m
  vertically; an initial floating-ring gap was found in screenshot review and
  fixed. The manifest records the boundary offset.
- Runtime materials use the existing licensed meadow photograph, world-space
  cliff projection, vertex slope/elevation colour and original procedural rock
  detail. This is not scanned geology or a photogrammetry asset claim.

Rebuild (Python environment with bpy 4.3 and its system libraries):

```sh
python tools/game/build_mountain.py
npm test --prefix engine
npm run build --prefix engine
```

The authoring `.blend` is not shipped in the browser bundle. The GLB and references
are included in the static build. Original uploaded Roadster, original terrain,
solo finite-hop rules and cinematic remain unchanged.

## Validation and honest limits

- Node rules/physics/visibility suite: **54 passing tests**.
- Python release suite: **63 passing tests**.
- Existing multiplayer layout/input isolation: **8 checks passed**.
- Existing solo layout/multitouch: **12 checks passed**.
- Production build includes `index.html`, `multiplayer.html`, `design.html`.
- [Workshop / terrain browser evidence](browser-validation.json): actual paint and
  name changes, mobile/desktop captures, a local physics test drive, five-view
  submitted-geometry A/B and unchanged collider/transform checks.
- [Multiplayer regression](regression/browser-validation.json) retains real local
  PeerJS/WebRTC integration. Public cross-NAT/TURN limitations from v6 remain.

The A/B compares **the same new mountain scene** with full-detail cells selected
versus distance LODs, at the same five cameras. Three.js still frustum-culls in
both modes. It is not an old-v6-versus-v7 FPS benchmark. Submitted triangles and
calls include the car/shadow render passes. Exact figures are in the JSON;
reduced geometry is evidence of reduced geometry work, **not proof of faster
frame time**, physical-phone 60 FPS, or unchanged image quality at every distance.

Screenshots named `live-car-preview*` and `mountain-*` are actual software-WebGL
renders under real DOM UI, unlike images in `references/`. QA uses preserved
buffers and a synchronous canvas image copy to avoid background/resize capture
loss. The normal game does not preserve its drawing buffer.

**Still to do:** bring the terrain's geology, vegetation distribution and close
surface detail up to the reference; evaluate hill occlusion carefully; measure
actual GPU/device frame times; review the UI direction; generate the remaining
four state references and implement the full approved UI set. No photorealism
or final UI approval is asserted by this first pass.
