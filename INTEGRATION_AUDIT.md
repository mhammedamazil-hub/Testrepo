# INTEGRATION_AUDIT — Universal Game Engine

## Policy
- No code is copied from incompatible projects.
- No source is merged merely because a repository is public.
- Preference: official libraries → proper dependency integration → compatible open-source components → clean-room implementations → documented/attributed algorithmic knowledge.
- Every integration must have a reason to exist.
- No fake functionality, simulated integrations, or placeholder implementations disguised as completed features.

## Integration status
| Integration | Reason | License compatibility | Status |
|-------------|--------|----------------------|--------|
| Blender (bpy) adapter | Central 3D authoring; scene/asset creation | GPL-2.0+ — Blender used as external tool, not linked | BLOCKED (Blender not installed) |
| Godot 4 adapter | Primary game runtime | MIT — compatible | PLANNED (Godot not installed) |
| glTF/GLB exchange | Blender → Godot asset pipeline | open spec | PLANNED |
| Godot Physics | Physics tied to runtime | MIT — compatible | PLANNED |
| Jolt Physics | Candidate headless/dedicated-server physics | MIT — compatible | PLANNED |

## Third-party code copied into this repo
None. All external technologies are referenced by name/URL/license only; no source code copied.

## Attribution
See THIRD_PARTY_NOTICES.md and LICENSES/.
