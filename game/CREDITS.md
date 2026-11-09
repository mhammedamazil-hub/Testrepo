# Alpine Mirror — credits and provenance

- Game: original Alpine Mirror walking/driving prototype created for this repository. No GTA characters, brands, models, music or proprietary game assets are included.
- Terrain: sampled directly from `output/Alpine_Mirror.blend`, SHA-256 `ef72c7f780af86dd6b89a07ae13aab9970d485ed782e835c19061c57b343dfc3`. The cinematic source is preserved, not overwritten.
- Mountain/ground materials: CPU-baked from that original Blender scene. See `assets/asset_manifest.json` and `tools/game/build_assets.py`.
- Vegetation: original scene spruce, CPU-rendered to a distant-tree cutout; original tree placements adapted to the road. Distant trees are billboard impostors; the close roadside subset uses spatial needle-bough card LODs, not thousands of cinematic needle meshes.
- Car, character, skeleton, animation clips and procedural sounds: generated specifically for this prototype using Blender/Python. Vehicle design is non-branded. Characters are simplified, not photoreal digital humans.
- Sky: **Kloofendal 48d Partly Cloudy**, Greg Zaal / Poly Haven, CC0. https://polyhaven.com/a/kloofendal_48d_partly_cloudy . Resized from the already-provenanced sky in `assets/` at repository root.
- Runtime: **Godot Engine 4.4.1**, MIT. See `licenses/GODOT_LICENSE.txt` and `licenses/GODOT_COPYRIGHT.txt`, also copied into the downloadable Web export.
- Authoring: Blender 4.2.23 / bpy; Blender itself is not bundled with the playable Web game.
- Specialist guidance: arjun988/blender-skills (MIT; repository root `.claude/BLENDER_SKILLS_LICENSE`), the local realistic-production guide, and wshobson/agents Godot patterns (MIT; `.claude/GODOT_SKILLS_LICENSE`). Pinned source metadata is retained in the repository.

The engine and asset tools do not make this a Rockstar product or imply endorsement. See the project README for tested behavior, unfinished work and performance limitations.

## Photographic grass surface

`assets/grass_surface.jpg` derives from **Dark grass**, by **Blender Foundation
(2009), Lamoot (2009), and qubodup (2010)**. Original:
https://opengameart.org/content/dark-grass . Licensed **Creative Commons
Attribution 3.0 Unported**: https://creativecommons.org/licenses/by/3.0/ .
Retrieved through the three.js terrain example at pinned commit
`9c4515e66f479864e39b72f29e10260821576b4a`; its terrain readme retains the same
license. Changes: resized to 1024px, JPEG recompression, saturation reduced to
72%. This attribution and source/license links must travel with redistribution.
Exact source blob and hashes: `assets/grass_surface.provenance.json`.

The new unbranded touring car, spatial branch-card spruce LOD, meadow tufts, granite
mesh, detail maps and lake reflection capture are authored for this project
with Blender/bpy. The lake capture is a **static reflection approximation** of
the actual terrain, not a real-time planar reflection. Nearby spruce foliage
uses economical 3D-arranged branch cards with a CPU-rendered needle atlas; distant trees remain billboards.

## Poly Haven vegetation library — new Alpine framework

**Powered by Poly Haven.** The following actual downloaded assets are CC0-1.0:
- Grass medium 01 — Rob Tuytel (photography), Rico Cilliers (processing): https://polyhaven.com/a/grass_medium_01 . Real `tiny_a_LOD0` geometry, 79 triangles, normalized to 0.42m; alpha mask combined with diffuse.
- Pine tree 01 — Rob Tuytel and Rico Cilliers: https://polyhaven.com/a/pine_tree_01 . Photographic twig diffuse/opacity adapted onto our 412-triangle branch-card tree. The 17M-triangle source scan is **not** included.
- Pine bark — Dimitrios Savva: https://polyhaven.com/a/pine_bark . Photographic bark color and GL normal maps.
- Leafy grass — Charlotte Baglioni: https://polyhaven.com/a/leafy_grass . Ground diffuse, GL normal and ARM maps.

Source URLs, original hashes and authors: `docs/research/library-catalog.json`; compiled asset hashes and exact adaptation: `assets/library/manifest.json`. Asset CC0 licensing is distinct from the Poly Haven API server's software license.

The second playable variant is the original **Alpine 0.1 framework**, using Three.js (MIT), Rapier (Apache-2.0), and postprocessing (Zlib). Complete dependency notices accompany that distribution in `world/credits.txt`. Its shafts are screen-space depth-occluded scattering, not full volumetric path tracing; water uses a current-frame reflected camera, not ray tracing.

## Alpine: After Dark — supplied Roadster and photographic night sky

- **Tesla Roadster 2020**, by **metarex.4d** (https://sketchfab.com/metarex.4d), supplied by the repository owner as `roadster_lite.glb`. Embedded source: https://sketchfab.com/3d-models/tesla-roadster-2020-1fbf29e297bd4a17ac39a00a378441d8 . **CC-BY-4.0**, https://creativecommons.org/licenses/by/4.0/ . Modifications: normalized ground/forward basis, grouped body/rotating wheels/calipers, bounded decimation, delivery textures capped to 1024, clearcoat/lamp-emission changes. Source binary unchanged; source/output hashes and measured geometry are in `world/roadster/model.json` in the custom game. Model credit is based on the supplied file's embedded asset metadata. Tesla trademarks remain their owners'; no endorsement or manufacturer-certified simulation is implied.
- **Satara Night**, actual Milky Way/star photography by **Greg Zaal / Poly Haven**, **CC0-1.0**: https://polyhaven.com/a/satara_night . Source MD5 and SHA256 verified; image resized to 4096x2048 and lower hemisphere feathered to remove village/ground backplates. Original/output hashes and exact modifications ship in `world/night/provenance.json`. **Powered by Poly Haven**. Night exposure and moonlight are art-directed for readable driving, not an astronomy simulation.
- Roadster dynamics: actual Rapier dynamic rigid body with four raycast suspension/tire contacts. The 2200 kg mass, 800 kW power, spring/damper, tire and aero values are explicit engineering estimates; historical concept performance claims are not independently validated current specifications. No manufacturer-validated thrusters, suction fans, real vehicle telemetry, full tire deformation or manufacturer affiliation. Optional game flight is separately labelled fiction.
- UI is inspired by premium PC game launchers; no Steam branding, reviews, player counts or account integration is included. Link preview uses a real captured launch screen, not generated promotional art.

## Beyond the Road / original additions

- Original procedural tapered grass blades, deterministic placements, GPU wind, lobby/HUD controls and fictional flight mechanics are project code, not additional third-party scans or manufacturer engineering. Existing licensed photographic grass remains. Meadow placement hashes/seed and graded-terrain source hash ship in `world/meadow/provenance.json`.
- Flight is an optional fictional game mechanic using forces/torques, finite boost and assisted landing; it is not a Tesla-certified flight system, manufacturer ADAS or real aircraft model. Driving estimates remain separately disclosed.
- Rocket League was a UI-direction reference only. No Rocket League assets, logos, accounts or services are used. AI-generated design references are clearly labelled in the repository and are not used as actual-game/social screenshots.

## Short Hop / Time Attack (v0.5)

- Original procedural circuit kerbs, checker start paint, gantry lettering, corner boards, reflectors and 128² asphalt-detail texture are generated by project code. Existing asphalt/source textures remain. No added licensed race-game assets, copied logos or dynamic lights.
- Supersedes v0.4's indefinite hover: finite gas is shared across lift/boost/braking/stabilization, cannot refill aloft and is not restored by engagement. Six seconds maximum powered use, auto descent after 2.8 seconds and 20 seconds ground refill are **game-balance choices**, NOT Tesla-published duration or compressor data. The official Roadster cold-gas description informed the short-hop direction only; no final manufacturer pressure/flow/inertia model was verified. See `docs/research/short-hop-and-time-attack.md`.
- Sector/PB medals and game-only gas mechanics do not imply manufacturer affiliation, validated stunt safety, public-road legality or aircraft certification.
