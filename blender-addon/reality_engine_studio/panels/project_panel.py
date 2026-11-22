"""
Panel 1: Project Panel
Project creation and management for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty


class RES_OT_project_create(Operator):
    """Create a new Reality Engine project."""
    bl_idname = "res.project_create"
    bl_label = "Create Project"
    bl_description = "Create a new Reality Engine project directory"

    project_name: StringProperty(name="Project Name", default="MyRealityProject")
    project_path: StringProperty(name="Path", default="")

    def execute(self, context):
        import subprocess
        import sys
        import os

        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")

        cmd = [
            sys.executable, cli_path,
            "reality", "project-create",
            self.project_name,
            "--path", self.project_path or ".",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Project '{self.project_name}' created" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_project_panel(Panel):
    """Project creation panel."""
    bl_idname = "RES_PT_project_panel"
    bl_label = "Project"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Project", icon="FILE_FOLDER")

        row = layout.row()
        row.prop(context.scene, "res_project_name", text="Name")

        row = layout.row()
        row.prop(context.scene, "res_project_path", text="Path")

        row = layout.row()
        row.operator("res.project_create", icon="ADD")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_project_name = bpy.props.StringProperty(
            name="Project Name", default="MyRealityProject"
        )
        bpy.types.Scene.res_project_path = bpy.props.StringProperty(
            name="Project Path", default=""
        )
        bpy.utils.register_class(RES_OT_project_create)
        bpy.utils.register_class(RES_PT_project_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_project_panel)
        bpy.utils.unregister_class(RES_OT_project_create)
        del bpy.types.Scene.res_project_name
        del bpy.types.Scene.res_project_path
