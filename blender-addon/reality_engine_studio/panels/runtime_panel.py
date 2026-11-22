"""
Panel 6: Runtime Panel
Runtime launch/inspect/stop for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty, IntProperty


class RES_OT_runtime_launch(Operator):
    """Launch the standalone runtime."""
    bl_idname = "res.runtime_launch"
    bl_label = "Launch Runtime"
    bl_description = "Launch the standalone Reality Engine runtime"

    scene_path: StringProperty(name="Path", default=".")
    frames: IntProperty(name="Frames", default=60)
    timeout: IntProperty(name="Timeout (s)", default=30)

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "runtime-launch",
            "--path", self.scene_path,
            "--frames", str(self.frames),
            "--timeout", str(self.timeout),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Runtime launched ({self.frames} frames)"
                if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_runtime_status(Operator):
    """Check runtime status."""
    bl_idname = "res.runtime_status"
    bl_label = "Runtime Status"
    bl_description = "Check Reality Engine runtime status"

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [sys.executable, cli_path, "reality", "runtime-status"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                "Runtime available" if result.returncode == 0
                else f"Runtime unavailable: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_runtime_inspect(Operator):
    """Inspect runtime state."""
    bl_idname = "res.runtime_inspect"
    bl_label = "Inspect Runtime"
    bl_description = "Inspect Reality Engine runtime state"

    scene_path: StringProperty(name="Path", default=".")
    timeout: IntProperty(name="Timeout (s)", default=30)

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "runtime-inspect",
            "--path", self.scene_path,
            "--timeout", str(self.timeout),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                "Runtime inspected" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_runtime_stop(Operator):
    """Stop the runtime."""
    bl_idname = "res.runtime_stop"
    bl_label = "Stop Runtime"
    bl_description = "Stop the Reality Engine runtime"

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [sys.executable, cli_path, "reality", "runtime-stop"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                "Runtime stopped" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_runtime_panel(Panel):
    """Runtime control panel."""
    bl_idname = "RES_PT_runtime_panel"
    bl_label = "Runtime"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Runtime", icon="PLAY")

        row = layout.row()
        row.prop(context.scene, "res_rt_path", text="Project Path")

        row = layout.row()
        row.prop(context.scene, "res_rt_frames", text="Frames")

        row = layout.row()
        row.operator("res.runtime_launch", icon="PLAY")

        layout.separator()

        row = layout.row()
        row.operator("res.runtime_status", icon="INFO")

        row = layout.row()
        row.prop(context.scene, "res_rt_inspect_path", text="Inspect Path")

        row = layout.row()
        row.operator("res.runtime_inspect", icon="ZOOM_IN")

        row = layout.row()
        row.operator("res.runtime_stop", icon="PANEL_CLOSE")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_rt_path = bpy.props.StringProperty(
            name="Project Path", default="."
        )
        bpy.types.Scene.res_rt_frames = bpy.props.IntProperty(name="Frames", default=60)
        bpy.types.Scene.res_rt_inspect_path = bpy.props.StringProperty(
            name="Inspect Path", default="."
        )
        bpy.utils.register_class(RES_OT_runtime_launch)
        bpy.utils.register_class(RES_OT_runtime_status)
        bpy.utils.register_class(RES_OT_runtime_inspect)
        bpy.utils.register_class(RES_OT_runtime_stop)
        bpy.utils.register_class(RES_PT_runtime_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_runtime_panel)
        bpy.utils.unregister_class(RES_OT_runtime_stop)
        bpy.utils.unregister_class(RES_OT_runtime_inspect)
        bpy.utils.unregister_class(RES_OT_runtime_status)
        bpy.utils.unregister_class(RES_OT_runtime_launch)
        del bpy.types.Scene.res_rt_path
        del bpy.types.Scene.res_rt_frames
        del bpy.types.Scene.res_rt_inspect_path
