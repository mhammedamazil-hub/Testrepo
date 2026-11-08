# Alpine Mirror — credits and provenance

- Game: original Alpine Mirror walking/driving prototype created for this repository. No GTA characters, brands, models, music or proprietary game assets are included.
- Terrain: sampled directly from `output/Alpine_Mirror.blend`, SHA-256 `ef72c7f780af86dd6b89a07ae13aab9970d485ed782e835c19061c57b343dfc3`. The cinematic source is preserved, not overwritten.
- Mountain/ground materials: CPU-baked from that original Blender scene. See `assets/asset_manifest.json` and `tools/game/build_assets.py`.
- Vegetation: original scene spruce, CPU-rendered to a distant-tree cutout; original tree placements adapted to the road. These are billboard impostors, not thousands of full-detail animated trees.
- Car, character, skeleton, animation clips and procedural sounds: generated specifically for this prototype using Blender/Python. Vehicle design is non-branded. Characters are simplified, not photoreal digital humans.
- Sky: **Kloofendal 48d Partly Cloudy**, Greg Zaal / Poly Haven, CC0. https://polyhaven.com/a/kloofendal_48d_partly_cloudy . Resized from the already-provenanced sky in `assets/` at repository root.
- Runtime: **Godot Engine 4.4.1**, MIT. See `licenses/GODOT_LICENSE.txt` and `licenses/GODOT_COPYRIGHT.txt`, also copied into the downloadable Web export.
- Authoring: Blender 4.2.23 / bpy; Blender itself is not bundled with the playable Web game.
- Specialist guidance: arjun988/blender-skills (MIT; repository root `.claude/BLENDER_SKILLS_LICENSE`), the local realistic-production guide, and wshobson/agents Godot patterns (MIT; `.claude/GODOT_SKILLS_LICENSE`). Pinned source metadata is retained in the repository.

The engine and asset tools do not make this a Rockstar product or imply endorsement. See the project README for tested behavior, unfinished work and performance limitations.
