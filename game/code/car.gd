class_name AlpineCar
extends CharacterBody3D

signal reset_requested

var driven: bool = false
var speed: float = 0.0
var steering: float = 0.0
var wheel_spin: float = 0.0
var model: Node3D
var front_wheels: Array[Node3D] = []
var rear_wheels: Array[Node3D] = []
var motor: AudioStreamPlayer3D

func _ready() -> void:
	collision_layer = 3
	collision_mask = 1
	floor_snap_length = 0.6
	floor_max_angle = deg_to_rad(48)
	var collider := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(1.82, 1.4, 4.2)
	collider.position.y = 0.70
	collider.shape = box
	add_child(collider)
	model = preload("res://assets/touring_car.glb").instantiate()
	add_child(model)
	for label in ["FL", "FR", "RL", "RR"]:
		var wheel := model.find_child("Wheel_" + label, true, false) as Node3D
		if wheel:
			if String(label).begins_with("F"):
				front_wheels.append(wheel)
			else:
				rear_wheels.append(wheel)
	# Headless physics/import tests have no audio device; do not create playback.
	if DisplayServer.get_name()!="headless" and ResourceLoader.exists("res://assets/motor.wav"):
		motor = AudioStreamPlayer3D.new()
		var audio := load("res://assets/motor.wav") as AudioStreamWAV
		audio.loop_mode = AudioStreamWAV.LOOP_FORWARD
		audio.loop_end = audio.data.size() / 2
		motor.stream = audio
		motor.volume_db = -22
		motor.max_distance = 45
		add_child(motor)

func set_driven(value: bool) -> void:
	driven = value
	if motor:
		if value:
			motor.play()
		else:
			motor.stop()

func _physics_process(delta: float) -> void:
	var throttle := Input.get_axis("back", "forward") if driven else 0.0
	var steer_input := Input.get_axis("left", "right") if driven else 0.0
	var brake := driven and Input.is_action_pressed("jump")
	var steering_limit := lerpf(0.48,0.16,clampf(absf(speed)/24.0,0,1))
	steering = move_toward(steering, steer_input * steering_limit, delta * 1.7)
	var target := throttle * (30.0 if throttle >= 0 else 9.0)
	var acceleration := 7.5 if absf(throttle) > 0.05 else 2.4
	if brake:
		target = 0.0
		acceleration = 20.0
	speed = move_toward(speed, target, acceleration * delta)
	if is_on_floor():
		rotation.y -= speed / 2.65 * tan(steering) * delta
	var forward := -global_transform.basis.z
	velocity.x = forward.x * speed
	velocity.z = forward.z * speed
	if not is_on_floor():
		velocity.y -= 18.0 * delta
	else:
		velocity.y = -0.8
	var before := global_position
	move_and_slide()
	var horizontal := Vector2(global_position.x-before.x, global_position.z-before.z).length()
	if delta > 0 and absf(speed) > 1.5 and horizontal < absf(speed) * delta * 0.25:
		speed *= 0.5
	wheel_spin -= speed / 0.38 * delta
	for wheel in front_wheels:
		wheel.rotation.y = steering
		wheel.rotation.x = wheel_spin
	for wheel in rear_wheels:
		wheel.rotation.x = wheel_spin
	model.rotation.z = lerpf(model.rotation.z, -steering * speed * 0.006, 1-exp(-5*delta))
	if motor:
		motor.pitch_scale = 0.7 + absf(speed) / 20.0
	if global_position.y < -0.8 or global_position.length() > 2000:
		reset_requested.emit()
