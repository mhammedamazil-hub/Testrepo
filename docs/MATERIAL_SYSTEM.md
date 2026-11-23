# Material System

## Overview

The Reality Engine material system implements physically-based rendering (PBR) using the metallic-roughness workflow per glTF 2.0 specifications. Materials define how surfaces interact with light and are used by the Vulkan renderer to configure graphics pipelines and descriptor sets.

## PBR Material Data

### PBRMaterial Structure

```cpp
struct PBRMaterial {
    std::string name;
    
    // Base color (albedo)
    glm::vec4 base_color_factor = {1.0f, 1.0f, 1.0f, 1.0f};
    
    // Metallic-roughness parameters
    float metallic_factor = 1.0f;      // 0.0 = dielectric, 1.0 = metal
    float roughness_factor = 1.0f;     // 0.0 = smooth, 1.0 = rough
    
    // Emissive
    glm::vec3 emissive_factor = {0.0f, 0.0f, 0.0f};
    
    // Texture references (file paths)
    std::string base_color_texture;
    std::string metallic_roughness_texture;
    std::string normal_texture;
    std::string emissive_texture;
    
    // Blending
    bool alpha_blend = false;
};
```

### glTF 2.0 Conventions

The material system follows glTF 2.0 PBR metallic-roughness conventions:

| Parameter | glTF Property | Range | Description |
|-----------|--------------|-------|-------------|
| baseColorFactor | `pbrMetallicRoughness.baseColorFactor` | [0,1]^4 | Base color RGBA |
| metallicFactor | `pbrMetallicRoughness.metallicFactor` | [0,1] | Metalness |
| roughnessFactor | `pbrMetallicRoughness.roughnessFactor` | [0,1] | Surface roughness |
| emissiveFactor | `emissiveFactor` | [0,∞) | Emissive color |
| baseColorTexture | `pbrMetallicRoughness.baseColorTexture` | - | Albedo texture |
| metallicRoughnessTexture | `pbrMetallicRoughness.metallicRoughnessTexture` | - | Metallic (B channel) + Roughness (G channel) |
| normalTexture | `normalTexture` | - | Normal map (OpenGL convention) |
| emissiveTexture | `emissiveTexture` | - | Emissive map |

### Material Types

| Material Type | Metallic | Roughness | Example |
|--------------|----------|-----------|---------|
| Dielectric (plastic, glass) | 0.0 | 0.1-0.9 | Plastic, glass, rubber |
| Metal | 1.0 | 0.0-0.5 | Gold, aluminum, copper |
| Dielectric (smooth) | 0.0 | 0.0-0.1 | Polished plastic, varnished wood |
| Rough metal | 1.0 | 0.5-1.0 | Brushed metal, weathered metal |

## Material Pipeline

### Pipeline Creation

Each unique material configuration creates a Vulkan graphics pipeline:

1. `VulkanRenderer::create_material(PBRMaterial)` is called
2. Pipeline state is configured based on material properties:
   - Alpha blending enabled if `alpha_blend == true`
   - Depth write disabled if transparent
   - Rasterizer state (cull mode, polygon mode)
3. `vkCreateGraphicsPipelines` creates the `VkPipeline`
4. Pipeline is cached by material name for reuse

### Descriptor Sets

Each material uses descriptor sets to bind:
- **Uniform buffer 0**: Camera matrices (view-projection)
- **Uniform buffer 1**: Material parameters (baseColor, metallic, roughness, emissive)
- **Uniform buffer 2**: Light data (directional, point, spot lights)
- **Sampler 0**: Base color texture
- **Sampler 1**: Metallic-roughness texture
- **Sampler 2**: Normal texture
- **Sampler 3**: Emissive texture

### Draw Call Flow

```
submit_draw_call(DrawCall)
  ├── Resolve material by name -> VulkanGraphicsPipeline
  ├── Bind graphics pipeline
  ├── Bind material descriptor set
  ├── Bind vertex buffer
  ├── Bind index buffer
  └── draw_indexed(index_count, ...)
```

## Shader Integration

### PBR Vertex Shader (`shaders/pbr.vert`)

Inputs:
- `in vec3 position` - Vertex position
- `in vec3 normal` - Vertex normal
- `in vec2 uv` - Texture coordinates
- `in vec4 tangent` - Tangent vector (for normal mapping)

Uniforms:
- `model` - Model matrix
- `view_proj` - View-projection matrix

Outputs to fragment shader:
- `world_position` - Position in world space
- `world_normal` - Normal in world space
- `uv` - Texture coordinates

### PBR Fragment Shader (`shaders/pbr.frag`)

Inputs:
- `world_position`, `world_normal`, `uv`

Uniforms:
- `camera_position` - Camera world position
- `base_color_factor`, `metallic_factor`, `roughness_factor`
- `emissive_factor`
- Light data (directional, point, spot)
- Texture samplers

Output:
- `fragColor` - HDR color output

### PBR Lighting Equation

The fragment shader implements the Cook-Torrance BRDF:

```
Lo = ∫ (DFG * Fi * (1 - F0) + F0) * Light * cos(theta) dω

Where:
  D = Normal distribution function (Trowbridge-Reitz GGX)
  F = Fresnel (Schlick approximation)
  G = Geometry function (Smith-Schlick-GGX)
  F0 = Base color * metallic + specular (0.04) * (1 - metallic)
```

## Texture Samplers

### Sampler Configuration

| Parameter | Value |
|-----------|-------|
| Mag filter | VK_FILTER_LINEAR |
| Min filter | VK_FILTER_LINEAR |
| Mipmap mode | VK_SAMPLER_MIPMAP_MODE_LINEAR |
| Address mode U | VK_SAMPLER_ADDRESS_MODE_REPEAT |
| Address mode V | VK_SAMPLER_ADDRESS_MODE_REPEAT |
| Address mode W | VK_SAMPLER_ADDRESS_MODE_REPEAT |
| Mip LOD bias | 0.0 |
| Max anisotropy | 16.0 (if supported) |
| Compare enable | VK_FALSE |
| Border color | VK_BORDER_COLOR_FLOAT_OPAQUE_WHITE |
| Unnormalized coordinates | VK_FALSE |

## Material Creation Example

```cpp
PBRMaterial material{};
material.name = "gold_metal";
material.base_color_factor = {1.0f, 0.8f, 0.4f, 1.0f};
material.metallic_factor = 1.0f;
material.roughness_factor = 0.1f;

auto result = vulkan_renderer->create_material(material);
// Use material name in MeshData to reference
```

## Limitations

1. **No material instance system**: Each material name maps to one pipeline; no per-instance material overrides
2. **No texture loading**: Texture file paths are stored but actual texture loading (from disk) is not yet implemented
3. **No material variants**: No support for specular workflow (only metallic-roughness)
4. **No subsurface scattering**: No SSS profile support
5. **No clear coat**: No clear coat layer support
6. **No anisotropic**: No anisotropic roughness support

## Future Enhancements

- Texture loading from disk (KTX2, PNG, JPG)
- Material instances with per-instance parameter overrides
- Specular workflow support
- Subsurface scattering
- Clear coat
- Anisotropic materials
- Material parameter animation
