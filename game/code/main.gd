extends Node3D

signal mode_changed(driving: bool)
signal checkpoint_reached(index: int)

var player: AlpinePlayer
var car: AlpineCar
var touch_controls: AlpineTouchControls
var hud: AlpineHUD
var camera_rig: Node3D
var spring: SpringArm3D
var camera: Camera3D
var route: Array[Vector3] = []
var checkpoint_nodes: Array[MeshInstance3D] = []
var in_vehicle: bool = false
var playing: bool = false
var paused: bool = false
var camera_yaw: float = 0.0
var camera_pitch: float = -0.19
var orbit_timeout: float = 0.0
var elapsed: float = 0.0
var next_checkpoint: int = 0
var laps: int = 0
var best_lap: float = 0.0
var toast: String = ""
var toast_time: float = 0.0
var frame_ms: Array[float] = []
var elapsed_real: float = 0.0
var _telemetry_clock: float = 0.0
var _last_frame_usec: int = 0
var _measurement_started_usec: int = 0
var world_data: Dictionary
var wind: AudioStreamPlayer
var sun: DirectionalLight3D
var enhanced_shadows: bool = false
var _last_telemetry_usec: int = 0
var lake_effects: AlpineLakeEffects
var lake_node: MeshInstance3D
var _web_input

func _ready() -> void:
	Engine.max_fps = 60
	_input_map()
	world_data = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world_data.json"))
	for p in world_data["route"]:
		route.append(Vector3(p[0], p[1], p[2]))
	_build_world()
	_build_actors()
	_build_camera()
	_build_checkpoints()
	hud = AlpineHUD.new()
	hud.game = self
	add_child(hud)
	touch_controls = AlpineTouchControls.new()
	touch_controls.game = self
	hud.root.add_child(touch_controls)
	hud.configure_touch(touch_controls.enabled)
	if OS.has_feature("web"):
		_web_input = JavaScriptBridge.get_interface("alpineInputSignals")
	_reset_positions()
	player.set_active(false)
	car.set_physics_process(false)
	_read_best()
	if DisplayServer.get_name()!="headless" and ResourceLoader.exists("res://assets/wind.wav"):
		wind = AudioStreamPlayer.new()
		var audio := load("res://assets/wind.wav") as AudioStreamWAV
		audio.loop_mode = AudioStreamWAV.LOOP_FORWARD
		audio.loop_end = audio.data.size() / 2
		wind.stream = audio
		wind.volume_db = -26
		add_child(wind)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT and playing and not paused:
		toggle_pause()

func _input_map() -> void:
	var keys := {"forward":[KEY_W,KEY_UP],"back":[KEY_S,KEY_DOWN],"left":[KEY_A,KEY_LEFT],
		"right":[KEY_D,KEY_RIGHT],"sprint":[KEY_SHIFT],"jump":[KEY_SPACE],
		"interact":[KEY_E],"reset":[KEY_R],"pause":[KEY_ESCAPE],"fullscreen":[KEY_F],
		"mute":[KEY_M],"look_back":[KEY_Q],"quality":[KEY_F2],"benchmark":[KEY_F8],"touch":[KEY_T]}
	for action in keys:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in keys[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action,event)

func _build_world() -> void:
	var environment := Environment.new()
	var sky := Sky.new()
	var panorama := PanoramaSkyMaterial.new()
	panorama.panorama = preload("res://assets/sky.jpg")
	panorama.energy_multiplier = 0.8
	sky.sky_material = panorama
	sky.radiance_size = Sky.RADIANCE_SIZE_128
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.sky_rotation = Vector3(0, -PI/2, 0)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.62,0.71,0.77)
	environment.ambient_light_energy = 0.60
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.fog_enabled = true
	environment.fog_density = 0.00042
	environment.fog_light_color = Color(0.65,0.76,0.79)
	environment.fog_sun_scatter = 0.1
	environment.fog_sky_affect = 0.10
	var world := WorldEnvironment.new()
	world.environment = environment
	add_child(world)
	sun = DirectionalLight3D.new()
	sun.rotation_degrees = Vector3.ZERO
	sun.light_color = Color(1.0,0.98,0.92)
	sun.light_energy = 1.18
	sun.shadow_enabled = enhanced_shadows
	sun.directional_shadow_max_distance = 65
	sun.shadow_bias = 0.04
	add_child(sun)
	sun.look_at(-AlpineLakeEffects.SUN_POSITION.normalized(),Vector3.UP)
	for resource in [preload("res://assets/terrain.glb"),preload("res://assets/road.glb")]:
		var instance: Node3D = resource.instantiate()
		add_child(instance)
		_add_static_collision(instance)
		_apply_surface_detail(instance)
	_build_forest()
	_build_detail_scatter()
	var lake := MeshInstance3D.new()
	lake.name = "Lake"
	lake_node = lake
	var plane := PlaneMesh.new()
	plane.size = Vector2(320,460)
	plane.subdivide_width = 32
	plane.subdivide_depth = 46
	lake.mesh = plane
	lake.position = Vector3(0,0,-135)
	lake.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var water := ShaderMaterial.new()
	water.shader = preload("res://shaders/water.gdshader")
	water.set_shader_parameter("reflection_map",preload("res://assets/lake_reflection.jpg"))
	water.set_shader_parameter("ripple_map",preload("res://assets/ground_detail_normal.png"))
	water.set_shader_parameter("sun_direction",sun.global_basis.z)
	lake.material_override = water
	add_child(lake)
	_build_roadside()

func _add_static_collision(root: Node) -> void:
	if root is MeshInstance3D and not "Center_Lines" in root.name:
		var body := StaticBody3D.new()
		body.collision_layer = 1
		var shape := CollisionShape3D.new()
		shape.shape = root.mesh.create_trimesh_shape()
		body.add_child(shape)
		root.add_child(body)
	for child in root.get_children():
		if not child is StaticBody3D:
			_add_static_collision(child)

func _build_forest() -> void:
	var material := StandardMaterial3D.new()
	material.albedo_texture = preload("res://assets/spruce_impostor.png")
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	material.alpha_scissor_threshold = 0.38
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	material.billboard_keep_scale = true
	var quad := QuadMesh.new()
	quad.size = Vector2(0.5,1.0)
	quad.center_offset.y = 0.5
	quad.material = material
	var cells: Dictionary = {}
	var nearby: Array = []
	for p in world_data["forest"]:
		var position := Vector3(p[0],p[1],p[2])
		var near_road: bool = false
		for point in route:
			if Vector2(position.x-point.x,position.z-point.z).length_squared() < 32.0*32.0:
				near_road = true
				break
		if near_road:
			nearby.append([p[0],p[1],p[2],p[3],fmod(absf(float(p[0])*0.71),TAU)])
			continue
		var key := Vector2i(floori(p[0]/120.0),floori(p[2]/120.0))
		if not cells.has(key): cells[key] = []
		cells[key].append(p)
	for key in cells:
		var data: Array = cells[key]
		var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D
		multi.mesh = quad
		multi.instance_count = data.size()
		for i in range(data.size()):
			var p: Array = data[i]
			multi.set_instance_transform(i,Transform3D(Basis.IDENTITY.scaled(Vector3.ONE*float(p[3])),Vector3(p[0],p[1],p[2])))
		var instance := MultiMeshInstance3D.new()
		instance.name = "ForestCell_%s" % str(key)
		instance.multimesh = multi
		instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		instance.visibility_range_end = 900
		instance.visibility_range_end_margin = 50
		add_child(instance)
	var source := preload("res://assets/library/pine.glb").instantiate()
	var tree_mesh := _first_mesh(source)
	if tree_mesh: _scatter_cells(_instancing_mesh(tree_mesh),nearby,60,110,"RoadsideSpruce")
	_scatter_cells(quad,nearby,60,900,"SpruceFarLOD")
	source.free()

func _first_mesh(node: Node) -> MeshInstance3D:
	if node is MeshInstance3D: return node
	for child in node.get_children():
		var found := _first_mesh(child)
		if found: return found
	return null

func _instancing_mesh(source: MeshInstance3D) -> ArrayMesh:
	# GLTF stores some materials on the instance, not the ArrayMesh. Preserve
	# those overrides when moving geometry into a MultiMesh (otherwise white).
	var mesh := source.mesh.duplicate() as ArrayMesh
	for index in range(mesh.get_surface_count()):
		var material := source.get_active_material(index)
		if (("Roadside_Spruce" in source.name or "Library_Pine" in source.name) and index > 0 or "PolyHaven_Grass" in source.name) and material is StandardMaterial3D:
			var foliage := material.duplicate() as StandardMaterial3D
			foliage.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
			foliage.alpha_scissor_threshold = 0.18
			foliage.cull_mode = BaseMaterial3D.CULL_DISABLED
			foliage.roughness = 0.9
			material = foliage
		mesh.surface_set_material(index,material)
	return mesh

func _apply_surface_detail(node: Node) -> void:
	if node is MeshInstance3D:
		for index in range(node.mesh.get_surface_count()):
			var original := node.mesh.surface_get_material(index) as StandardMaterial3D
			if original and original.albedo_texture and "Alpine_" in node.name:
				var mat := ShaderMaterial.new()
				mat.shader = preload("res://shaders/terrain_detail.gdshader")
				mat.set_shader_parameter("base_map",original.albedo_texture)
				mat.set_shader_parameter("base_normal",original.normal_texture)
				mat.set_shader_parameter("detail_map",preload("res://assets/library/ground_diff.jpg"))
				mat.set_shader_parameter("detail_normal",preload("res://assets/library/ground_normal.jpg"))
				mat.set_shader_parameter("mountain","Massif" in node.name)
				node.set_surface_override_material(index,mat)
			elif original and "Lakeside_Road" in node.name:
				var mat := original.duplicate() as StandardMaterial3D
				mat.normal_enabled = true
				mat.normal_texture = preload("res://assets/ground_detail_normal.png")
				mat.normal_scale = 0.22
				mat.roughness = 0.94
				node.set_surface_override_material(index,mat)
	for child in node.get_children(): _apply_surface_detail(child)

func _scatter_cells(mesh: Mesh, placements: Array, cell_size: float, distance: float, prefix: String) -> void:
	var cells: Dictionary = {}
	for p in placements:
		var key := Vector2i(floori(float(p[0])/cell_size),floori(float(p[2])/cell_size))
		if not cells.has(key): cells[key] = []
		cells[key].append(p)
	for key in cells:
		var data: Array = cells[key]
		var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D
		multi.mesh = mesh
		multi.instance_count = data.size()
		for i in range(data.size()):
			var p: Array = data[i]
			var basis := Basis(Vector3.UP,float(p[4])).scaled(Vector3.ONE*float(p[3]))
			multi.set_instance_transform(i,Transform3D(basis,Vector3(p[0],p[1],p[2])))
		var instance := MultiMeshInstance3D.new()
		instance.name = prefix+str(key)
		instance.multimesh = multi
		instance.visibility_range_end = distance
		if prefix == "SpruceFarLOD": instance.visibility_range_begin = 85
		instance.visibility_range_end_margin = 15
		instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(instance)

func _build_detail_scatter() -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/world_data_detail.json"))
	for entry in [["grass","res://assets/library/grass.glb",35.0,70.0],["rocks","res://assets/granite.glb",60.0,150.0]]:
		var source := (load(entry[1]) as PackedScene).instantiate()
		var detail_mesh := _first_mesh(source)
		if detail_mesh: _scatter_cells(_instancing_mesh(detail_mesh),data[entry[0]],float(entry[2]),float(entry[3]),str(entry[0]))
		source.free()

func _build_roadside() -> void:
	# Instanced guideposts, not hundreds of individually processed scene nodes.
	var box := BoxMesh.new()
	box.size = Vector3(0.10,0.82,0.10)
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.79,0.76,0.65)
	box.material = material
	var multi := MultiMesh.new()
	multi.transform_format = MultiMesh.TRANSFORM_3D
	multi.mesh = box
	multi.instance_count = route.size()/2
	for i in range(multi.instance_count):
		var index := i*2
		var forward := (route[(index+1)%route.size()]-route[index]).normalized()
		var side := forward.cross(Vector3.UP).normalized()
		var p := route[index]+side*4.6+Vector3.UP*0.35
		multi.set_instance_transform(i,Transform3D(Basis.IDENTITY,p))
	var instance := MultiMeshInstance3D.new()
	instance.multimesh = multi
	add_child(instance)

func _build_actors() -> void:
	player = AlpinePlayer.new()
	player.name = "Player"
	add_child(player)
	player.fell_into_water.connect(func(): reset_run("Deep water. Back to the overlook."))
	car = AlpineCar.new()
	car.name = "Car"
	add_child(car)
	car.reset_requested.connect(func(): reset_run("Vehicle recovered at the overlook."))
	_contact_shadow(car,Vector2(2.2,4.6))
	_contact_shadow(player,Vector2(0.8,0.65))

func _contact_shadow(parent: Node3D, dimensions: Vector2) -> void:
	var shadow := MeshInstance3D.new()
	var plane := QuadMesh.new()
	plane.size = dimensions
	shadow.mesh = plane
	shadow.rotation.x = -PI/2
	shadow.position.y = 0.025
	shadow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var texture := GradientTexture2D.new()
	texture.width = 64
	texture.height = 64
	texture.fill = GradientTexture2D.FILL_RADIAL
	texture.fill_from = Vector2(0.5,0.5)
	texture.fill_to = Vector2(1,0.5)
	var gradient := Gradient.new()
	gradient.set_color(0,Color(0,0,0,0.42))
	gradient.set_color(1,Color(0,0,0,0))
	texture.gradient = gradient
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.albedo_texture = texture
	shadow.material_override = material
	parent.add_child(shadow)
	shadow.add_to_group("contact_shadows")

func _build_camera() -> void:
	camera_rig = Node3D.new()
	camera_rig.name = "FollowCameraRig"
	add_child(camera_rig)
	spring = SpringArm3D.new()
	spring.spring_length = 7.4
	spring.margin = 0.25
	spring.collision_mask = 1
	spring.add_excluded_object(car.get_rid())
	spring.add_excluded_object(player.get_rid())
	camera_rig.add_child(spring)
	camera = Camera3D.new()
	camera.fov = 66
	camera.near = 0.15
	camera.far = 2200
	camera.current = true
	spring.add_child(camera)
	lake_effects = AlpineLakeEffects.new()
	add_child(lake_effects)
	lake_effects.setup(self,lake_node)

func _build_checkpoints() -> void:
	for index in [24,64,104,148]:
		var ring := MeshInstance3D.new()
		var mesh := TorusMesh.new()
		mesh.inner_radius = 2.85
		mesh.outer_radius = 3.0
		mesh.rings = 24
		mesh.ring_segments = 6
		ring.mesh = mesh
		ring.position = route[index]+Vector3.UP*2.9
		ring.rotation.x = PI/2
		var forward := route[(index+1)%route.size()]-route[index]
		ring.rotation.y = atan2(-forward.x,-forward.z)
		ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.albedo_color = Color(0.42,0.79,0.66)
		ring.material_override = material
		ring.visible = checkpoint_nodes.is_empty()
		add_child(ring)
		checkpoint_nodes.append(ring)

func _reset_positions() -> void:
	var forward := (route[2]-route[0]).normalized()
	car.global_position = route[0]+Vector3.UP*0.12
	car.rotation.y = atan2(-forward.x,-forward.z)
	car.velocity = Vector3.ZERO
	car.speed = 0
	player.global_position = car.global_position+car.global_basis.x*2.5+Vector3.UP*0.05
	player.velocity = Vector3.ZERO
	camera_yaw = car.rotation.y
	camera_rig.global_position = car.global_position+Vector3.UP*1.6
	camera_rig.rotation = Vector3(camera_pitch,camera_yaw,0)

func start_game() -> void:
	_measurement_started_usec = Time.get_ticks_usec()
	frame_ms.clear()
	playing = true
	paused = false
	player.set_active(not in_vehicle)
	car.set_physics_process(true)
	car.set_driven(in_vehicle)
	if wind and not wind.playing: wind.play()
	hud.show_menu(false)
	show_toast("Your car is waiting. Tap ENTER beside it." if touch_controls.enabled else "Your car is waiting. Press E beside it.")

func toggle_pause() -> void:
	if not playing: return
	paused = not paused
	if touch_controls: touch_controls.clear_controls()
	player.set_physics_process(not paused and not in_vehicle)
	car.set_physics_process(not paused)
	if paused:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		if car.motor: car.motor.stop()
	elif in_vehicle and car.motor: car.motor.play()
	hud.show_menu(paused)

func interact() -> bool:
	if not playing or paused: return false
	if in_vehicle:
		if absf(car.speed)>1.5:
			show_toast("Stop the car before stepping out.")
			return false
		# Check both exits against real collision before placing the character.
		for side in [1.0,-1.0]:
			var target: Vector3 = car.global_position+car.global_basis.x*2.1*side+Vector3.UP*0.12
			var query := PhysicsShapeQueryParameters3D.new()
			var shape := CapsuleShape3D.new()
			shape.radius = 0.30
			shape.height = 1.65
			query.shape = shape
			query.transform = Transform3D(Basis.IDENTITY,target+Vector3.UP*0.90)
			query.collision_mask = 1
			query.exclude = [car.get_rid()]
			if get_world_3d().direct_space_state.intersect_shape(query,1).is_empty():
				in_vehicle = false
				car.set_driven(false)
				player.global_position = target
				player.set_active(true)
				mode_changed.emit(false)
				return true
		show_toast("Both doors are blocked. Move the car to open ground.")
		return false
	if player.global_position.distance_to(car.global_position)>4.3:
		show_toast("Walk closer to the car to get in.")
		return false
	in_vehicle = true
	player.set_active(false)
	car.set_driven(true)
	mode_changed.emit(true)
	show_toast("Follow the mint markers. Tap BRAKE to stop." if touch_controls.enabled else "Follow the mint markers around the lake. Space to brake.")
	return true

func reset_run(message: String = "Back at the overlook.") -> void:
	if touch_controls: touch_controls.clear_controls()
	_reset_positions()
	elapsed = 0
	next_checkpoint = 0
	for i in range(checkpoint_nodes.size()): checkpoint_nodes[i].visible = i==0
	show_toast(message)

func show_toast(message: String) -> void:
	toast = message
	toast_time = 4.0

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		toggle_pause()
	elif event.is_action_pressed("interact"):
		interact()
	elif event.is_action_pressed("reset") and playing:
		reset_run()
	elif event.is_action_pressed("quality"):
		enhanced_shadows = not enhanced_shadows
		sun.shadow_enabled = enhanced_shadows
		get_tree().call_group("contact_shadows","set_visible",not enhanced_shadows)
		show_toast("Enhanced shadows" if enhanced_shadows else "Balanced lighting — native 1080p")
	elif event.is_action_pressed("touch"):
		touch_controls.set_enabled(not touch_controls.enabled)
		hud.configure_touch(touch_controls.enabled)
	elif event.is_action_pressed("benchmark"):
		frame_ms.clear()
		_measurement_started_usec = Time.get_ticks_usec()
	elif event.is_action_pressed("mute"):
		AudioServer.set_bus_mute(0,not AudioServer.is_bus_mute(0))
	elif event.is_action_pressed("fullscreen"):
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if DisplayServer.window_get_mode()==DisplayServer.WINDOW_MODE_FULLSCREEN else DisplayServer.WINDOW_MODE_FULLSCREEN)
	elif event is InputEventMouseMotion and playing and not paused and Input.mouse_mode==Input.MOUSE_MODE_CAPTURED:
		camera_yaw -= event.relative.x*0.0025
		camera_pitch = clampf(camera_pitch-event.relative.y*0.002,-0.75,0.18)
		orbit_timeout = 2.0
	elif event is InputEventMouseButton and playing and not paused:
		if event.button_index==MOUSE_BUTTON_LEFT and event.pressed and not touch_controls.enabled:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		elif event.button_index==MOUSE_BUTTON_WHEEL_UP:
			spring.spring_length = maxf(3.2,spring.spring_length-0.7)
		elif event.button_index==MOUSE_BUTTON_WHEEL_DOWN:
			spring.spring_length = minf(14,spring.spring_length+0.7)

func _process(delta: float) -> void:
	# Explicit browser lifecycle bridge: some mobile browsers do not forward a
	# synthetic/window blur through Godot's native focus notification path.
	if _web_input != null and _web_input.focusLost:
		_web_input.focusLost = false
		if touch_controls: touch_controls.clear_controls()
		if playing and not paused: toggle_pause()
	elapsed_real += delta
	var now := Time.get_ticks_usec()
	if playing and not paused and _last_frame_usec>0 and now-_measurement_started_usec>2000000:
		# Real wall-clock frame intervals, not physics ticks or clamped delta.
		frame_ms.append((now-_last_frame_usec)/1000.0)
		if frame_ms.size()>600: frame_ms.pop_front()
	_last_frame_usec = now
	toast_time = maxf(0,toast_time-delta)
	orbit_timeout = maxf(0,orbit_timeout-delta)
	var target := car.global_position+Vector3.UP*1.25 if in_vehicle or not playing else player.global_position+Vector3.UP*1.35
	if in_vehicle and orbit_timeout<=0 and absf(car.speed)>1.0:
		camera_yaw = lerp_angle(camera_yaw,car.rotation.y,1-exp(-2.2*delta))
	var back := PI if Input.is_action_pressed("look_back") else 0.0
	camera_rig.global_position = camera_rig.global_position.lerp(target,1-exp(-8.0*delta))
	camera_rig.rotation = Vector3(camera_pitch,camera_yaw+back,0)
	player.camera_yaw = camera_yaw
	if playing and not paused and in_vehicle:
		elapsed += delta
		var ring := checkpoint_nodes[next_checkpoint]
		if car.global_position.distance_to(ring.global_position-Vector3.UP*2.9)<7:
			ring.visible = false
			next_checkpoint += 1
			checkpoint_reached.emit(next_checkpoint)
			if next_checkpoint>=checkpoint_nodes.size():
				laps += 1
				if best_lap<=0 or elapsed<best_lap:
					best_lap = elapsed
					_save_best()
				show_toast("Lake loop complete — %.1f s. Another lap?" % elapsed)
				elapsed = 0
				next_checkpoint = 0
			checkpoint_nodes[next_checkpoint].visible = true
	if now-_last_telemetry_usec>500000:
		_last_telemetry_usec = now
		if OS.has_feature("web"):
			JavaScriptBridge.eval("window.alpineTelemetry = " + JSON.stringify(telemetry()) + ";")

func telemetry() -> Dictionary:
	var samples := frame_ms.duplicate()
	samples.sort()
	var p95: float = samples[int((samples.size()-1)*.95)] if not samples.is_empty() else 0.0
	return {"engine":"Godot 4.4.1","frame":Engine.get_process_frames(),"fps":Engine.get_frames_per_second(),"p95_frame_ms":snappedf(p95,.01),
		"render_size":[int(get_viewport().get_visible_rect().size.x),int(get_viewport().get_visible_rect().size.y)],
		"render_scale":get_viewport().scaling_3d_scale,"frame_samples":samples.size(),
		"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"player":[player.position.x,player.position.y,player.position.z],
		"car":[car.position.x,car.position.y,car.position.z],"speed_mps":car.speed,
		"driving":in_vehicle,"playing":playing,"paused":paused,"laps":laps,
		"last_touch":[touch_controls.last_position.x,touch_controls.last_position.y] if touch_controls else [],
		"touch_enabled":touch_controls.enabled if touch_controls else false,
		"touch_fingers":touch_controls.owners.size() if touch_controls else 0,
		"touch_actions":touch_controls.held if touch_controls else {},
		"camera_yaw":camera_yaw,"camera_pitch":camera_pitch,
		"live_reflection_frames":lake_effects.mirror_frames if lake_effects else 0,
		"water_reflection":"shared-world planar camera 512x288",
		"sun_shafts":"depth-occluded 32-tap screen-space scattering",
		"renderer":"gl_compatibility","enhanced_shadows":enhanced_shadows,"fps_target":60,"native_resolution_target":[1920,1080]}

func _read_best() -> void:
	var config := ConfigFile.new()
	if config.load("user://alpine.cfg")==OK:
		best_lap = float(config.get_value("record","best_seconds",0.0))

func _save_best() -> void:
	var config := ConfigFile.new()
	config.set_value("record","best_seconds",best_lap)
	config.save("user://alpine.cfg")
