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
