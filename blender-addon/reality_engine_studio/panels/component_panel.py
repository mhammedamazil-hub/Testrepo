"""
Panel 4: Component Panel
Component add/remove for entities in Reality Engine scenes.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty


class RES_OT_component_add(Operator):
    """Add a component to an entity."""
    bl_idname = "res.component_add"
    bl_label = "Add Component"
    bl_description = "Add a component to an entity"

    scene_name: StringProperty(name="Scene Name")
    entity_id: StringProperty(name="Entity ID or Name")
    component_type: StringProperty(name="Component Type", default="Transform")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "component-add",
            self.scene_name, self.entity_id, self.component_type,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Component '{self.component_type}' added" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_component_remove(Operator):
    """Remove a component from an entity."""
    bl_idname = "res.component_remove"
    bl_label = "Remove Component"
    bl_description = "Remove a component from an entity"

    scene_name: StringProperty(name="Scene Name")
    entity_id: StringProperty(name="Entity ID or Name")
    component_type: StringProperty(name="Component Type")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "component-remove",
            self.scene_name, self.entity_id, self.component_type,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Component '{self.component_type}' removed" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_component_panel(Panel):
    """Component management panel."""
    bl_idname = "RES_PT_component_panel"
    bl_label = "Component"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Component", icon="CON_REQUIRED")

        row = layout.row()
        row.prop(context.scene, "res_comp_scene", text="Scene")

        row = layout.row()
        row.prop(context.scene, "res_comp_entity", text="Entity ID/Name")

        row = layout.row()
        row.prop(context.scene, "res_comp_type", text="Component")

        row = layout.row()
        row.operator("res.component_add", icon="ADD")

        row = layout.row()
        row.operator("res.component_remove", icon="REMOVE")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_comp_scene = bpy.props.StringProperty(
            name="Scene Name", default="Level1"
        )
        bpy.types.Scene.res_comp_entity = bpy.props.StringProperty(
            name="Entity ID/Name", default=""
        )
        bpy.types.Scene.res_comp_type = bpy.props.StringProperty(
            name="Component Type", default="Transform"
        )
        bpy.utils.register_class(RES_OT_component_add)
        bpy.utils.register_class(RES_OT_component_remove)
        bpy.utils.register_class(RES_PT_component_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_component_panel)
        bpy.utils.unregister_class(RES_OT_component_remove)
        bpy.utils.unregister_class(RES_OT_component_add)
        del bpy.types.Scene.res_comp_scene
        del bpy.types.Scene.res_comp_entity
        del bpy.types.Scene.res_comp_type
