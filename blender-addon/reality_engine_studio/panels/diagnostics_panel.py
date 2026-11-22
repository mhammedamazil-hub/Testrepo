"""
Panel 8: Diagnostics Panel
Engine diagnostics for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy


class RES_OT_engine_diagnostics(Operator):
    """Get engine diagnostics."""
    bl_idname = "res.engine_diagnostics"
    bl_label = "Engine Diagnostics"
    bl_description = "Get Reality Engine diagnostics"

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [sys.executable, cli_path, "reality", "engine-diagnostics"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.report({"INFO"}, "Engine diagnostics retrieved")
                # Print diagnostics to console
                print("=== Reality Engine Diagnostics ===")
                print(result.stdout)
            else:
                self.report({"ERROR"}, f"Failed: {result.stderr.strip()}")
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_diagnostics_panel(Panel):
    """Engine diagnostics panel."""
    bl_idname = "RES_PT_diagnostics_panel"
    bl_label = "Diagnostics"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Diagnostics", icon="ERROR")

        row = layout.row()
        row.operator("res.engine_diagnostics", icon="PREVIEWS")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.register_class(RES_OT_engine_diagnostics)
        bpy.utils.register_class(RES_PT_diagnostics_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_diagnostics_panel)
        bpy.utils.unregister_class(RES_OT_engine_diagnostics)
