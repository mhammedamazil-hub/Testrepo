"""
Panel 3: Entity Panel
Entity creation and inspection for Reality Engine scenes.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty


class RES_OT_entity_create(Operator):
    """Create an entity in a scene."""
    bl_idname = "res.entity_create"
    bl_label = "Create Entity"
    bl_description = "Create a new entity in a Reality Engine scene"

    scene_name: StringProperty(name="Scene Name")
    entity_name: StringProperty(name="Entity Name", default="Entity")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "entity-create",
            self.scene_name, self.entity_name,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Entity '{self.entity_name}' created" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_entity_inspect(Operator):
    """Inspect an entity."""
    bl_idname = "res.entity_inspect"
    bl_label = "Inspect Entity"
    bl_description = "Inspect an entity's properties"

    scene_name: StringProperty(name="Scene Name")
    entity_id: StringProperty(name="Entity ID or Name")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "entity-inspect",
            self.scene_name, self.entity_id,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Entity inspected" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_entity_modify(Operator):
    """Modify an entity property."""
    bl_idname = "res.entity_modify"
    bl_label = "Modify Entity"
    bl_description = "Modify an entity property"

    scene_name: StringProperty(name="Scene Name")
    entity_id: StringProperty(name="Entity ID or Name")
    property_str: StringProperty(name="Property (key=value)")
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "entity-modify",
            self.scene_name, self.entity_id,
            "--property", self.property_str,
            "--path", self.scene_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Entity modified" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_entity_panel(Panel):
    """Entity management panel."""
    bl_idname = "RES_PT_entity_panel"
    bl_label = "Entity"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Entity", icon="OBJECT_DATA")

        row = layout.row()
        row.prop(context.scene, "res_entity_scene", text="Scene")

        row = layout.row()
        row.prop(context.scene, "res_entity_name", text="Name")

        row = layout.row()
        row.operator("res.entity_create", icon="ADD")

        layout.separator()

        row = layout.row()
        row.prop(context.scene, "res_inspect_entity_id", text="Entity ID/Name")

        row = layout.row()
        row.operator("res.entity_inspect", icon="ZOOM_IN")

        row = layout.row()
        row.prop(context.scene, "res_modify_property", text="Property")

        row = layout.row()
        row.operator("res.entity_modify", icon="PREFERENCES")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_entity_scene = bpy.props.StringProperty(
            name="Scene Name", default="Level1"
        )
        bpy.types.Scene.res_entity_name = bpy.props.StringProperty(
            name="Entity Name", default="Entity"
        )
        bpy.types.Scene.res_inspect_entity_id = bpy.props.StringProperty(
            name="Entity ID/Name", default=""
        )
        bpy.types.Scene.res_modify_property = bpy.props.StringProperty(
            name="Property (key=value)", default="name=NewName"
        )
        bpy.utils.register_class(RES_OT_entity_create)
        bpy.utils.register_class(RES_OT_entity_inspect)
        bpy.utils.register_class(RES_OT_entity_modify)
        bpy.utils.register_class(RES_PT_entity_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_entity_panel)
        bpy.utils.unregister_class(RES_OT_entity_modify)
        bpy.utils.unregister_class(RES_OT_entity_inspect)
        bpy.utils.unregister_class(RES_OT_entity_create)
        del bpy.types.Scene.res_entity_scene
        del bpy.types.Scene.res_entity_name
        del bpy.types.Scene.res_inspect_entity_id
        del bpy.types.Scene.res_modify_property
