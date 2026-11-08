class_name AlpinePlayer
extends CharacterBody3D

signal fell_into_water

var active: bool = true
var camera_yaw: float = 0.0
var gait: float = 0.0
var animator: AnimationPlayer
var model: Node3D
var _walk_clip: StringName = &""
var _idle_clip: StringName = &""

func _ready() -> void:
	collision_layer = 2
	collision_mask = 1
	floor_max_angle = deg_to_rad(48.0)
	floor_snap_length = 0.4
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.27
	capsule.height = 1.78
	shape.shape = capsule
	shape.position.y = 0.90
	add_child(shape)
	model = preload("res://assets/hiker.glb").instantiate()
	add_child(model)
	animator = _find_animator(model)
	if animator:
		for clip in animator.get_animation_list():
			var lower := String(clip).to_lower()
			if "walk" in lower:
				_walk_clip = clip
			elif "idle" in lower:
				_idle_clip = clip
			animator.get_animation(clip).loop_mode = Animation.LOOP_LINEAR

func _find_animator(root: Node) -> AnimationPlayer:
	if root is AnimationPlayer:
		return root
	for child in root.get_children():
		var result := _find_animator(child)
		if result:
			return result
	return null

func set_active(value: bool) -> void:
	active = value
	visible = value
	set_physics_process(value)
	collision_layer = 2 if value else 0
	collision_mask = 1 if value else 0
	velocity = Vector3.ZERO

func _physics_process(delta: float) -> void:
	if not active:
		return
	var axis := Input.get_vector("left", "right", "forward", "back")
	var direction := (Basis(Vector3.UP, camera_yaw) * Vector3(axis.x, 0, axis.y)).normalized()
	var speed := 7.3 if Input.is_action_pressed("sprint") else 3.8
	var acceleration := 22.0 if is_on_floor() else 6.0
	velocity.x = move_toward(velocity.x, direction.x * speed, acceleration * delta)
	velocity.z = move_toward(velocity.z, direction.z * speed, acceleration * delta)
	if not is_on_floor():
		velocity.y -= 18.0 * delta
	elif Input.is_action_just_pressed("jump"):
		velocity.y = 6.3
	else:
		velocity.y = -0.2
	move_and_slide()
	if direction.length_squared() > 0.01:
		model.rotation.y = lerp_angle(model.rotation.y, atan2(-direction.x, -direction.z), 1.0 - exp(-12 * delta))
	var horizontal := Vector2(velocity.x, velocity.z).length()
	gait = horizontal
	if animator:
		var clip := _walk_clip if horizontal > 0.3 else _idle_clip
		if clip != &"" and animator.current_animation != clip:
			animator.play(clip, 0.18)
		animator.speed_scale = clampf(horizontal / 3.8, 0.7, 1.7) if horizontal > 0.3 else 1.0
	if global_position.y < -0.7 or global_position.y > 400:
		fell_into_water.emit()
