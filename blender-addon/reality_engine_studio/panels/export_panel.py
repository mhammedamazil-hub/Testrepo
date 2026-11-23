"""
Panel 7: Export Panel
Scene export for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty


class RES_OT_scene_export(Operator):
    """Export a scene."""
    bl_idname = "res.scene_export"
    bl_label = "Export Scene"
    bl_description = "Export a Reality Engine scene"

    scene_name: StringProperty(name="Scene Name")
    scene_path: StringProperty(name="Path", default=".")
    output_path: StringProperty(name="Output Path", default="")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "scene-export",
            self.scene_name,
            "--path", self.scene_path,
        ]
        if self.output_path:
            cmd += ["--output", self.output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Scene '{self.scene_name}' exported" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_export_panel(Panel):
    """Scene export panel."""
    bl_idname = "RES_PT_export_panel"
    bl_label = "Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Export", icon="EXPORT")

        row = layout.row()
        row.prop(context.scene, "res_export_scene", text="Scene Name")

        row = layout.row()
        row.prop(context.scene, "res_export_path", text="Path")

        row = layout.row()
        row.prop(context.scene, "res_export_output", text="Output Path")

        row = layout.row()
        row.operator("res.scene_export", icon="EXPORT")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_export_scene = bpy.props.StringProperty(
            name="Scene Name", default="Level1"
        )
        bpy.types.Scene.res_export_path = bpy.props.StringProperty(
            name="Path", default="."
        )
        bpy.types.Scene.res_export_output = bpy.props.StringProperty(
            name="Output Path", default=""
        )
        bpy.utils.register_class(RES_OT_scene_export)
        bpy.utils.register_class(RES_PT_export_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_export_panel)
        bpy.utils.unregister_class(RES_OT_scene_export)
        del bpy.types.Scene.res_export_scene
        del bpy.types.Scene.res_export_path
        del bpy.types.Scene.res_export_output
