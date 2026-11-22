"""
Panel 5: Physics Panel
Physics configuration and simulation for Reality Engine.
"""

from .. import _BPY_AVAILABLE, Panel, Operator, StringProperty, IntProperty, BoolProperty, FloatProperty, EnumProperty

if _BPY_AVAILABLE:
    import bpy
    from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty


class RES_OT_physics_configure(Operator):
    """Configure physics for an entity."""
    bl_idname = "res.physics_configure"
    bl_label = "Configure Physics"
    bl_description = "Configure physics body for an entity"

    scene_name: StringProperty(name="Scene Name")
    entity_id: StringProperty(name="Entity ID or Name")
    body_type: EnumProperty(
        name="Body Type",
        items=[
            ("static", "Static", "Static body"),
            ("dynamic", "Dynamic", "Dynamic body"),
            ("kinematic", "Kinematic", "Kinematic body"),
        ],
        default="dynamic",
    )
    mass: FloatProperty(name="Mass", default=1.0)
    friction: FloatProperty(name="Friction", default=0.5)
    restitution: FloatProperty(name="Restitution", default=0.0)
    gravity: BoolProperty(name="Gravity", default=True)
    collider_shape: EnumProperty(
        name="Collider Shape",
        items=[
            ("box", "Box", "Box collider"),
            ("sphere", "Sphere", "Sphere collider"),
            ("capsule", "Capsule", "Capsule collider"),
            ("mesh", "Mesh", "Mesh collider"),
        ],
        default="box",
    )
    scene_path: StringProperty(name="Path", default=".")

    def execute(self, context):
        import subprocess, sys, os
        repo_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".."
        ))
        cli_path = os.path.join(repo_root, "universal_engine", "__main__.py")
        cmd = [
            sys.executable, cli_path,
            "reality", "physics-configure",
            self.scene_name, self.entity_id,
            "--body-type", self.body_type,
            "--mass", str(self.mass),
            "--friction", str(self.friction),
            "--restitution", str(self.restitution),
            "--collider-shape", self.collider_shape,
        ]
        if not self.gravity:
            cmd.append("--no-gravity")
        cmd += ["--path", self.scene_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Physics configured for '{self.entity_id}'" if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_OT_physics_simulate(Operator):
    """Run physics simulation."""
    bl_idname = "res.physics_simulate"
    bl_label = "Simulate Physics"
    bl_description = "Run physics simulation via the standalone runtime"

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
            "reality", "physics-simulate",
            "--path", self.scene_path,
            "--frames", str(self.frames),
            "--timeout", str(self.timeout),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            self.report(
                {"INFO" if result.returncode == 0 else "ERROR"},
                f"Physics simulation complete ({self.frames} frames)"
                if result.returncode == 0
                else f"Failed: {result.stderr.strip()}"
            )
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
        return {"FINISHED"}


class RES_PT_physics_panel(Panel):
    """Physics configuration panel."""
    bl_idname = "RES_PT_physics_panel"
    bl_label = "Physics"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Reality Engine"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Reality Engine Physics", icon="PHYSICS")

        row = layout.row()
        row.prop(context.scene, "res_phys_scene", text="Scene")

        row = layout.row()
        row.prop(context.scene, "res_phys_entity", text="Entity ID/Name")

        row = layout.row()
        row.prop(context.scene, "res_phys_body_type", text="Body Type")

        row = layout.row()
        row.prop(context.scene, "res_phys_mass", text="Mass")

        row = layout.row()
        row.prop(context.scene, "res_phys_friction", text="Friction")

        row = layout.row()
        row.prop(context.scene, "res_phys_restitution", text="Restitution")

        row = layout.row()
        row.prop(context.scene, "res_phys_gravity", text="Gravity")

        row = layout.row()
        row.prop(context.scene, "res_phys_collider", text="Collider Shape")

        row = layout.row()
        row.operator("res.physics_configure", icon="CONSTRAINT")

        layout.separator()

        row = layout.row()
        row.prop(context.scene, "res_phys_sim_path", text="Sim Path")

        row = layout.row()
        row.prop(context.scene, "res_phys_frames", text="Frames")

        row = layout.row()
        row.operator("res.physics_simulate", icon="PLAY")


def register():
    if _BPY_AVAILABLE:
        import bpy
        bpy.types.Scene.res_phys_scene = bpy.props.StringProperty(
            name="Scene Name", default="Level1"
        )
        bpy.types.Scene.res_phys_entity = bpy.props.StringProperty(
            name="Entity ID/Name", default=""
        )
        bpy.types.Scene.res_phys_body_type = bpy.props.EnumProperty(
            name="Body Type",
            items=[("static", "Static", ""), ("dynamic", "Dynamic", ""), ("kinematic", "Kinematic", "")],
            default="dynamic",
        )
        bpy.types.Scene.res_phys_mass = bpy.props.FloatProperty(name="Mass", default=1.0)
        bpy.types.Scene.res_phys_friction = bpy.props.FloatProperty(name="Friction", default=0.5)
        bpy.types.Scene.res_phys_restitution = bpy.props.FloatProperty(name="Restitution", default=0.0)
        bpy.types.Scene.res_phys_gravity = bpy.props.BoolProperty(name="Gravity", default=True)
        bpy.types.Scene.res_phys_collider = bpy.props.EnumProperty(
            name="Collider Shape",
            items=[("box", "Box", ""), ("sphere", "Sphere", ""), ("capsule", "Capsule", ""), ("mesh", "Mesh", "")],
            default="box",
        )
        bpy.types.Scene.res_phys_sim_path = bpy.props.StringProperty(name="Sim Path", default=".")
        bpy.types.Scene.res_phys_frames = bpy.props.IntProperty(name="Frames", default=60)
        bpy.utils.register_class(RES_OT_physics_configure)
        bpy.utils.register_class(RES_OT_physics_simulate)
        bpy.utils.register_class(RES_PT_physics_panel)


def unregister():
    if _BPY_AVAILABLE:
        import bpy
        bpy.utils.unregister_class(RES_PT_physics_panel)
        bpy.utils.unregister_class(RES_OT_physics_simulate)
        bpy.utils.unregister_class(RES_OT_physics_configure)
        for prop in [
            "res_phys_scene", "res_phys_entity", "res_phys_body_type",
            "res_phys_mass", "res_phys_friction", "res_phys_restitution",
            "res_phys_gravity", "res_phys_collider", "res_phys_sim_path", "res_phys_frames",
        ]:
            del bpy.types.Scene[prop]
