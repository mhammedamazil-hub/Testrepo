"""
Panel 2: Scene Panel
Scene creation and management for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty


class RES_OT_scene_create(Operator):
    """Create a new scene."""
    bl_idname = "res.scene_create"
    bl_label = "Create Scene"
    bl_description = "Create a new Reality Engine scene"

    scene_name: StringProperty(name="Scene Name", default="Level1")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "scene-create",
            self.scene_name,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Scene '{self.scene_name}' created" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_scene_load(Operator):
    """Load and inspect a scene."""
    bl_idname = "res.scene_load"
    bl_label = "Load Scene"
    bl_description = "Load and validate a Reality Engine scene"

    scene_name: StringProperty(name="Scene Name")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "scene-load",
            self.scene_name,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Scene loaded: {result.stdout.strip()}" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_scene_panel(Panel):
    """Scene management panel."""
    bl_idname = "RES_PT_scene_panel"
    bl_label = "Scene"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Scene", icon="SCENE_DATA")

        row = layout.row()
        row.prop(context.scene, "res_scene_name", text="Name")

        row = layout.row()
        row.prop(context.scene, "res_scene_path", text="Path")

        row = layout.row()
        row.operator("res.scene_create", icon="ADD")

        row = layout.row()
        row.operator("res.scene_load", icon="FILE_FOLDER")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_scene_name = bpy.props.StringProperty(
            name="Scene Name", default="Level1"
        )
        bpy.types.Scene.res_scene_path = bpy.props.StringProperty(
            name="Scene Path", default="."
        )
        bpy.utils.register_class(RES_OT_scene_create)
        bpy.utils.register_class(RES_OT_scene_load)
        bpy.utils.register_class(RES_PT_scene_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_scene_panel)
        bpy.utils.unregister_class(RES_OT_scene_load)
        bpy.utils.unregister_class(RES_OT_scene_create)
        del bpy.types.Scene.res_scene_name
        del bpy.types.Scene.res_scene_path
