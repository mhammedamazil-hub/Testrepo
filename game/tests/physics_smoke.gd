extends SceneTree

var checks: Array[Dictionary] = []
var failed: bool = false
var game

func _initialize() -> void:
	call_deferred("_run")

func check(label: String, value: bool) -> void:
	checks.append({"check":label,"passed":value})
	if not value:
		failed = true
		push_error("GAME TEST FAILED: " + label)

func ticks(count: int) -> void:
	for unused in range(count):
		await physics_frame

func touch(index: int, at: Vector2, pressed: bool) -> void:
	var event := InputEventScreenTouch.new()
	event.index = index
	event.position = at
	event.pressed = pressed
	root.push_input(event, true)
	Input.flush_buffered_events()

func drag(index: int, at: Vector2, relative: Vector2) -> void:
	var event := InputEventScreenDrag.new()
	event.index = index
	event.position = at
	event.relative = relative
	root.push_input(event, true)
	Input.flush_buffered_events()

func _run() -> void:
	game = load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	current_scene = game
	await process_frame
	check("Native project viewport is 1920x1080",game.get_viewport().get_visible_rect().size==Vector2(1920,1080))
	check("Original terrain and road imported",game.route.size()==160)
	check("Real skeletal animation imported",game.player.animator!=null and game.player._walk_clip!=&"" and game.player._idle_clip!=&"")
	game.start_game()
	await ticks(30)
	check("Player stands on physical terrain",game.player.is_on_floor() and game.player.global_position.y>0)
	check("Vehicle stands on physical terrain",game.car.is_on_floor() and game.car.global_position.y>0)
	var start: Vector3 = game.player.global_position
	Input.action_press("forward")
	await ticks(45)
	Input.action_release("forward")
	check("Walking changes actual character position",game.player.global_position.distance_to(start)>1)
	game.reset_run()
	await ticks(15)
	check("Enter car near vehicle",game.interact() and game.in_vehicle and not game.player.active)
	var before: Vector3 = game.car.global_position
	Input.action_press("forward")
	await ticks(90)
	Input.action_release("forward")
	check("Driving moves collision body",game.car.global_position.distance_to(before)>3)
	check("Cannot exit a moving car",not game.interact() and game.in_vehicle)
	Input.action_press("jump")
	await ticks(60)
	Input.action_release("jump")
	check("Brake stops the vehicle",absf(game.car.speed)<0.1)
	check("Exit stationary vehicle",game.interact() and not game.in_vehicle and game.player.active)
	await ticks(10)
	var remembered: Vector3 = game.player.global_position
	game.toggle_pause()
	Input.action_press("forward")
	await ticks(15)
	Input.action_release("forward")
	check("Pause freezes player physics",game.player.global_position.distance_to(remembered)<0.05)
	game.toggle_pause()
	game.reset_run()
	await ticks(15)
	game.interact()
	for index in [24,64,104,148]:
		game.car.speed = 0
		game.car.velocity = Vector3.ZERO
		game.car.global_position = game.route[index]+Vector3.UP*0.1
		await process_frame
		await process_frame
	check("Checkpoint loop completes a lap",game.laps==1)
	game.reset_run()
	check("Recovery resets route progress",game.next_checkpoint==0 and game.car.speed==0)
	# Actual Godot viewport-local screen-touch events (dummy OS window is 64px).
	if game.in_vehicle: game.interact()
	game.reset_run()
	game.touch_controls.set_enabled(true)
	game.hud.configure_touch(true)
	await ticks(15)
	var touch_start: Vector3 = game.player.global_position
	touch(0,Vector2(235,840),true)
	drag(0,Vector2(235,680),Vector2(0,-160))
	var yaw_before: float = game.camera_yaw
	touch(1,Vector2(1100,450),true)
	drag(1,Vector2(1200,450),Vector2(100,0))
	check("Touch joystick and camera own independent fingers",game.touch_controls.owners.size()==2)
	check("Touch drag orbits the real camera",absf(game.camera_yaw-yaw_before)>0.1)
	await ticks(35)
	touch(0,Vector2(235,680),false)
	touch(1,Vector2(1200,450),false)
	check("Touch joystick moves physical player",game.player.global_position.distance_to(touch_start)>1)
	check("Touch release clears held movement",not Input.is_action_pressed("forward") and game.touch_controls.owners.is_empty())
	game.reset_run()
	await ticks(15)
	touch(2,Vector2(1535,710),true)
	touch(2,Vector2(1535,710),false)
	check("Touch ENTER takes the wheel",game.in_vehicle)
	var touch_car_start: Vector3 = game.car.global_position
	touch(3,Vector2(1760,740),true)
	await ticks(75)
	touch(3,Vector2(1760,740),false)
	check("Touch GAS drives physical car",game.car.global_position.distance_to(touch_car_start)>3)
	touch(4,Vector2(1740,945),true)
	await ticks(60)
	touch(4,Vector2(1740,945),false)
	check("Touch BRAKE stops car",absf(game.car.speed)<0.1)
	touch(2,Vector2(1535,710),true)
	touch(2,Vector2(1535,710),false)
	check("Touch EXIT returns to walking",not game.in_vehicle and game.player.active)
	touch(0,Vector2(235,680),true)
	touch(5,Vector2(1760,200),true)
	check("Touch PAUSE clears all active controls",game.paused and game.touch_controls.owners.is_empty() and not Input.is_action_pressed("forward"))
	game.toggle_pause()
	touch(0,Vector2(235,680),true)
	game.touch_controls.notification(Node.NOTIFICATION_APPLICATION_FOCUS_OUT)
	check("Focus loss releases touch movement",game.touch_controls.owners.is_empty() and not Input.is_action_pressed("forward"))
	touch(6,Vector2(1510,200),true)
	touch(6,Vector2(1510,200),false)
	check("Touch RECOVER resets progress",game.next_checkpoint==0 and game.car.speed==0)
	check("Roadside 3D detail is actually instantiated",game.find_children("RoadsideSpruce*","MultiMeshInstance3D",false,false).size()>0 and game.find_children("grass*","MultiMeshInstance3D",false,false).size()>0)
	var result := {"status":"HEADLESS_GAMEPLAY_PASS" if not failed else "HEADLESS_GAMEPLAY_FAIL",
		"engine":Engine.get_version_info().string,"checks":checks,
		"rendered":false,"fps_benchmarked":false,
		"scope":"Actual Godot physics/input/state/import tests. Headless frame rate is NOT rendering performance."}
	var destination := "res://../docs/game/headless-validation.json"
	var file := FileAccess.open(destination,FileAccess.WRITE)
	if file:
		file.store_string(JSON.stringify(result,"  ")+"\n")
	print(JSON.stringify(result,"  "))
	print("GAMEPLAY_SMOKE_PASS" if not failed else "GAMEPLAY_SMOKE_FAIL")
	current_scene = null
	game.queue_free()
	game = null
	await process_frame
	await process_frame
	quit(1 if failed else 0)
