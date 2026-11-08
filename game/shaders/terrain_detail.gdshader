shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

uniform sampler2D base_map : source_color, filter_linear_mipmap_anisotropic;
uniform sampler2D base_normal : hint_normal, filter_linear_mipmap_anisotropic;
uniform sampler2D detail_map : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D detail_normal : hint_normal, repeat_enable, filter_linear_mipmap_anisotropic;
uniform bool mountain = false;
varying vec3 world_position;

void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 base = texture(base_map, UV).rgb;
	vec2 metres = world_position.xz * 0.20;
	vec3 detail = texture(detail_map, metres).rgb;
	float near_detail = 1.0 - smoothstep(30.0, 210.0, distance(CAMERA_POSITION_WORLD, world_position));
	float grain = dot(detail, vec3(0.3333));
	vec3 earth = base * mix(0.68, 1.26, grain * 1.65);
	// Keep baked snow/rock identity; only the valley receives a muted turf tint.
	if (!mountain) earth = mix(earth, detail * vec3(0.85, 0.94, 0.76), 0.72);
	ALBEDO = mix(base, earth, near_detail * 0.85);
	vec3 coarse = texture(base_normal, UV).xyz * 2.0 - 1.0;
	vec3 fine = texture(detail_normal, metres).xyz * 2.0 - 1.0;
	NORMAL_MAP = normalize(vec3(coarse.xy + fine.xy * near_detail * 0.45, max(coarse.z, 0.3))) * 0.5 + 0.5;
	ROUGHNESS = 0.94;
	SPECULAR = 0.25;
}
