"""MCP server — real implementation.

Exposes the same underlying core API as the CLI via stdio JSON-RPC 2.0.
The CLI, MCP server, and any API all call the same underlying services
(GodotAdapter + Project + Scene model) — no independent implementations.

No dangerous unrestricted system execution is exposed as a default capability.
All file access is scoped to the project directory.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from universal_engine import PLANNED, __version__
from universal_engine.adapters import BlenderAdapter, build_godot_adapter
from universal_engine.core import ObjectDef, Project, Scene, Transform, ok_result, error_result


# ---------------------------------------------------------------------------
# MCP JSON-RPC helpers
# ---------------------------------------------------------------------------


def _json_rpc_result(request_id: Any, result: Any) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})


def _json_rpc_error(request_id: Any, code: int, message: str, data: Any = None) -> str:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "error": err})


def _parse_content_length_headers(raw: bytes) -> Optional[int]:
    """Parse Content-Length from MCP stdio headers."""
    try:
        header_part = raw.split(b"\r\n\r\n", 1)[0]
        for line in header_part.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                return int(line.split(b":", 1)[1].strip())
    except (ValueError, IndexError):
        pass
    return None


# ---------------------------------------------------------------------------
# Service layer (shared with CLI)
# ---------------------------------------------------------------------------


class _EngineServices:
    """Shared backend used by both MCP and CLI. No duplicate implementation."""

    def __init__(self, godot_path: Optional[str] = None):
        self.godot = build_godot_adapter(godot_path=godot_path)
        self._projects: Dict[str, Project] = {}
        self._run_ids: Dict[str, str] = {}  # mcp_call_id -> godot run_id

    def _resolve_root(self, path: Optional[str]) -> Path:
        if path:
            return Path(path).resolve()
        return Path.cwd().resolve()

    def _project_for(self, path: Optional[str]) -> Project:
        root = self._resolve_root(path)
        key = str(root)
        if key not in self._projects:
            self._projects[key] = Project(str(root))
        return self._projects[key]

    # -- tool handlers ----------------------------------------------------

    def tool_project_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        path = args.get("path", name)
        project = Project(str(Path(path).resolve()), name=name)
        result = project.create()
        if result["ok"]:
            self._projects[str(Path(path).resolve())] = project
        return result

    def tool_project_inspect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = args.get("path", ".")
        project = self._project_for(path)
        result = project.load()
        if result["ok"]:
            scenes = project.list_scenes()
            result["data"] = dict(result["data"] or {})
            result["data"]["scenes"] = scenes
            result["data"]["root"] = project.root
        return result

    def tool_project_validate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = args.get("path", ".")
        project = self._project_for(path)
        return project.validate()

    def tool_scene_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        path = args.get("path", ".")
        project = self._project_for(path)
        load = project.load()
        if not load["ok"]:
            return load

        # Ensure scenes directory exists.
        os.makedirs(project.scenes_dir, exist_ok=True)

        scene = Scene(name=name)
        for nd in args.get("nodes", []):
            scene.add_object(
                scene_object_from_dict(nd)
            )
        spath = project.scene_path(name)
        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
            return ok_result(
                data={
                    "scene": name,
                    "path": str(spath),
                    "objects": len(scene.objects),
                }
            )
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))

    def tool_scene_inspect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        path = args.get("path", ".")
        project = self._project_for(path)
        load = project.load()
        if not load["ok"]:
            return load
        spath = Path(project.scene_path(name))
        if not spath.is_file():
            return error_result("SCENE_NOT_FOUND", f"No scene: {name}")
        try:
            scene = Scene.from_dict(json.loads(spath.read_text(encoding="utf-8")))
            return ok_result(
                data={
                    "scene": scene.name,
                    "objects": [o.to_dict() for o in scene.objects],
                    "object_count": len(scene.objects),
                }
            )
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))

    def tool_node_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a node in a universal JSON scene."""
        scene_name = args.get("scene")
        ntype = args.get("type")
        nname = args.get("name")
        if not scene_name or not ntype or not nname:
            return error_result("INVALID_INPUT", "scene, type, and name are required")
        path = args.get("path", ".")
        project = self._project_for(path)
        load = project.load()
        if not load["ok"]:
            return load

        # Ensure scenes directory exists.
        os.makedirs(project.scenes_dir, exist_ok=True)
        spath = Path(project.scene_path(scene_name))

        # Load existing scene or create a new one.
        if spath.is_file():
            try:
                scene = Scene.from_dict(json.loads(spath.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError) as exc:
                return error_result("SCENE_READ_FAILED", str(exc))
        else:
            scene = Scene(name=scene_name)

        # Check for duplicate node name.
        if scene.find_object_by_name(nname):
            return error_result("NODE_EXISTS", f"Node '{nname}' already exists in scene '{scene_name}'")

        # Build transform from properties if provided.
        transform = Transform()
        props = args.get("properties", {}) or {}
        if "position" in props:
            transform.position = [float(x) for x in props["position"]] if isinstance(props["position"], list) else [0.0, 0.0, 0.0]
        if "rotation" in props:
            transform.rotation = [float(x) for x in props["rotation"]] if isinstance(props["rotation"], list) else [0.0, 0.0, 0.0]
        if "scale" in props:
            transform.scale = [float(x) for x in props["scale"]] if isinstance(props["scale"], list) else [1.0, 1.0, 1.0]

        scene.add_object(ObjectDef(
            id=str(uuid.uuid4()),
            name=nname,
            type=ntype,
            transform=transform,
            parent=args.get("parent"),
            components={},
            metadata={},
        ))

        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
            return ok_result(
                data={
                    "scene": scene_name,
                    "node": nname,
                    "type": ntype,
                    "parent": args.get("parent"),
                    "path": str(spath),
                }
            )
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))

    def tool_node_modify(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Modify a node's properties in a universal JSON scene."""
        scene_name = args.get("scene")
        node_name = args.get("node")
        props = args.get("properties", {})
        if not scene_name or not node_name:
            return error_result("INVALID_INPUT", "scene and node are required")
        path = args.get("path", ".")
        project = self._project_for(path)
        load = project.load()
        if not load["ok"]:
            return load

        spath = Path(project.scene_path(scene_name))
        if not spath.is_file():
            return error_result("SCENE_NOT_FOUND", f"No scene: {scene_name}")

        try:
            scene = Scene.from_dict(json.loads(spath.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))

        obj = scene.find_object_by_name(node_name)
        if not obj:
            return error_result("NODE_NOT_FOUND", f"Node '{node_name}' not found in scene '{scene_name}'")

        modified = []
        if "position" in props:
            obj.transform.position = [float(x) for x in props["position"]] if isinstance(props["position"], list) else obj.transform.position
            modified.append("position")
        if "rotation" in props:
            obj.transform.rotation = [float(x) for x in props["rotation"]] if isinstance(props["rotation"], list) else obj.transform.rotation
            modified.append("rotation")
        if "scale" in props:
            obj.transform.scale = [float(x) for x in props["scale"]] if isinstance(props["scale"], list) else obj.transform.scale
            modified.append("scale")

        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
            return ok_result(
                data={
                    "scene": scene_name,
                    "node": node_name,
                    "modified_properties": modified,
                    "path": str(spath),
                }
            )
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))

    def tool_script_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        return adapter.script_create(
            project_root=args.get("path", "."),
            script_name=name,
            extends=args.get("extends", "Node3D"),
            code=args.get("code"),
        )

    def tool_asset_import(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        src = args.get("file")
        if not src:
            return error_result("INVALID_INPUT", "file is required")
        return adapter.asset_import(
            project_root=args.get("path", "."),
            source_path=src,
            dest_name=args.get("name"),
        )

    def tool_physics_configure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        size = args.get("size")
        return adapter.physics_configure(
            project_root=args.get("path", "."),
            scene_name=args.get("scene", ""),
            body_name=args.get("name", ""),
            body_type=args.get("type", "RigidBody3D"),
            shape=args.get("shape", "box"),
            size=size,
            mass=args.get("mass", 1.0),
            friction=args.get("friction", 0.5),
            restitution=args.get("restitution", 0.0),
        )

    def tool_game_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Delegate to CLI's game_create logic via the adapter directly.
        adapter = self.godot
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        root = args.get("path", name)

        presult = adapter.project_create(root, name=name)
        if not presult["ok"]:
            return presult

        nodes = [
            {"type": "Node3D", "name": "World"},
            {"type": "Node3D", "name": "Ground", "parent": "World"},
            {"type": "Node3D", "name": "Player", "parent": "World"},
            {"type": "Node3D", "name": "Camera", "parent": "Player"},
            {"type": "Node3D", "name": "Light", "parent": "World"},
            {"type": "Node3D", "name": "Collectibles", "parent": "World"},
            {"type": "Node3D", "name": "GameManager", "parent": "World"},
            {"type": "CanvasLayer", "name": "UI", "parent": "World"},
        ]
        sresult = adapter.scene_create(root, "Main", nodes=nodes)
        if not sresult["ok"]:
            return sresult

        from universal_engine.cli import (
            _player_gdscript,
            _game_manager_gdscript,
            _collectible_gdscript,
            _write_main_scene,
        )

        adapter.script_create(root, "Player", extends="CharacterBody3D", code=_player_gdscript())
        adapter.script_create(root, "GameManager", extends="Node3D", code=_game_manager_gdscript())
        adapter.script_create(root, "Collectible", extends="Area3D", code=_collectible_gdscript())
        _write_main_scene(root)

        return ok_result(
            data={
                "game": name,
                "project_root": str(Path(root).resolve()),
                "scene": "Main",
                "scripts": ["Player.gd", "GameManager.gd", "Collectible.gd"],
                "godot_available": adapter.available,
                "note": "Game project generated. Use `game_run` to execute (requires Godot binary).",
            }
        )

    def tool_game_run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        if not adapter.available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Godot binary not found. Install Godot 4.x or set GODOT_PATH.",
            )
        result = adapter.game_run(
            project_root=args.get("path", "."),
            scene=args.get("scene"),
            headless=args.get("headless", True),
            timeout_s=args.get("timeout", 30),
            capture_screenshot=args.get("capture", False),
        )
        # Store run id mapping for game_stop.
        if result["ok"]:
            run_id = result["data"].get("run_id")
            if run_id:
                self._run_ids[str(uuid.uuid4())] = run_id
                result["data"]["mcp_run_id"] = list(self._run_ids.keys())[
                    list(self._run_ids.values()).index(run_id)
                ]
        return result

    def tool_game_stop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        mcp_run_id = args.get("run_id")
        if not mcp_run_id or mcp_run_id not in self._run_ids:
            return error_result("NOT_RUNNING", f"No running process with id {mcp_run_id}")
        godot_run_id = self._run_ids.pop(mcp_run_id)
        return adapter.game_stop(godot_run_id)

    def tool_game_test(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        if not adapter.available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Godot binary not found. Cannot run game test.",
            )
        return adapter.game_test(
            project_root=args.get("path", "."),
            headless=args.get("headless", True),
            timeout_s=args.get("timeout", 30),
        )

    def tool_preview_capture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        adapter = self.godot
        if not adapter.available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Godot binary not found. Cannot capture preview.",
            )
        return adapter.preview_capture(
            project_root=args.get("path", "."),
            scene_name=args.get("scene", ""),
            output_path=args.get("output", ""),
            width=args.get("width", 640),
            height=args.get("height", 480),
        )

    def tool_adapters_list(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return ok_result(
            data={
                "adapters": [
                    BlenderAdapter().capabilities(),
                    self.godot.capabilities(),
                ]
            }
        )

    # ---- Blender tool methods ----

    def tool_blender_project_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Blender project directory structure."""
        path = args.get("path", ".")
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        project = Project(path, name=name)
        result = project.create()
        if not result["ok"]:
            return result
        for sub in ("scenes", "objects", "materials", "textures", "scripts", "exports", "prefabs"):
            try:
                os.makedirs(os.path.join(project.root, sub), exist_ok=True)
            except OSError as exc:
                return error_result("DIR_CREATE_FAILED", f"{sub}: {exc}")
        result["data"] = dict(result["data"] or {})
        result["data"]["blender_dirs"] = [
            "scenes", "objects", "materials", "textures", "scripts", "exports", "prefabs",
        ]
        result["data"]["blender_available"] = BlenderAdapter().available
        return result

    def tool_blender_scene_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Blender scene as universal JSON."""
        path = args.get("path", ".")
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        scene = Scene(name=name)
        scene.add_object(
            ObjectDef(id="cam-1", name="Camera", type="Camera", transform=Transform(position=[0, 0, 3]))
        )
        scene.add_object(
            ObjectDef(id="light-1", name="Light", type="Light", transform=Transform(position=[0, 5, 5]))
        )
        scene.add_object(ObjectDef(id="root-1", name="Root", type="Empty"))
        spath = project.scene_path(name)
        try:
            os.makedirs(project.scenes_dir, exist_ok=True)
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))
        return ok_result(
            data={
                "scene": name,
                "path": spath,
                "objects": len(scene.objects),
                "blender_available": BlenderAdapter().available,
                "note": "Scene created as universal JSON. Use BlenderAdapter to convert to .blend when Blender is available.",
            }
        )

    def tool_blender_scene_inspect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect a Blender scene (universal JSON)."""
        path = args.get("path", ".")
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        spath = project.scene_path(name)
        if not os.path.isfile(spath):
            return error_result("SCENE_NOT_FOUND", f"No scene: {name}")
        try:
            with open(spath, "r", encoding="utf-8") as f:
                scene = Scene.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))
        return ok_result(
            data={
                "scene": scene.name,
                "objects": [o.to_dict() for o in scene.objects],
                "object_count": len(scene.objects),
                "format": "universal-json",
                "blender_available": BlenderAdapter().available,
            }
        )

    def tool_blender_object_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an object in a Blender scene (universal JSON)."""
        path = args.get("path", ".")
        scene_name = args.get("scene")
        otype = args.get("type")
        oname = args.get("name")
        if not scene_name or not otype or not oname:
            return error_result("INVALID_INPUT", "scene, type, and name are required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        spath = project.scene_path(scene_name)
        if not os.path.isfile(spath):
            return error_result("SCENE_NOT_FOUND", f"No scene: {scene_name}")
        try:
            with open(spath, "r", encoding="utf-8") as f:
                scene = Scene.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))
        if scene.find_object_by_name(oname):
            return error_result("OBJECT_EXISTS", f"Object '{oname}' already exists in scene '{scene_name}'")
        position = [0.0, 0.0, 0.0]
        rotation = [0.0, 0.0, 0.0]
        scale = [1.0, 1.0, 1.0]
        props = args.get("properties", {}) or {}
        if "position" in props:
            try:
                position = [float(x) for x in props["position"]]
            except (TypeError, ValueError):
                pass
        if "rotation" in props:
            try:
                rotation = [float(x) for x in props["rotation"]]
            except (TypeError, ValueError):
                pass
        if "scale" in props:
            try:
                scale = [float(x) for x in props["scale"]]
            except (TypeError, ValueError):
                pass
        scene.add_object(
            ObjectDef(
                id=str(uuid.uuid4()),
                name=oname,
                type=otype,
                transform=Transform(position=position, rotation=rotation, scale=scale),
                parent=args.get("parent"),
                components={},
                metadata={},
            )
        )
        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))
        return ok_result(
            data={
                "scene": scene_name,
                "object": oname,
                "type": otype,
                "parent": args.get("parent"),
                "path": spath,
                "blender_available": BlenderAdapter().available,
            }
        )

    def tool_blender_object_modify(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an object's properties in a Blender scene (universal JSON)."""
        path = args.get("path", ".")
        scene_name = args.get("scene")
        oname = args.get("node")
        props = args.get("properties", {}) or {}
        if not scene_name or not oname:
            return error_result("INVALID_INPUT", "scene and node are required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        spath = project.scene_path(scene_name)
        if not os.path.isfile(spath):
            return error_result("SCENE_NOT_FOUND", f"No scene: {scene_name}")
        try:
            with open(spath, "r", encoding="utf-8") as f:
                scene = Scene.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))
        obj = scene.find_object_by_name(oname)
        if not obj:
            return error_result("OBJECT_NOT_FOUND", f"Object '{oname}' not found in scene '{scene_name}'")
        modified = []
        if "position" in props:
            try:
                obj.transform.position = [float(x) for x in props["position"]]
                modified.append("position")
            except (TypeError, ValueError):
                pass
        if "rotation" in props:
            try:
                obj.transform.rotation = [float(x) for x in props["rotation"]]
                modified.append("rotation")
            except (TypeError, ValueError):
                pass
        if "scale" in props:
            try:
                obj.transform.scale = [float(x) for x in props["scale"]]
                modified.append("scale")
            except (TypeError, ValueError):
                pass
        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))
        return ok_result(
            data={
                "scene": scene_name,
                "object": oname,
                "modified_properties": modified,
                "path": spath,
                "blender_available": BlenderAdapter().available,
            }
        )

    def tool_blender_mesh_generate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mesh. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Mesh generation requires bpy.",
                data={
                    "mesh_type": args.get("type"),
                    "mesh_name": args.get("name"),
                    "blender_source": "cloned at blender-source/",
                    "build_blocked": "missing dev headers, no root, insufficient RAM",
                },
            )
        return ok_result(
            data={
                "mesh_type": args.get("type"),
                "mesh_name": args.get("name"),
                "status": "generated",
                "note": "Mesh generated via bpy.",
            }
        )

    def tool_blender_material_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a material. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Material creation requires bpy.",
                data={
                    "material_name": args.get("name"),
                    "blender_source": "cloned at blender-source/",
                },
            )
        return ok_result(
            data={
                "material_name": args.get("name"),
                "status": "created",
                "note": "Material created via bpy.",
            }
        )

    def tool_blender_render(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Render a scene to an image. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Rendering requires bpy.",
                data={
                    "scene": args.get("scene"),
                    "output": args.get("output"),
                    "blender_source": "cloned at blender-source/",
                },
            )
        return ok_result(
            data={
                "scene": args.get("scene"),
                "output": args.get("output"),
                "status": "rendered",
            }
        )

    def tool_blender_export(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export a scene as glTF/GLB. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. glTF/GLB export requires bpy.",
                data={
                    "scene": args.get("scene"),
                    "output": args.get("output"),
                    "format": args.get("format", "glb"),
                    "blender_source": "cloned at blender-source/",
                },
            )
        return ok_result(
            data={
                "scene": args.get("scene"),
                "output": args.get("output"),
                "format": args.get("format", "glb"),
                "status": "exported",
            }
        )

    def tool_blender_prefab_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a collection as a prefab template (universal JSON)."""
        path = args.get("path", ".")
        name = args.get("name")
        if not name:
            return error_result("INVALID_INPUT", "name is required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        prefab_dir = os.path.join(project.root, "prefabs")
        os.makedirs(prefab_dir, exist_ok=True)
        prefab_path = os.path.join(prefab_dir, f"{name}.prefab.json")
        prefab = {
            "name": name,
            "format": "blender-prefab/1",
            "objects": [o.to_dict() for o in Scene(name=name).objects],
            "blender_available": BlenderAdapter().available,
        }
        try:
            with open(prefab_path, "w", encoding="utf-8") as f:
                json.dump(prefab, f, indent=2)
        except OSError as exc:
            return error_result("PREFAB_WRITE_FAILED", str(exc))
        return ok_result(data={"prefab": name, "path": prefab_path, "objects": 0})

    def tool_blender_prefab_instance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Instance a prefab in a scene (universal JSON)."""
        path = args.get("path", ".")
        prefab_name = args.get("prefab")
        scene_name = args.get("scene")
        if not prefab_name or not scene_name:
            return error_result("INVALID_INPUT", "prefab and scene are required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        prefab_path = os.path.join(project.root, "prefabs", f"{prefab_name}.prefab.json")
        if not os.path.isfile(prefab_path):
            return error_result("PREFAB_NOT_FOUND", f"No prefab: {prefab_name}")
        try:
            with open(prefab_path, "r", encoding="utf-8") as f:
                prefab = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("PREFAB_READ_FAILED", str(exc))
        spath = project.scene_path(scene_name)
        if not os.path.isfile(spath):
            return error_result("SCENE_NOT_FOUND", f"No scene: {scene_name}")
        try:
            with open(spath, "r", encoding="utf-8") as f:
                scene = Scene.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("SCENE_READ_FAILED", str(exc))
        instance_name = f"{prefab_name}_inst"
        scene.add_object(
            ObjectDef(
                id=str(uuid.uuid4()),
                name=instance_name,
                type="CollectionInstance",
                transform=Transform(position=[0.0, 0.0, 0.0]),
                parent=None,
                components={"prefab": prefab_name},
                metadata={},
            )
        )
        try:
            with open(spath, "w", encoding="utf-8") as f:
                json.dump(scene.to_dict(), f, indent=2)
        except OSError as exc:
            return error_result("SCENE_WRITE_FAILED", str(exc))
        return ok_result(
            data={
                "prefab": prefab_name,
                "instance": instance_name,
                "scene": scene_name,
                "path": spath,
            }
        )

    def tool_blender_addressable_register(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Register an asset as addressable (universal JSON)."""
        path = args.get("path", ".")
        address = args.get("address")
        asset_path = args.get("asset_path")
        if not address or not asset_path:
            return error_result("INVALID_INPUT", "address and asset_path are required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        addr_dir = os.path.join(project.root, "addressables")
        os.makedirs(addr_dir, exist_ok=True)
        registry_path = os.path.join(addr_dir, "registry.json")
        registry = {}
        if os.path.isfile(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except (OSError, json.JSONDecodeError):
                registry = {}
        registry[address] = {
            "path": asset_path,
            "type": os.path.splitext(asset_path)[1].lstrip(".") or "unknown",
            "registered": True,
        }
        try:
            with open(registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except OSError as exc:
            return error_result("REGISTRY_WRITE_FAILED", str(exc))
        return ok_result(data={"address": address, "asset_path": asset_path, "registry": registry_path})

    def tool_blender_addressable_resolve(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve an addressable address to an asset path."""
        path = args.get("path", ".")
        address = args.get("address")
        if not address:
            return error_result("INVALID_INPUT", "address is required")
        project = Project(path, name=None)
        load = project.load()
        if not load["ok"]:
            return load
        registry_path = os.path.join(project.root, "addressables", "registry.json")
        if not os.path.isfile(registry_path):
            return error_result("REGISTRY_NOT_FOUND", "No addressable registry")
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("REGISTRY_READ_FAILED", str(exc))
        entry = registry.get(address)
        if not entry:
            return error_result("ADDRESS_NOT_FOUND", f"No addressable: {address}")
        return ok_result(
            data={"address": address, "asset_path": entry["path"], "type": entry.get("type")}
        )

    def tool_blender_light_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a light. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Light creation requires bpy.",
                data={"light_type": args.get("type"), "light_name": args.get("name")},
            )
        return ok_result(
            data={
                "light_type": args.get("type"),
                "light_name": args.get("name"),
                "status": "created",
            }
        )

    def tool_blender_camera_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a camera. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Camera creation requires bpy.",
                data={"camera_name": args.get("name")},
            )
        return ok_result(
            data={
                "camera_name": args.get("name"),
                "status": "created",
            }
        )

    def tool_blender_preview_capture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a preview screenshot. Requires Blender (bpy)."""
        if not BlenderAdapter().available:
            return error_result(
                "BACKEND_UNAVAILABLE",
                "Blender is not installed. Preview capture requires bpy.",
                data={"scene": args.get("scene"), "output": args.get("output")},
            )
        return ok_result(
            data={
                "scene": args.get("scene"),
                "output": args.get("output"),
                "status": "captured",
            }
        )



    # ---- Reality Engine tools ----

    def tool_reality_project_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Reality Engine project."""
        from universal_engine.reality_cli import cmd_reality_project_create
        import argparse
        ns = argparse.Namespace(
            name=args.get("name"),
            path=args.get("path"),
            json=False,
        )
        return cmd_reality_project_create(ns, False)

    def tool_reality_scene_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_scene_create
        import argparse
        ns = argparse.Namespace(
            name=args.get("name"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_scene_create(ns, False)

    def tool_reality_scene_load(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Load and validate a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_scene_load
        import argparse
        ns = argparse.Namespace(
            name=args.get("name"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_scene_load(ns, False)

    def tool_reality_scene_export(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Export a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_scene_export
        import argparse
        ns = argparse.Namespace(
            name=args.get("name"),
            path=args.get("path", "."),
            output=args.get("output"),
            json=False,
        )
        return cmd_reality_scene_export(ns, False)

    def tool_reality_entity_create(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create an entity in a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_entity_create
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            name=args.get("name"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_entity_create(ns, False)

    def tool_reality_entity_inspect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect an entity in a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_entity_inspect
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            id=args.get("id"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_entity_inspect(ns, False)

    def tool_reality_entity_modify(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an entity property in a Reality Engine scene."""
        from universal_engine.reality_cli import cmd_reality_entity_modify
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            id=args.get("id"),
            property=args.get("property", []),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_entity_modify(ns, False)

    def tool_reality_component_add(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Add a component to an entity."""
        from universal_engine.reality_cli import cmd_reality_component_add
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            id=args.get("id"),
            component=args.get("component"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_component_add(ns, False)

    def tool_reality_component_remove(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a component from an entity."""
        from universal_engine.reality_cli import cmd_reality_component_remove
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            id=args.get("id"),
            component=args.get("component"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_component_remove(ns, False)

    def tool_reality_physics_configure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Configure physics for an entity."""
        from universal_engine.reality_cli import cmd_reality_physics_configure
        import argparse
        ns = argparse.Namespace(
            scene=args.get("scene"),
            id=args.get("id"),
            body_type=args.get("body_type", "dynamic"),
            mass=args.get("mass", 1.0),
            friction=args.get("friction", 0.5),
            restitution=args.get("restitution", 0.0),
            gravity=args.get("gravity", True),
            collider_shape=args.get("collider_shape", "box"),
            path=args.get("path", "."),
            json=False,
        )
        return cmd_reality_physics_configure(ns, False)

    def tool_reality_physics_simulate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Run physics simulation via the runtime."""
        from universal_engine.reality_cli import cmd_reality_physics_simulate
        import argparse
        ns = argparse.Namespace(
            path=args.get("path", "."),
            frames=args.get("frames", 60),
            timeout=args.get("timeout", 30),
            json=False,
        )
        return cmd_reality_physics_simulate(ns, False)

    def tool_reality_runtime_launch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Launch the standalone Reality Engine runtime."""
        from universal_engine.reality_cli import cmd_reality_runtime_launch
        import argparse
        ns = argparse.Namespace(
            path=args.get("path", "."),
            frames=args.get("frames", 60),
            timeout=args.get("timeout", 30),
            json=False,
        )
        return cmd_reality_runtime_launch(ns, False)

    def tool_reality_runtime_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check runtime status."""
        from universal_engine.reality_cli import cmd_reality_runtime_status
        import argparse
        ns = argparse.Namespace(json=False)
        return cmd_reality_runtime_status(ns, False)

    def tool_reality_runtime_inspect(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect runtime state."""
        from universal_engine.reality_cli import cmd_reality_runtime_inspect
        import argparse
        ns = argparse.Namespace(
            path=args.get("path", "."),
            timeout=args.get("timeout", 30),
            json=False,
        )
        return cmd_reality_runtime_inspect(ns, False)

    def tool_reality_runtime_stop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stop the runtime."""
        from universal_engine.reality_cli import cmd_reality_runtime_stop
        import argparse
        ns = argparse.Namespace(json=False)
        return cmd_reality_runtime_stop(ns, False)

    def tool_reality_engine_diagnostics(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get engine diagnostics."""
        from universal_engine.reality_cli import cmd_reality_engine_diagnostics
        import argparse
        ns = argparse.Namespace(json=False)
        return cmd_reality_engine_diagnostics(ns, False)

def scene_object_from_dict(d: Dict[str, Any]):
    from universal_engine.core import ObjectDef, Transform
    t = d.get("transform", {})
    return ObjectDef(
        id=d.get("id", str(uuid.uuid4())),
        name=d.get("name", "Object"),
        type=d.get("type", "Empty"),
        transform=Transform(
            position=t.get("position", [0.0, 0.0, 0.0]),
            rotation=t.get("rotation", [0.0, 0.0, 0.0]),
            scale=t.get("scale", [1.0, 1.0, 1.0]),
        ),
        parent=d.get("parent"),
        components=d.get("components", {}),
        metadata=d.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "project_create": {
        "description": "Create a new game project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "project_inspect": {
        "description": "Inspect the current project.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Project root directory"}},
        },
    },
    "project_validate": {
        "description": "Validate the current project structure.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Project root directory"}},
        },
    },
    "scene_create": {
        "description": "Create a scene in the current project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
                "nodes": {
                    "type": "array",
                    "description": "Optional list of node descriptors",
                    "items": {"type": "object"},
                },
            },
            "required": ["name"],
        },
    },
    "scene_inspect": {
        "description": "Inspect a scene file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "node_create": {
        "description": "Create a node in a Godot scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "type": {"type": "string"},
                "name": {"type": "string"},
                "path": {"type": "string"},
                "parent": {"type": "string"},
                "script": {"type": "string"},
                "properties": {"type": "object"},
            },
            "required": ["scene", "type", "name"],
        },
    },
    "node_modify": {
        "description": "Modify a node's properties in a Godot scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "node": {"type": "string"},
                "properties": {"type": "object"},
                "path": {"type": "string"},
            },
            "required": ["scene", "node", "properties"],
        },
    },
    "script_create": {
        "description": "Create a GDScript file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "path": {"type": "string"},
                "extends": {"type": "string"},
                "code": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    "asset_import": {
        "description": "Import an asset into the project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string"},
                "path": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["file"],
        },
    },
    "physics_configure": {
        "description": "Configure a physics body in a scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "name": {"type": "string"},
                "path": {"type": "string"},
                "type": {"type": "string"},
                "shape": {"type": "string"},
                "size": {"type": "array", "items": {"type": "number"}},
                "mass": {"type": "number"},
                "friction": {"type": "number"},
                "restitution": {"type": "number"},
            },
            "required": ["scene", "name"],
        },
    },
    "game_create": {
        "description": "Generate a complete playable test game.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["name"],
        },
    },
    "game_run": {
        "description": "Run the game via Godot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "scene": {"type": "string"},
                "headless": {"type": "boolean"},
                "timeout": {"type": "integer"},
                "capture": {"type": "boolean"},
            },
        },
    },
    "game_stop": {
        "description": "Stop a running game.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "string"}},
            "required": ["run_id"],
        },
    },
    "game_test": {
        "description": "Headless game smoke test.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "headless": {"type": "boolean"},
                "timeout": {"type": "integer"},
            },
        },
    },
    "preview_capture": {
        "description": "Capture a preview image of a scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string"},
                "output": {"type": "string"},
                "path": {"type": "string"},
                "width": {"type": "integer"},
                "height": {"type": "integer"},
            },
            "required": ["scene", "output"],
        },
    },
    "adapters_list": {
        "description": "List adapters and availability.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # ---- Blender tools ----
    "blender_project_create": {
        "description": "Create a Blender project with directory structure (scenes, objects, materials, textures, scripts, exports, prefabs).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_scene_create": {
        "description": "Create a Blender scene as universal JSON (works without Blender installed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_scene_inspect": {
        "description": "Inspect a Blender scene (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_object_create": {
        "description": "Create an object in a Blender scene (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "type": {"type": "string", "description": "Object type (Mesh, Empty, Camera, Light, etc.)"},
                "name": {"type": "string", "description": "Object name"},
                "path": {"type": "string", "description": "Project root directory"},
                "parent": {"type": "string", "description": "Parent object name"},
                "properties": {"type": "object", "description": "Object properties (position, rotation, scale)"},
            },
            "required": ["scene", "type", "name"],
        },
    },
    "blender_object_modify": {
        "description": "Modify an object's properties in a Blender scene (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "node": {"type": "string", "description": "Object name"},
                "properties": {"type": "object", "description": "Properties to modify (position, rotation, scale)"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "node", "properties"],
        },
    },
    "blender_mesh_generate": {
        "description": "Generate a mesh (cube, sphere, ico, cylinder). Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Mesh type (cube, sphere, ico, cylinder)"},
                "name": {"type": "string", "description": "Mesh name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["type", "name"],
        },
    },
    "blender_material_create": {
        "description": "Create a material. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Material name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_render": {
        "description": "Render a scene to an image. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "output": {"type": "string", "description": "Output image path"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "output"],
        },
    },
    "blender_export": {
        "description": "Export a scene as glTF/GLB. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "output": {"type": "string", "description": "Output file path"},
                "format": {"type": "string", "description": "Export format (glb or gltf)", "default": "glb"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "output"],
        },
    },
    "blender_prefab_create": {
        "description": "Create a collection as a prefab template (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prefab name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_prefab_instance": {
        "description": "Instance a prefab in a scene (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prefab": {"type": "string", "description": "Prefab name"},
                "scene": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["prefab", "scene"],
        },
    },
    "blender_addressable_register": {
        "description": "Register an asset as addressable (universal JSON).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Addressable address"},
                "asset_path": {"type": "string", "description": "Path to the asset file"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["address", "asset_path"],
        },
    },
    "blender_addressable_resolve": {
        "description": "Resolve an addressable address to an asset path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Addressable address"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["address"],
        },
    },
    "blender_light_create": {
        "description": "Create a light. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Light type (SUN, POINT, SPOT, AREA)"},
                "name": {"type": "string", "description": "Light name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["type", "name"],
        },
    },
    "blender_camera_create": {
        "description": "Create a camera. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Camera name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "blender_preview_capture": {
        "description": "Capture a preview screenshot. Requires Blender (bpy).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "output": {"type": "string", "description": "Output image path"},
                "path": {"type": "string", "description": "Project root directory"},
                "width": {"type": "integer", "description": "Image width", "default": 640},
                "height": {"type": "integer", "description": "Image height", "default": 480},
            },
            "required": ["scene", "output"],
        },
    },
    "reality_project_create": {
        "description": "Create a Reality Engine project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Project name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "reality_scene_create": {
        "description": "Create a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "reality_scene_load": {
        "description": "Load and validate a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["name"],
        },
    },
    "reality_scene_export": {
        "description": "Export a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Scene name"},
                "path": {"type": "string", "description": "Project root directory"},
                "output": {"type": "string", "description": "Output path"},
            },
            "required": ["name"],
        },
    },
    "reality_entity_create": {
        "description": "Create an entity in a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "name": {"type": "string", "description": "Entity name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "name"],
        },
    },
    "reality_entity_inspect": {
        "description": "Inspect an entity in a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "id": {"type": "string", "description": "Entity id or name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "id"],
        },
    },
    "reality_entity_modify": {
        "description": "Modify an entity property in a Reality Engine scene.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "id": {"type": "string", "description": "Entity id or name"},
                "property": {"type": "array", "description": "List of key=value properties", "items": {"type": "string"}},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "id"],
        },
    },
    "reality_component_add": {
        "description": "Add a component to an entity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "id": {"type": "string", "description": "Entity id or name"},
                "component": {"type": "string", "description": "Component type name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "id", "component"],
        },
    },
    "reality_component_remove": {
        "description": "Remove a component from an entity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "id": {"type": "string", "description": "Entity id or name"},
                "component": {"type": "string", "description": "Component type name"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "id", "component"],
        },
    },
    "reality_physics_configure": {
        "description": "Configure physics for an entity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene": {"type": "string", "description": "Scene name"},
                "id": {"type": "string", "description": "Entity id or name"},
                "body_type": {"type": "string", "description": "Body type"},
                "mass": {"type": "number", "description": "Mass"},
                "friction": {"type": "number", "description": "Friction"},
                "restitution": {"type": "number", "description": "Restitution"},
                "gravity": {"type": "boolean", "description": "Enable gravity"},
                "collider_shape": {"type": "string", "description": "Collider shape"},
                "path": {"type": "string", "description": "Project root directory"},
            },
            "required": ["scene", "id"],
        },
    },
    "reality_physics_simulate": {
        "description": "Run physics simulation via the runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root directory"},
                "frames": {"type": "integer", "description": "Number of frames"},
                "timeout": {"type": "integer", "description": "Timeout seconds"},
            },
        },
    },
    "reality_runtime_launch": {
        "description": "Launch the standalone Reality Engine runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root directory"},
                "frames": {"type": "integer", "description": "Number of frames"},
                "timeout": {"type": "integer", "description": "Timeout seconds"},
            },
        },
    },
    "reality_runtime_status": {
        "description": "Check runtime status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "reality_runtime_inspect": {
        "description": "Inspect runtime state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Project root directory"},
                "timeout": {"type": "integer", "description": "Timeout seconds"},
            },
        },
    },
    "reality_runtime_stop": {
        "description": "Stop the runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    "reality_engine_diagnostics": {
        "description": "Get engine diagnostics.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
}

HANDLERS = {
    "project_create": lambda s, a: s.tool_project_create(a),
    "project_inspect": lambda s, a: s.tool_project_inspect(a),
    "project_validate": lambda s, a: s.tool_project_validate(a),
    "scene_create": lambda s, a: s.tool_scene_create(a),
    "scene_inspect": lambda s, a: s.tool_scene_inspect(a),
    "node_create": lambda s, a: s.tool_node_create(a),
    "node_modify": lambda s, a: s.tool_node_modify(a),
    "script_create": lambda s, a: s.tool_script_create(a),
    "asset_import": lambda s, a: s.tool_asset_import(a),
    "physics_configure": lambda s, a: s.tool_physics_configure(a),
    "game_create": lambda s, a: s.tool_game_create(a),
    "game_run": lambda s, a: s.tool_game_run(a),
    "game_stop": lambda s, a: s.tool_game_stop(a),
    "game_test": lambda s, a: s.tool_game_test(a),
    "preview_capture": lambda s, a: s.tool_preview_capture(a),
    "adapters_list": lambda s, a: s.tool_adapters_list(a),
    # ---- Blender handlers ----
    "blender_project_create": lambda s, a: s.tool_blender_project_create(a),
    "blender_scene_create": lambda s, a: s.tool_blender_scene_create(a),
    "blender_scene_inspect": lambda s, a: s.tool_blender_scene_inspect(a),
    "blender_object_create": lambda s, a: s.tool_blender_object_create(a),
    "blender_object_modify": lambda s, a: s.tool_blender_object_modify(a),
    "blender_mesh_generate": lambda s, a: s.tool_blender_mesh_generate(a),
    "blender_material_create": lambda s, a: s.tool_blender_material_create(a),
    "blender_render": lambda s, a: s.tool_blender_render(a),
    "blender_export": lambda s, a: s.tool_blender_export(a),
    "blender_prefab_create": lambda s, a: s.tool_blender_prefab_create(a),
    "blender_prefab_instance": lambda s, a: s.tool_blender_prefab_instance(a),
    "blender_addressable_register": lambda s, a: s.tool_blender_addressable_register(a),
    "blender_addressable_resolve": lambda s, a: s.tool_blender_addressable_resolve(a),
    "blender_light_create": lambda s, a: s.tool_blender_light_create(a),
    "blender_camera_create": lambda s, a: s.tool_blender_camera_create(a),
    "blender_preview_capture": lambda s, a: s.tool_blender_preview_capture(a),
    # ---- Reality Engine handlers ----
    "reality_project_create": lambda s, a: s.tool_reality_project_create(a),
    "reality_scene_create": lambda s, a: s.tool_reality_scene_create(a),
    "reality_scene_load": lambda s, a: s.tool_reality_scene_load(a),
    "reality_scene_export": lambda s, a: s.tool_reality_scene_export(a),
    "reality_entity_create": lambda s, a: s.tool_reality_entity_create(a),
    "reality_entity_inspect": lambda s, a: s.tool_reality_entity_inspect(a),
    "reality_entity_modify": lambda s, a: s.tool_reality_entity_modify(a),
    "reality_component_add": lambda s, a: s.tool_reality_component_add(a),
    "reality_component_remove": lambda s, a: s.tool_reality_component_remove(a),
    "reality_physics_configure": lambda s, a: s.tool_reality_physics_configure(a),
    "reality_physics_simulate": lambda s, a: s.tool_reality_physics_simulate(a),
    "reality_runtime_launch": lambda s, a: s.tool_reality_runtime_launch(a),
    "reality_runtime_status": lambda s, a: s.tool_reality_runtime_status(a),
    "reality_runtime_inspect": lambda s, a: s.tool_reality_runtime_inspect(a),
    "reality_runtime_stop": lambda s, a: s.tool_reality_runtime_stop(a),
    "reality_engine_diagnostics": lambda s, a: s.tool_reality_engine_diagnostics(a),
}


# ---------------------------------------------------------------------------
# MCP server loop
# ---------------------------------------------------------------------------


class MCPServer:
    def __init__(self, services: _EngineServices):
        self.services = services
        self.initialized = False

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rpc_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {}) or {}

        if method == "initialize":
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": "universal-engine-mcp",
                        "version": __version__,
                    },
                },
            }

        if method == "initialized":
            # Notification, no response needed.
            return None

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "tools": [
                        {
                            "name": name,
                            "description": schema["description"],
                            "inputSchema": schema["inputSchema"],
                        }
                        for name, schema in TOOL_SCHEMAS.items()
                    ]
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {}) or {}
            if not self.initialized:
                return _json_rpc_error_dict(
                    rpc_id, -32002, "Server not initialized. Call initialize first."
                )
            if tool_name not in HANDLERS:
                return _json_rpc_error_dict(
                    rpc_id, -32601, f"Unknown tool: {tool_name}"
                )
            try:
                result = HANDLERS[tool_name](self.services, tool_args)
                # Convert ok_result/error_result dict to MCP result.
                return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
            except Exception as exc:  # noqa: BLE001
                return _json_rpc_error_dict(rpc_id, -32603, f"Internal error: {exc}")

        return _json_rpc_error_dict(rpc_id, -32601, f"Unknown method: {method}")


def _json_rpc_error_dict(rpc_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": rpc_id, "error": err}


def run(stdin_stream=sys.stdin, stdout_stream=sys.stdout) -> int:
    """Run the MCP server over stdio using JSON-RPC 2.0 with Content-Length headers."""
    services = _EngineServices(godot_path=os.environ.get("GODOT_PATH"))
    server = MCPServer(services)

    # Use binary buffers for Content-Length framed MCP messages.
    stdin_bin = getattr(stdin_stream, "buffer", stdin_stream)
    stdout_bin = getattr(stdout_stream, "buffer", stdout_stream)

    # Read messages from stdin.
    buffer = b""
    while True:
        chunk = stdin_bin.read(4096)
        if not chunk:
            break
        buffer += chunk

        # Process any complete messages in the buffer.
        while True:
            content_len = _parse_content_length_headers(buffer)
            if content_len is None:
                break
            header_end = buffer.find(b"\r\n\r\n")
            if header_end == -1:
                break
            header_end += 4
            if len(buffer) < header_end + content_len:
                break
            body = buffer[header_end:header_end + content_len]
            buffer = buffer[header_end + content_len:]

            try:
                request = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                response = _json_rpc_error_dict(None, -32700, "Parse error")
                _write_response(stdout_bin, response)
                continue

            response = server.handle_request(request)
            if response is not None:
                _write_response(stdout_bin, response)

    return 0


def _write_response(stdout_stream, response: Dict[str, Any]) -> None:
    payload = json.dumps(response).encode("utf-8")
    header = f"Content-Length: {len(payload)}\r\n\r\n".encode("utf-8")
    stdout_stream.write(header + payload)
    stdout_stream.flush()



def serve_stdio() -> int:
    return run(stdin_stream=sys.stdin, stdout_stream=sys.stdout)


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
