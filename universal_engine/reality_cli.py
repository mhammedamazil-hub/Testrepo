"""Reality Engine CLI commands.

Extends the universal-engine CLI with reality_* subcommands that
interact with the compiled C++ standalone runtime.
"""

from __future__ import annotations

import json as _json
import os
import subprocess
import uuid as _uuid

from universal_engine.core import error_result, ok_result


def _runtime_binary() -> str:
    """Return path to the compiled Reality Engine runtime."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "engine", "build", "bin", "reality_runtime",
    )


def _run_runtime(args: list, timeout: int = 30) -> dict:
    """Run the Reality Engine runtime and return parsed result."""
    runtime = _runtime_binary()
    if not os.path.isfile(runtime):
        return error_result(
            "BACKEND_UNAVAILABLE",
            "Reality Engine runtime not built. Build with: cd engine/build && cmake .. && make",
            data={"runtime_path": runtime},
        )
    cmd = [runtime] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        stdout = proc.stdout.strip()
        result_data = {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": proc.stderr.strip(),
        }
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    result_data["diagnostics"] = _json.loads(line)
                    break
                except _json.JSONDecodeError:
                    pass
        if proc.returncode == 0:
            return ok_result(data=result_data)
        else:
            return error_result(
                "RUNTIME_ERROR",
                f"Runtime exited with code {proc.returncode}",
                data=result_data,
            )
    except subprocess.TimeoutExpired:
        return error_result("RUNTIME_TIMEOUT", f"Runtime timed out after {timeout}s")
    except Exception as exc:
        return error_result("RUNTIME_EXCEPTION", str(exc))


# -- Command handlers --

def cmd_reality_project_create(args, json_mode):
    project_root = args.path or args.name
    for sub in ("scenes", "assets", "builds", "scripts"):
        try:
            os.makedirs(os.path.join(project_root, sub), exist_ok=True)
        except OSError as exc:
            return error_result("DIR_CREATE_FAILED", f"{sub}: {exc}")
    descriptor = {
        "name": args.name,
        "format": "reality-engine-project/1",
        "version": "0.1.0",
        "scenes_dir": "scenes",
        "assets_dir": "assets",
        "scripts_dir": "scripts",
        "builds_dir": "builds",
    }
    try:
        with open(os.path.join(project_root, "project.reality"), "w", encoding="utf-8") as f:
            _json.dump(descriptor, f, indent=2)
    except OSError as exc:
        return error_result("DESCRIPTOR_WRITE_FAILED", str(exc))
    data = {
        "project": args.name,
        "root": os.path.abspath(project_root),
        "format": "reality-engine-project/1",
        "directories": ["scenes", "assets", "builds", "scripts"],
    }
    return ok_result(data=data)


def cmd_reality_scene_create(args, json_mode):
    project_root = args.path or "."
    scenes_dir = os.path.join(project_root, "scenes")
    os.makedirs(scenes_dir, exist_ok=True)
    scene_path = os.path.join(scenes_dir, f"{args.name}.scene.reality")
    scene_data = {
        "name": args.name,
        "format": "reality-engine-scene/1",
        "version": "1.0",
        "entities": [],
    }
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(scene_data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    data = {"scene": args.name, "path": scene_path, "entities": 0}
    return ok_result(data=data)


def cmd_reality_scene_load(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.name}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.name}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    result_data = {
        "scene": data.get("name", args.name),
        "format": data.get("format", "unknown"),
        "version": data.get("version", "unknown"),
        "entities": len(data.get("entities", [])),
        "path": scene_path,
    }
    return ok_result(data=result_data)


def cmd_reality_scene_export(args, json_mode):
    project_root = args.path or "."
    scenes_dir = os.path.join(project_root, "scenes")
    source = os.path.join(scenes_dir, f"{args.name}.scene.reality")
    if not os.path.isfile(source):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.name}")
    try:
        with open(source, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    output_path = args.output or os.path.join(scenes_dir, f"{args.name}.exported.reality")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("EXPORT_WRITE_FAILED", str(exc))
    data = {
        "scene": args.name,
        "input": source,
        "output": output_path,
        "format": "reality-engine-scene/1",
    }
    return ok_result(data=data)


def cmd_reality_entity_create(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    entity_id = str(_uuid.uuid4())
    entity = {
        "id": entity_id,
        "name": args.name,
        "transform": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]},
        "components": {},
    }
    data.setdefault("entities", []).append(entity)
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    result_data = {"scene": args.scene, "entity": args.name, "id": entity_id, "path": scene_path}
    return ok_result(data=result_data)


def cmd_reality_entity_inspect(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    for entity in data.get("entities", []):
        if entity.get("id") == args.id or entity.get("name") == args.id:
            return ok_result(data=entity)
    return error_result("ENTITY_NOT_FOUND", f"No entity: {args.id}")


def cmd_reality_entity_modify(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    found = False
    for entity in data.get("entities", []):
        if entity.get("id") == args.id or entity.get("name") == args.id:
            found = True
            if args.property:
                for p in args.property:
                    if "=" in p:
                        k, v = p.split("=", 1)
                        if k == "name":
                            entity["name"] = v
                        elif k in ("position", "rotation", "scale"):
                            try:
                                vals = [float(x) for x in v.split(",")]
                                entity.setdefault("transform", {})[k] = vals
                            except ValueError:
                                pass
            break
    if not found:
        return error_result("ENTITY_NOT_FOUND", f"No entity: {args.id}")
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    return ok_result(data={"scene": args.scene, "entity": args.id, "modified": True})


def cmd_reality_component_add(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    found = False
    for entity in data.get("entities", []):
        if entity.get("id") == args.id or entity.get("name") == args.id:
            found = True
            entity.setdefault("components", {})[args.component] = {}
            break
    if not found:
        return error_result("ENTITY_NOT_FOUND", f"No entity: {args.id}")
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    return ok_result(data={"scene": args.scene, "entity": args.id, "component": args.component, "added": True})


def cmd_reality_component_remove(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    found = False
    removed = False
    for entity in data.get("entities", []):
        if entity.get("id") == args.id or entity.get("name") == args.id:
            found = True
            if args.component in entity.get("components", {}):
                del entity["components"][args.component]
                removed = True
            break
    if not found:
        return error_result("ENTITY_NOT_FOUND", f"No entity: {args.id}")
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    return ok_result(data={"scene": args.scene, "entity": args.id, "component": args.component, "removed": removed})


def cmd_reality_physics_configure(args, json_mode):
    project_root = args.path or "."
    scene_path = os.path.join(project_root, "scenes", f"{args.scene}.scene.reality")
    if not os.path.isfile(scene_path):
        return error_result("SCENE_NOT_FOUND", f"No scene: {args.scene}")
    try:
        with open(scene_path, "r", encoding="utf-8") as f:
            data = _json.load(f)
    except (OSError, _json.JSONDecodeError) as exc:
        return error_result("SCENE_READ_FAILED", str(exc))
    found = False
    for entity in data.get("entities", []):
        if entity.get("id") == args.id or entity.get("name") == args.id:
            found = True
            physics = {
                "body_type": args.body_type,
                "mass": args.mass,
                "friction": args.friction,
                "restitution": args.restitution,
                "gravity_enabled": args.gravity,
                "collider": {"shape": args.collider_shape},
            }
            entity.setdefault("components", {})["physics"] = physics
            break
    if not found:
        return error_result("ENTITY_NOT_FOUND", f"No entity: {args.id}")
    try:
        with open(scene_path, "w", encoding="utf-8") as f:
            _json.dump(data, f, indent=2)
    except OSError as exc:
        return error_result("SCENE_WRITE_FAILED", str(exc))
    return ok_result(data={"scene": args.scene, "entity": args.id, "physics_configured": True})


def cmd_reality_physics_simulate(args, json_mode):
    project_root = args.path or "."
    result = _run_runtime([project_root, "--frames", str(args.frames), "--diagnostics"], timeout=args.timeout)
    return result


def cmd_reality_runtime_launch(args, json_mode):
    project_root = args.path or "."
    result = _run_runtime([project_root, "--frames", str(args.frames)], timeout=args.timeout)
    return result


def cmd_reality_runtime_status(args, json_mode):
    runtime = _runtime_binary()
    data = {
        "runtime_path": runtime,
        "runtime_available": os.path.isfile(runtime),
        "physics_backend": "jolt",
        "renderer": "headless",
        "platform": "linux",
    }
    return ok_result(data=data)


def cmd_reality_runtime_inspect(args, json_mode):
    project_root = args.path or "."
    result = _run_runtime([project_root, "--frames", "1", "--diagnostics"], timeout=args.timeout)
    return result


def cmd_reality_runtime_stop(args, json_mode):
    return ok_result(data={"status": "stopped", "note": "Runtime runs synchronously in Phase 1"})


def cmd_reality_asset_list(args, json_mode):
    project_root = args.path or "."
    assets_dir = os.path.join(project_root, "assets")
    assets = []
    if os.path.isdir(assets_dir):
        for fname in os.listdir(assets_dir):
            fpath = os.path.join(assets_dir, fname)
            if os.path.isfile(fpath):
                assets.append({"name": fname, "path": fpath, "size_bytes": os.path.getsize(fpath)})
    return ok_result(data={"assets": assets, "count": len(assets)})


def cmd_reality_engine_diagnostics(args, json_mode):
    data = {
        "engine": "Reality Engine",
        "version": "0.1.0-phase1",
        "modules": [
            "core", "ecs", "world", "scene", "assets", "physics",
            "rendering", "platform", "input", "animation", "audio",
            "navigation", "scripting", "gameplay", "diagnostics",
        ],
        "physics_backend": "jolt",
        "renderer": "headless",
        "platform": "linux",
    }
    return ok_result(data=data)
