# MCP_REFERENCE — Universal Game Engine

## Overview
The MCP server exposes the same underlying core API as the CLI. It is implemented in Python and communicates over stdio. It does NOT independently reimplement every operation.

## Invocation
```
python -m universal_engine mcp [--help]
```
Serves MCP on stdin/stdout.

## Security boundaries
- No dangerous unrestricted system execution as a default capability.
- Sensible permissions; file access scoped to the project directory where feasible.
- Long-running tasks report status and support cancellation where feasible.
- Preview artifact access exposed as resources when appropriate.

## Potential tools (designed; not implemented)
project_create, project_inspect, project_validate, scene_create, scene_inspect, scene_modify, object_create, object_inspect, object_modify, mesh_generate, material_create, terrain_generate, asset_import, asset_inspect, asset_optimize, physics_configure, physics_simulate, physics_test, script_create, script_edit, script_validate, game_run, game_stop, preview_capture, preview_inspect, performance_profile, test_run, game_build.

## Tool schema conventions
- Typed input schemas (JSON Schema).
- Structured responses.
- Tool errors (code + message, no fake successes).
- Project context carried across calls.
- Operation status for long-running tasks.

## Status
MCP server: PLANNED (mcp_server.py scaffold only; no working MCP server yet). Not claimed as working.
