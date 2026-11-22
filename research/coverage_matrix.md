# Research Coverage Matrix

Tier 1 (deep, directly relevant): Godot, Bevy, Blender, UPBGE, Godot Physics, Jolt Physics.
Tier 2 (documentation + selective source): Panda3D, Bullet, Box2D, Rapier.
Tier 3 (catalog only — not individually researched unless a decision requires it): O3DE, Flax, Stride, Wicked Engine, OGRE, Urho3D, Armory, Defold, Cocos, PlayCanvas, Babylon.js, Three.js, Unity-related open-source tools, Unreal-related open-source tools, GDevelop, GameMaker alternatives, LÖVE, MonoGame, FNA, SDL, Pygame, Arcade, Raylib, Macroquad, ggez, Ebiten, Piston, Amethyst, Fyrox, Korge, Kivy game tech, Excalibur.js, Phaser, MelonJS, HaxeFlixel, OpenRA, Xash3D, VCMI, Minetest/Luanti, Hex Engine, Nazara Engine, RaZ Engine, Halley, Ambient, microStudio, Noa, NFluids, and other projects discovered during research.

| Area | Tier 1 researched | Tier 2 researched | Tier 3 cataloged | Decision made |
|------|-------------------|-------------------|------------------|---------------|
| Runtime engine | Godot, Bevy, Blender(authoring), UPBGE | Panda3D | — | Godot (D-01) |
| Authoring foundation | Blender | — | — | Blender (D-06, BLOCKED in env) |
| Physics (3D) | Godot Physics, Jolt | Bullet | Box2D, Rapier | Godot Physics primary (D-04), Jolt candidate |
| Physics (2D) | — | Box2D | — | Box2D documented |
| Rendering | Godot (Vulkan/GL), Blender (EEVEE/Cycles) | Panda3D | OGRE, Urho3D, Three.js, Babylon.js | Delegated to Blender/Godot adapters |
| Scripting | GDScript, Python | — | Lua, JavaScript, WASM, C#, Rust | GDScript runtime + Python platform (D-05) |
| Asset pipeline | glTF/GLB (Blender/Godot) | — | FBX, OBJ, USD | glTF/GLB canonical (D-02) |
| Audio | Godot AudioServer, Blender Audaspace | — | OpenAL | Delegated |
| Networking | Godot multiplayer (ENet/WebRTC/WebSocket) | — | — | Delegated to Godot |
| AI / NPC | — | — | behavior trees, navmeshes, LLM NPCs | PLANNED |
| Licensing audit | Godot, Bevy, Blender, UPBGE, Panda3D, Jolt, Bullet, Box2D, Rapier | — | — | IN PROGRESS |

Gaps: source-level code review of Godot/Bevy/Blender (no clones in this env yet — github clones are network-allowed); hands-on experimentation; benchmarks.
