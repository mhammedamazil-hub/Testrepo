class_name AlpineTouchControls
extends Control
## Real multi-touch input in Godot viewport coordinates; no DOM key emulation.

var game
var enabled: bool = false
var stick: Vector2 = Vector2.ZERO
var owners: Dictionary = {}
var held: Dictionary = {}
var last_action: String = ""
var last_position := Vector2.ZERO
const STICK_CENTER := Vector2(235, 840)
const STICK_RADIUS := 160.0
const BUTTON_RADIUS := 82.0
const BUTTONS := {
	"interact": Vector2(1535, 710),
	"forward": Vector2(1760, 740),
	"jump": Vector2(1740, 945),
	"back": Vector2(1515, 945),
	"sprint": Vector2(485, 945),
	"reset": Vector2(1510, 200),
	"pause": Vector2(1760, 200),
}

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	set_enabled(DisplayServer.is_touchscreen_available() or OS.has_feature("mobile"))
	if OS.has_feature("web"):
		set_enabled(enabled or bool(JavaScriptBridge.eval("navigator.maxTouchPoints > 0 || matchMedia('(pointer: coarse)').matches")))

func set_enabled(value: bool) -> void:
	enabled = value
	if not value: clear_controls()
	queue_redraw()

func clear_controls() -> void:
	for action in held: Input.action_release(action)
	held.clear()
	owners.clear()
	stick = Vector2.ZERO
	queue_redraw()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		clear_controls()

func _exit_tree() -> void:
	clear_controls()

func _apply_actions() -> void:
	var desired: Dictionary = {}
	if stick.length() > 0.12:
		desired["left"] = maxf(0, -stick.x)
		desired["right"] = maxf(0, stick.x)
		if not game.in_vehicle:
			desired["forward"] = maxf(0, -stick.y)
			desired["back"] = maxf(0, stick.y)
	for role in owners.values():
		if role in ["forward", "back", "jump", "sprint"]:
			desired[role] = 1.0
	for action in held:
		if float(desired.get(action, 0)) <= 0: Input.action_release(action)
	held.clear()
	for action in desired:
		if float(desired[action]) > 0:
			Input.action_press(action, float(desired[action]))
			held[action] = desired[action]
	queue_redraw()

func _button_at(point: Vector2) -> String:
	for action in BUTTONS:
		if action in ["forward", "back"] and not game.in_vehicle: continue
		if action == "sprint" and game.in_vehicle: continue
		if point.distance_to(BUTTONS[action]) <= BUTTON_RADIUS:
			return action
	return ""

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch or event is InputEventScreenDrag:
		last_position = event.position
	if not enabled or not game.playing or game.paused: return
	if event is InputEventScreenTouch:
		if event.pressed:
			var action := _button_at(event.position)
			if not action.is_empty():
				last_action = action
				if action == "pause":
					clear_controls()
					game.toggle_pause()
				elif action == "reset":
					clear_controls()
					game.reset_run()
				elif action == "interact":
					game.interact()
					clear_controls()
				else:
					owners[event.index] = action
			elif event.position.distance_to(STICK_CENTER) <= STICK_RADIUS * 1.3 and not owners.values().has("stick"):
				owners[event.index] = "stick"
				stick = ((event.position - STICK_CENTER) / STICK_RADIUS).limit_length()
			elif event.position.x > 600 and not owners.values().has("look"):
				owners[event.index] = "look"
		else:
			if owners.get(event.index, "") == "stick": stick = Vector2.ZERO
			owners.erase(event.index)
		_apply_actions()
		get_viewport().set_input_as_handled()
	elif event is InputEventScreenDrag and owners.has(event.index):
		if owners[event.index] == "stick":
			stick = ((event.position - STICK_CENTER) / STICK_RADIUS).limit_length()
		elif owners[event.index] == "look":
			game.camera_yaw -= event.relative.x * 0.003
			game.camera_pitch = clampf(game.camera_pitch - event.relative.y * 0.0025, -0.75, 0.18)
			game.orbit_timeout = 2.0
		_apply_actions()
		get_viewport().set_input_as_handled()

func _process(_delta: float) -> void:
	if enabled and game.playing and not game.paused: queue_redraw()

func _draw() -> void:
	if not enabled or not game.playing or game.paused: return
	var font := ThemeDB.fallback_font
	var ink := Color(0.035, 0.07, 0.075, 0.74)
	var light := Color(0.86, 0.95, 0.9, 0.90)
	draw_circle(STICK_CENTER, STICK_RADIUS, ink)
	draw_arc(STICK_CENTER, STICK_RADIUS, 0, TAU, 48, Color(0.7, 0.85, 0.8, 0.55), 3, true)
	draw_circle(STICK_CENTER + stick * 105, 56, Color(0.72, 0.88, 0.8, 0.72))
	draw_string(font, STICK_CENTER + Vector2(-78, -183), "STEER" if game.in_vehicle else "MOVE", HORIZONTAL_ALIGNMENT_CENTER, 156, 30, light)
	for action in BUTTONS:
		if action in ["forward", "back"] and not game.in_vehicle: continue
		if action == "sprint" and game.in_vehicle: continue
		var point: Vector2 = BUTTONS[action]
		var color := Color(0.30, 0.52, 0.44, 0.92) if owners.values().has(action) else ink
		draw_circle(point, BUTTON_RADIUS, color)
		draw_arc(point, BUTTON_RADIUS, 0, TAU, 40, Color(0.7, 0.85, 0.8, 0.55), 2, true)
		var labels := {"interact": "EXIT" if game.in_vehicle else "ENTER", "forward": "GAS", "back": "REVERSE", "jump": "BRAKE" if game.in_vehicle else "JUMP", "sprint": "RUN", "reset": "RECOVER", "pause": "PAUSE"}
		draw_string(font, point + Vector2(-80, 11), labels[action], HORIZONTAL_ALIGNMENT_CENTER, 160, 28, light)
