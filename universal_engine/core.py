"""Core platform API.

Shared by the CLI and the MCP server. Provides the project, scene, and asset
data models plus the adapter interface. Pure Python — no Blender/Godot required.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from universal_engine import PLANNED, UNAVAILABLE

PROJECT_FILENAME = "universal-engine.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Transform:
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObjectDef:
    id: str
    name: str
    type: str = "Empty"  # Empty | Mesh | Camera | Light | ...
    transform: Transform = field(default_factory=Transform)
    parent: Optional[str] = None
    components: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["transform"] = self.transform.to_dict()
        return d


@dataclass
class Scene:
    name: str
    objects: List[ObjectDef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_object(self, obj: ObjectDef) -> None:
        self.objects.append(obj)

    def find_object(self, object_id: str) -> Optional[ObjectDef]:
        for obj in self.objects:
            if obj.id == object_id:
                return obj
        return None

    def find_object_by_name(self, name: str) -> Optional[ObjectDef]:
        for obj in self.objects:
            if obj.name == name:
                return obj
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "objects": [o.to_dict() for o in self.objects],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        scene = cls(name=data.get("name", "Untitled"), metadata=data.get("metadata", {}))
        for o in data.get("objects", []):
            t = o.get("transform", {})
            scene.add_object(
                ObjectDef(
                    id=o.get("id", str(uuid.uuid4())),
                    name=o.get("name", "Object"),
                    type=o.get("type", "Empty"),
                    transform=Transform(
                        position=t.get("position", [0.0, 0.0, 0.0]),
                        rotation=t.get("rotation", [0.0, 0.0, 0.0]),
                        scale=t.get("scale", [1.0, 1.0, 1.0]),
                    ),
                    parent=o.get("parent"),
                    components=o.get("components", {}),
                    metadata=o.get("metadata", {}),
                )
            )
        return scene


@dataclass
class AssetRecord:
    path: str
    format: str
    source: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str = PLANNED  # PLANNED | IMPORTED | OPTIMIZED | ...
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Result helper
# ---------------------------------------------------------------------------


def ok_result(data: Optional[Any] = None, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "code": "OK",
        "data": data,
        "error": None,
        "warnings": warnings or [],
    }


def error_result(code: str, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "data": data,
        "error": {"code": code, "message": message},
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project:
    """A game project on disk.

    Layout:
        <root>/
          universal-engine.json     # project descriptor
          scenes/                   # scene JSON files
          assets/                   # asset records + source assets
          scripts/                  # gameplay scripts
          builds/                   # build artifacts
    """

    def __init__(self, root: str, name: Optional[str] = None):
        self.root = os.path.abspath(root)
        self.name = name or os.path.basename(self.root)
        self.descriptor_path = os.path.join(self.root, PROJECT_FILENAME)
        self.scenes_dir = os.path.join(self.root, "scenes")
        self.assets_dir = os.path.join(self.root, "assets")
        self.scripts_dir = os.path.join(self.root, "scripts")
        self.builds_dir = os.path.join(self.root, "builds")

    @property
    def exists(self) -> bool:
        return os.path.isfile(self.descriptor_path)

    def descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "root": self.root,
            "version": "0.1.0",
            "format": "universal-engine-project/1",
            "scenes_dir": "scenes",
            "assets_dir": "assets",
            "scripts_dir": "scripts",
            "builds_dir": "builds",
        }

    def create(self) -> Dict[str, Any]:
        """Create the project directory structure and descriptor."""
        if self.exists:
            return error_result("PROJECT_EXISTS", f"Project already exists at {self.root}")
        try:
            for d in (self.root, self.scenes_dir, self.assets_dir, self.scripts_dir, self.builds_dir):
                os.makedirs(d, exist_ok=True)
            with open(self.descriptor_path, "w", encoding="utf-8") as f:
                json.dump(self.descriptor(), f, indent=2)
            return ok_result(data=self.descriptor())
        except OSError as exc:  # pragma: no cover - filesystem errors
            return error_result("CREATE_FAILED", str(exc))

    def load(self) -> Dict[str, Any]:
        if not self.exists:
            return error_result("PROJECT_NOT_FOUND", f"No project at {self.root}")
        try:
            with open(self.descriptor_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.name = data.get("name", self.name)
            return ok_result(data=data)
        except (OSError, json.JSONDecodeError) as exc:
            return error_result("LOAD_FAILED", str(exc))

    def validate(self) -> Dict[str, Any]:
        """Validate the project structure. Returns issues (not a hard failure)."""
        issues: List[str] = []
        if not self.exists:
            issues.append("missing universal-engine.json")
        for d in (self.scenes_dir, self.assets_dir, self.scripts_dir, self.builds_dir):
            if not os.path.isdir(d):
                issues.append(f"missing directory: {os.path.basename(d)}")
        return ok_result(data={"valid": len(issues) == 0, "issues": issues})

    def list_scenes(self) -> List[str]:
        if not os.path.isdir(self.scenes_dir):
            return []
        return sorted(
            f for f in os.listdir(self.scenes_dir) if f.endswith(".scene.json")
        )

    def scene_path(self, name: str) -> str:
        if not name.endswith(".scene.json"):
            name = name + ".scene.json"
        return os.path.join(self.scenes_dir, name)


# ---------------------------------------------------------------------------
# Adapter interface
# ---------------------------------------------------------------------------


class AdapterBase:
    """Base class for platform adapters (Blender, Godot, physics, ...).

    Each adapter declares its capabilities, version, and compatibility so the
    platform can decide whether to use it without requiring the backend to be
    installed.
    """

    name: str = "base"
    version: str = "0.0.0"
    status: str = PLANNED
    available: bool = False

    def check_availability(self) -> bool:
        """Return True if the backend is installed and usable."""
        return self.available

    def capabilities(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status,
            "available": self.check_availability(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} available={self.available} status={self.status}>"
