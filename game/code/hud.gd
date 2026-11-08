class_name AlpineHUD
extends CanvasLayer

var game
var root: Control
var menu: Control
var overlay: Control
var primary: Button
var speed: Label
var unit: Label
var mode: Label
var prompt: Label
var notice: Label
var objective: Label
var stats: Label
var timer: Label
var minimap: Control
var _clock: float = 0.0
const INK := Color(0.055,0.075,0.072)
const IVORY := Color(0.94,0.94,0.87)
const MINT := Color(0.64,0.85,0.72)

func _ready() -> void:
	root = Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)
	overlay = Control.new()
	overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(overlay)
	for bottom in [false,true]:
		var fade := TextureRect.new()
		var texture := GradientTexture2D.new()
		var gradient := Gradient.new()
		gradient.set_color(0,Color(0.02,0.05,0.06,0.65))
		gradient.set_color(1,Color(0.02,0.05,0.06,0))
		texture.gradient = gradient
		texture.fill_from = Vector2(0,1) if bottom else Vector2(0,0)
		texture.fill_to = Vector2(0,0) if bottom else Vector2(0,1)
		fade.texture = texture
		fade.size = Vector2(1920,240)
		fade.position.y = 840 if bottom else 0
		fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
		overlay.add_child(fade)
	_label(overlay,"A / M",Vector2(58,46),32,IVORY)
	_label(overlay,"ALPINE MIRROR",Vector2(58,89),14,MINT)
	_label(overlay,"L A K E S I D E   E S C A P E",Vector2(58,112),12,IVORY)
	objective = _label(overlay,"LAKESIDE LOOP",Vector2(680,50),19,IVORY,560)
	objective.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	timer = _label(overlay,"",Vector2(680,80),15,MINT,560)
	timer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	stats = _label(overlay,"",Vector2(1480,48),14,IVORY,382)
	stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	mode = _label(overlay,"ON FOOT",Vector2(1680,829),15,MINT,180)
	mode.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	speed = _label(overlay,"",Vector2(1620,842),94,IVORY,240)
	speed.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	unit = _label(overlay,"",Vector2(1650,950),14,MINT,210)
	unit.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	prompt = _label(overlay,"",Vector2(460,902),23,IVORY,1000)
	prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notice = _label(overlay,"",Vector2(460,850),20,MINT,1000)
	notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label(overlay,"WASD  MOVE / DRIVE     SHIFT  RUN     SPACE  JUMP / BRAKE     E  ENTER / EXIT     R  RECOVER     ESC  PAUSE",Vector2(380,1027),14,IVORY,1180).horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label(overlay,"CLICK TO LOOK  ·  MOUSE TO ORBIT  ·  Q REAR VIEW  ·  M MUTE",Vector2(380,1001),12,Color(0.8,0.85,0.8),1180).horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	minimap = preload("res://code/minimap.gd").new()
	minimap.game = game
	minimap.position = Vector2(46,804)
	minimap.size = Vector2(220,220)
	minimap.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay.add_child(minimap)
	menu = Control.new()
	menu.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(menu)
	var fade := TextureRect.new()
	var texture := GradientTexture2D.new()
	var gradient := Gradient.new()
	gradient.set_color(0,Color(0.025,0.048,0.052,0.96))
	gradient.set_color(1,Color(0.025,0.048,0.052,0.0))
	texture.gradient = gradient
	texture.width = 1024
	texture.fill_from = Vector2(0.0,0)
	texture.fill_to = Vector2(1,0)
	fade.texture = texture
	fade.size = Vector2(1520,1080)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	menu.add_child(fade)
	_label(menu,"A / M     —     AN ALPINE ESCAPE",Vector2(100,83),20,MINT)
	_label(menu,"ALPINE\nMIRROR",Vector2(92,220),110,IVORY,760)
	_label(menu,"An open road.\nA quieter kind of escape.",Vector2(101,503),31,IVORY,760)
	_label(menu,"Explore the lake on foot, take the wheel,\nand follow the mountain road.",Vector2(103,624),23,Color(0.74,0.81,0.77),720)
	primary = Button.new()
	primary.position = Vector2(103,754)
	primary.size = Vector2(430,76)
	primary.text = "Begin escape     >"
	primary.add_theme_font_size_override("font_size",25)
	primary.add_theme_color_override("font_color",INK)
	primary.add_theme_color_override("font_hover_color",INK)
	primary.add_theme_stylebox_override("normal",_style(MINT))
	primary.add_theme_stylebox_override("hover",_style(Color(0.78,0.94,0.82)))
	primary.add_theme_stylebox_override("pressed",_style(Color(0.50,0.73,0.60)))
	primary.pressed.connect(func():
		primary.release_focus()
		if game.playing: game.toggle_pause()
		else: game.start_game())
	menu.add_child(primary)
	_label(menu,"NATIVE 1920 × 1080     /     60 FPS TARGET",Vector2(104,861),14,MINT)
	_label(menu,"WASD move  ·  E enter car  ·  F fullscreen  ·  M mute",Vector2(104,899),17,IVORY)
	_label(menu,"01   /   THE LAKESIDE LOOP",Vector2(104,1006),14,Color(0.64,0.73,0.71))
	_label(menu,"BLENDER / GODOT\nPLAYABLE VERTICAL SLICE",Vector2(1490,975),14,IVORY,330).horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	overlay.visible = false

func _label(parent: Control,text: String,at: Vector2,font_size: int,color: Color,width: float=850) -> Label:
	var label := Label.new()
	label.text = text
	label.position = at
	label.size.x = width
	label.add_theme_font_size_override("font_size",font_size)
	label.add_theme_color_override("font_color",color)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(label)
	return label

func _style(color: Color) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.corner_radius_top_left = 5
	style.corner_radius_top_right = 5
	style.corner_radius_bottom_left = 5
	style.corner_radius_bottom_right = 5
	return style

func show_menu(value: bool) -> void:
	menu.visible = value
	overlay.visible = not value
	primary.text = "Resume escape     >" if game.playing else "Begin escape     >"

func _process(delta: float) -> void:
	_clock += delta
	if _clock<0.15: return
	_clock = 0
	if not game.playing or game.paused: return
	var driving: bool = game.in_vehicle
	mode.text = "BEHIND THE WHEEL" if driving else "ON FOOT"
	speed.text = "%02d" % roundi(absf(game.car.speed)*3.6) if driving else ""
	unit.text = "KM / H" if driving else "EXPLORE AT YOUR OWN PACE"
	var distance: float = game.player.global_position.distance_to(game.car.global_position)
	prompt.text = "[ E ]   Step out" if driving and absf(game.car.speed)<1.5 else ("[ E ]   Take the wheel" if not driving and distance<4.3 else "")
	notice.text = game.toast if game.toast_time>0 else ""
	objective.text = "LAKESIDE LOOP    %d / 4" % game.next_checkpoint
	var ring_position: Vector3 = game.checkpoint_nodes[game.next_checkpoint].global_position
	var location: Vector3 = game.car.global_position if driving else game.player.global_position
	var meters := int(location.distance_to(ring_position))
	timer.text = "%d m TO NEXT MARKER    ·    %02d:%02d" % [meters,int(game.elapsed)/60,int(game.elapsed)%60]
	var info: Dictionary = game.telemetry()
	stats.text = "%d FPS   ·   1920 × 1080" % info["fps"]
	minimap.queue_redraw()
