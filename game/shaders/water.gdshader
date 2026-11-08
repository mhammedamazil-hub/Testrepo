shader_type spatial;
render_mode cull_disabled;

varying vec3 surface;

void vertex() {
	surface = VERTEX;
	float a = VERTEX.x * 0.19 + VERTEX.z * 0.13 + TIME * 0.65;
	float b = VERTEX.x * -0.31 + VERTEX.z * 0.11 + TIME * 0.95;
	VERTEX.y += sin(a) * 0.035 + sin(b) * 0.022;
	NORMAL = normalize(vec3(-cos(a)*0.00665 + cos(b)*0.00682, 1.0, -cos(a)*0.00455-cos(b)*0.00242));
}

void fragment() {
	float ripple = sin(surface.x*1.7 + surface.z*0.9 + TIME*1.3) * 0.016;
	NORMAL = normalize(NORMAL + vec3(ripple,0.0,ripple*0.6));
	float fresnel = pow(1.0-max(dot(normalize(NORMAL),normalize(VIEW)),0.0),4.0);
	ALBEDO = mix(vec3(0.018,0.15,0.16),vec3(0.16,0.32,0.36),fresnel);
	METALLIC = 0.48;
	ROUGHNESS = 0.14;
	SPECULAR = 0.7;
}
