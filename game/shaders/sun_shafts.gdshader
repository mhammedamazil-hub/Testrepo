shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, depth_test_disabled, cull_disabled, fog_disabled;

// Original, bounded 32-tap radial scattering. Sky-depth masking occludes the
// light behind terrain/foliage. This is screen-space, NOT volumetric raymarching.
uniform sampler2D scene_depth : hint_depth_texture, filter_nearest;
uniform vec2 sun_uv = vec2(0.5,0.08);
uniform bool sun_visible = true;
uniform vec3 shaft_color : source_color = vec3(1.0,0.84,0.53);

void vertex() { POSITION = vec4(VERTEX.xy,1.0,1.0); }
void fragment() {
	vec2 position = SCREEN_UV;
	vec2 step_uv = (sun_uv-position)*0.98/32.0;
	float illumination = 1.0;
	float scattering = 0.0;
	float aspect = VIEWPORT_SIZE.x/VIEWPORT_SIZE.y;
	for (int i=0;i<32;i++) {
		position += step_uv;
		float depth = texture(scene_depth,clamp(position,vec2(0.001),vec2(0.999))).r;
		// Compatibility/OpenGL NDC is -1..1. Reconstruct view distance rather
		// than assuming a particular reversed-Z convention.
		float ndc_z = depth*2.0-1.0;
		// Perspective view-Z is independent of X/Y: avoid 32 full mat4 multiplies.
		float view_distance = abs((INV_PROJECTION_MATRIX[2].z*ndc_z+INV_PROJECTION_MATRIX[3].z)/(INV_PROJECTION_MATRIX[2].w*ndc_z+INV_PROJECTION_MATRIX[3].w));
		float sky_mask = step(1500.0,view_distance);
		vec2 radial = (position-sun_uv)*vec2(aspect,1.0);
		float solar_mask = exp(-dot(radial,radial)*420.0);
		scattering += solar_mask*sky_mask*illumination;
		illumination *= 0.965;
	}
	float visible = sun_visible ? 1.0 : 0.0;
	ALBEDO = shaft_color*min(scattering*0.075,0.65)*visible;
	ALPHA = 1.0;
}
