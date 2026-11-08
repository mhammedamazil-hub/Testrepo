class_name AlpineLakeEffects
extends Node

# A real shared-world mirrored-camera pass. It is deliberately 512x288;
# the playable main view remains native 1920x1080. No ray-tracing claim.
var game: Node3D
var viewport: SubViewport
var mirror: Camera3D
var water: ShaderMaterial
var shafts: ShaderMaterial
var mirror_frames: int = 0
const SUN_POSITION := Vector3(20,285,-800)

func setup(owner_game: Node3D, lake: MeshInstance3D) -> void:
	game = owner_game
	water = lake.material_override as ShaderMaterial
	lake.layers = 2
	viewport = SubViewport.new()
	viewport.name = "PlanarLakeReflection"
	viewport.size = Vector2i(512,288)
	viewport.world_3d = game.get_world_3d()
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	viewport.transparent_bg = false
	add_child(viewport)
	mirror = Camera3D.new()
	mirror.cull_mask = 1 # Water and post-process quad use layer 2: no recursion.
	mirror.current = true
	mirror.fov = game.camera.fov
	mirror.near = game.camera.near
	mirror.far = game.camera.far
	viewport.add_child(mirror)
	water.set_shader_parameter("live_reflection",viewport.get_texture())
	var quad := MeshInstance3D.new()
	quad.name = "DepthOccludedSunShafts"
	var plane := QuadMesh.new()
	plane.size = Vector2(2,2)
	quad.mesh = plane
	quad.layers = 2
	quad.position.z = -1
	quad.extra_cull_margin = 16384
	quad.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	shafts = ShaderMaterial.new()
	shafts.shader = preload("res://shaders/sun_shafts.gdshader")
	shafts.render_priority = 110
	quad.material_override = shafts
	game.camera.add_child(quad)

func _process(_delta: float) -> void:
	if not is_instance_valid(game.camera): return
	var source: Camera3D = game.camera
	var position := source.global_position
	var forward := -source.global_basis.z
	var up := source.global_basis.y
	position.y = -position.y
	forward.y = -forward.y
	up.y = -up.y
	mirror.look_at_from_position(position,position+forward,up)
	var view_projection := mirror.get_camera_projection()*Projection(mirror.global_transform.affine_inverse())
	water.set_shader_parameter("reflection_view_projection",view_projection)
	mirror_frames += 1
	var pixel := source.unproject_position(SUN_POSITION)
	var size := Vector2(source.get_viewport().get_visible_rect().size)
	shafts.set_shader_parameter("sun_uv",pixel/size)
	shafts.set_shader_parameter("sun_visible",not source.is_position_behind(SUN_POSITION))
