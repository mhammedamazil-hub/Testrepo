extends Control
var game

func _draw() -> void:
	var center := Vector2(110,110)
	draw_circle(center,103,Color(0.03,0.065,0.075,0.82))
	draw_arc(center,103,0,TAU,64,Color(0.77,0.89,0.80,0.4),1.0,true)
	var lake := PackedVector2Array()
	for i in range(64):
		var a := TAU*i/64.0
		lake.append(center+Vector2(cos(a)*25,sin(a)*69))
	draw_colored_polygon(lake,Color(0.10,0.28,0.32))
	var line := PackedVector2Array()
	for p in game.route:
		line.append(_project(p))
	line.append(line[0])
	draw_polyline(line,Color(0.70,0.76,0.66),2,true)
	var checkpoint: Vector3 = game.checkpoint_nodes[game.next_checkpoint].global_position
	draw_circle(_project(checkpoint),4,Color(0.59,0.87,0.72))
	var body: Node3D = game.car if game.in_vehicle else game.player
	var at := _project(body.global_position)
	var triangle := PackedVector2Array()
	for v in [Vector2(0,-7),Vector2(4,5),Vector2(-4,5)]:
		triangle.append(at+v.rotated(-body.rotation.y))
	draw_colored_polygon(triangle,Color(0.96,0.95,0.83))
	draw_string(ThemeDB.fallback_font,Vector2(104,19),"N",HORIZONTAL_ALIGNMENT_LEFT,-1,13,Color(0.85,0.91,0.83))

func _project(p: Vector3) -> Vector2:
	return Vector2(110,110)+Vector2(p.x,p.z+143)*0.40
