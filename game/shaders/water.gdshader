shader_type spatial;
render_mode unshaded, cull_back;

// Static panorama captured from the ACTUAL game terrain at lake centre.
// Cheap enough for Web/mobile, but not a real-time planar/SSR reflection.
uniform sampler2D reflection_map : source_color, filter_linear_mipmap;
uniform sampler2D ripple_map : hint_normal, repeat_enable, filter_linear_mipmap;
uniform vec3 sun_direction = vec3(-0.35, 0.68, 0.64);
varying vec3 world_position;

void vertex() {
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	VERTEX.y += sin(world.x * 0.19 + world.z * 0.12 + TIME * 0.9) * 0.028;
	VERTEX.y += sin(world.x * -0.28 + world.z * 0.21 + TIME * 1.13) * 0.018;
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = world_position.xz * 0.08;
	vec3 a = texture(ripple_map, uv + vec2(TIME * 0.013, TIME * 0.005)).xyz * 2.0 - 1.0;
	vec3 b = texture(ripple_map, uv * 1.73 + vec2(-TIME * 0.008, TIME * 0.011)).xyz * 2.0 - 1.0;
	vec3 normal_world = normalize(vec3((a.x + b.x) * 0.11, 1.0, (a.y + b.y) * 0.11));
	vec3 view_world = normalize(CAMERA_POSITION_WORLD - world_position);
	vec3 reflected = reflect(-view_world, normal_world);
	vec2 panorama_uv = vec2(atan(reflected.x, -reflected.z) / 6.2831853 + 0.5, acos(clamp(reflected.y, -1.0, 1.0)) / 3.14159265);
	vec3 reflection = texture(reflection_map, panorama_uv).rgb;
	float fresnel = 0.025 + 0.975 * pow(1.0 - max(dot(normal_world, view_world), 0.0), 5.0);
	vec3 absorption = vec3(0.014, 0.065, 0.068);
	float sun_glint = pow(max(dot(reflected, normalize(sun_direction)), 0.0), 320.0);
	ALBEDO = mix(absorption, reflection * 0.86, clamp(fresnel * 1.22, 0.08, 0.96)) + vec3(1.0, 0.93, 0.76) * sun_glint * 0.50;
}
