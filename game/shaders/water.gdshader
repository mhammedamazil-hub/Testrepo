shader_type spatial;
render_mode unshaded, cull_back;

// Actual shared-world planar mirror camera, rendered every frame at 512x288.
// The panorama is only a bounded out-of-frustum fallback, not the main mirror.
uniform sampler2D reflection_map : source_color, filter_linear_mipmap;
uniform sampler2D live_reflection : source_color, filter_linear;
uniform mat4 reflection_view_projection;
uniform sampler2D ripple_map : hint_normal, repeat_enable, filter_linear_mipmap;
uniform vec3 sun_direction = vec3(-0.35,0.68,0.64);
varying vec3 world_position;
varying vec4 mirror_clip;
void vertex() {
	vec3 world = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
	VERTEX.y += sin(world.x*.19+world.z*.12+TIME*.9)*.028;
	VERTEX.y += sin(world.x*-.28+world.z*.21+TIME*1.13)*.018;
	world_position = (MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
	mirror_clip = reflection_view_projection*vec4(world_position,1.0);
}
void fragment() {
	vec2 uv = world_position.xz*.08;
	vec3 a = texture(ripple_map,uv+vec2(TIME*.013,TIME*.005)).xyz*2.0-1.0;
	vec3 b = texture(ripple_map,uv*1.73+vec2(-TIME*.008,TIME*.011)).xyz*2.0-1.0;
	vec3 normal_world = normalize(vec3((a.x+b.x)*.075,1.0,(a.y+b.y)*.075));
	vec3 view_world = normalize(CAMERA_POSITION_WORLD-world_position);
	vec3 reflected = reflect(-view_world,normal_world);
	vec2 panorama_uv = vec2(atan(reflected.x,-reflected.z)/6.2831853+.5,acos(clamp(reflected.y,-1.0,1.0))/3.14159265);
	vec2 mirror_uv = mirror_clip.xy/mirror_clip.w*.5+.5;
	mirror_uv.y = 1.0-mirror_uv.y;
	mirror_uv += normal_world.xz*.008;
	vec3 fallback = texture(reflection_map,panorama_uv).rgb;
	float inside = step(.005,mirror_uv.x)*step(mirror_uv.x,.995)*step(.005,mirror_uv.y)*step(mirror_uv.y,.995)*step(0.0,mirror_clip.w);
	vec3 reflection = mix(fallback,texture(live_reflection,clamp(mirror_uv,vec2(.005),vec2(.995))).rgb,inside);
	float fresnel = .025+.975*pow(1.0-max(dot(normal_world,view_world),0.0),5.0);
	float sun_glint = pow(max(dot(reflected,normalize(sun_direction)),0.0),320.0);
	ALBEDO = mix(vec3(.014,.065,.068),reflection*.93,clamp(fresnel*1.22,.08,.97))+vec3(1.0,.93,.76)*sun_glint*.5;
}
