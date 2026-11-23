# DEPENDENCIES — Universal Game Engine

## Platform dependencies (implemented here)
- Python 3.11+ (runtime for CLI + MCP server) — installed in this environment (3.11.2)
- Standard library only for the CLI scaffold (no third-party Python packages required at this stage)

## External technologies (NOT bundled; used via adapters when installed)
| Technology | Role | License | Status in this env |
|------------|------|---------|--------------------|
| Blender | 3D authoring foundation (bpy, headless) | GPL-2.0+ | NOT INSTALLED — cannot install (no root, no blender.org) |
| Godot 4 | Primary game runtime | MIT | NOT INSTALLED |
| glTF / GLB | Asset exchange format | open spec | n/a (format, not code) |
| Godot Physics | Primary physics (in Godot) | MIT | NOT INSTALLED |
| Jolt Physics | Candidate physics adapter | MIT | NOT INSTALLED |
| Bullet | Physics alternative | zlib* | NOT INSTALLED |
| Box2D | 2D physics alternative | MIT | NOT INSTALLED |
| Rapier | Physics alternative (Rust) | Apache-2.0 | NOT INSTALLED |

\* Bullet license noted as zlib in some sources and GPL in community discussions; verify before any use.

## Dependency policy
- No external engine code is copied into this repository.
- Adapters interface with externally-installed tools (Blender, Godot, physics libs) only when those tools are present.
- A project uses only the components it needs; no backend is required to be installed.
- Third-party notices are maintained in THIRD_PARTY_NOTICES.md and LICENSES/.

## Verified dependencies in this environment
- Python 3.11.2 (stdlib) — VERIFIED
- Node.js v22.22.3 / npm — present, not required by the Python platform
- Blender — ABSENT
- Godot — ABSENT
