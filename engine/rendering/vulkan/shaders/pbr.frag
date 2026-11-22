#version 450

layout(location = 0) in vec4 v_color;
layout(location = 1) in vec2 v_uv;
layout(location = 2) in vec3 v_normal;
layout(location = 3) in vec3 v_world_pos;

layout(location = 0) out vec4 out_color;

layout(set = 0, binding = 0) uniform UniformBuffer {
    mat4 model;
    mat4 view;
    mat4 proj;
    vec4 camera_pos;
    vec4 light_dir;
    vec4 light_color;
    float light_intensity;
} ubo;

layout(set = 0, binding = 1) uniform sampler2D base_color_texture;
layout(set = 0, binding = 2) uniform sampler2D metallic_roughness_texture;
layout(set = 0, binding = 3) uniform sampler2D normal_texture;

layout(push_constant) push UniformPush {
    float metallic_factor;
    float roughness_factor;
    vec4 base_color_factor;
} push;

void main() {
    vec3 normal = normalize(v_normal);
    vec3 world_pos = v_world_pos;
    vec3 view_dir = normalize(ubo.camera_pos.xyz - world_pos);
    vec3 light_dir_norm = normalize(ubo.light_dir.xyz);

    vec3 base_color = push.base_color_factor.rgb * push.base_color_factor.a;
    float metallic = push.metallic_factor;
    float roughness = push.roughness_factor;

    // Simple PBR lighting (direct diffuse + specular)
    float diff = max(dot(normal, light_dir_norm), 0.0);
    vec3 diffuse = base_color * ubo.light_color.rgb * ubo.light_intensity * diff;

    vec3 halfway = normalize(light_dir_norm + view_dir);
    float spec_angle = max(dot(normal, halfway), 0.0);
    float spec_power = pow(spec_angle, 32.0);
    vec3 specular = ubo.light_color.rgb * ubo.light_intensity * spec_power * (1.0 - metallic);

    vec3 lighting = diffuse + specular;
    out_color = vec4(lighting, base_color.a);
}