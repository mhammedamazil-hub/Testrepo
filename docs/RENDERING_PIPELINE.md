# Rendering Pipeline

## Overview

The Reality Engine rendering pipeline is a Vulkan-based forward rendering pipeline with PBR materials, multiple light types, and camera support. The pipeline is implemented in the `VulkanRenderer` class which bridges the high-level `Renderer` interface with the Vulkan RHI.

## Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│  1. Camera Setup                                             │
│     - View matrix from camera position/orientation          │
│     - Projection matrix (perspective or orthographic)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Mesh & Material Preparation                              │
│     - Vertex/index buffers uploaded to GPU                  │
│     - PBR material descriptors (baseColor, metallic,       │
│       roughness, normal map) bound to descriptor sets       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Light Uniform Buffer Setup                               │
│     - Directional, point, spot lights with parameters       │
│     - Shadow map matrices (if shadow mapping enabled)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Frame Recording                                          │
│     - Begin command buffer                                   │
│     - Begin render pass (clear colors, depth)               │
│     - Bind graphics pipeline                                 │
│     - Bind vertex/index buffers                              │
│     - Bind descriptor sets (materials, lights, camera)      │
│     - Set viewport and scissor                               │
│     - Draw indexed (per mesh)                                │
│     - End render pass                                        │
│     - End command buffer                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  5. Queue Submit & Present                                   │
│     - Submit command buffer to graphics queue               │
│     - Acquire next swapchain image                          │
│     - Present to surface                                    │
└─────────────────────────────────────────────────────────────┘
```

## Camera System

### Supported Camera Types

| Type | Description | Use Case |
|------|-------------|----------|
| Perspective | Perspective projection with FOV | First-person, third-person, cinematic |
| Orthographic | Orthographic projection | UI, 2D, architectural, isometric |
| First-person | Camera controlled by keyboard/mouse | FPS games |
| Orbit | Camera orbits around a target | Model inspection, editor |

### Camera Matrices

- **View matrix**: Computed from camera position, target, and up vector
- **Projection matrix**: Perspective (`perspective(fov, aspect, near, far)`) or orthographic (`orthographic(left, right, bottom, top, near, far)`)
- **View-Projection matrix**: Combined matrix passed to shaders as uniform

### Camera Data (`CameraData`)

```cpp
struct CameraData {
    glm::vec3 position;
    glm::vec3 target;
    glm::vec3 up;
    float fov;           // degrees, for perspective
    float aspect;        // width/height ratio
    float near_plane;
    float far_plane;
    CameraType type;     // Perspective, Orthographic, etc.
};
```

## Mesh Resources

### Mesh Data (`MeshData`)

```cpp
struct MeshData {
    std::string name;
    std::vector<Vertex> vertices;   // Position, normal, UV, tangent
    std::vector<uint32_t> indices;
    std::string material_name;      // Reference to PBR material
};
```

### Vertex Format

```cpp
struct Vertex {
    glm::vec3 position;   // 3 floats
    glm::vec3 normal;     // 3 floats
    glm::vec2 uv;         // 2 floats
    glm::vec4 tangent;    // 4 floats (for normal mapping)
};
```

### GPU Resource Creation

1. `VulkanDevice::create_buffer()` creates `VkBuffer` + `VkDeviceMemory`
2. `VulkanDevice::upload_buffer()` copies CPU data to GPU memory
3. `VulkanRenderer::create_mesh()` creates vertex + index buffers per mesh
4. Buffers are bound via `VulkanCommandBuffer::bind_vertex_buffer()` / `bind_index_buffer()`

## PBR Materials

### PBR Material Data (`PBRMaterial`)

```cpp
struct PBRMaterial {
    std::string name;
    glm::vec4 base_color_factor;       // Base color (albedo) + alpha
    float metallic_factor;             // 0.0 = dielectric, 1.0 = metal
    float roughness_factor;            // 0.0 = smooth, 1.0 = rough
    glm::vec3 emissive_factor;         // Emissive color
    std::string base_color_texture;    // Texture file path
    std::string metallic_roughness_texture;
    std::string normal_texture;
    std::string emissive_texture;
    bool alpha_blend;                  // Enable alpha blending
};
```

### PBR Shader (`shaders/pbr.vert` / `shaders/pbr.frag`)

The PBR shader implements physically-based rendering per glTF 2.0 specifications:

- **Vertex shader**: Transforms vertex positions, passes normals/UVs/tangents to fragment shader
- **Fragment shader**: Computes PBR lighting using:
  - Normalized Blinn-Phong NDF (Trowbridge-Reitz GGX)
  - Smith-Schlick-GGX geometry function
  - Fresnel (Schlick approximation)
  - Metallic/roughness workflow

### Material Pipeline

1. `VulkanRenderer::create_material()` creates a graphics pipeline for each unique material
2. Pipeline includes: vertex shader, fragment shader, vertex input, rasterizer, depth-stencil, color blend
3. Descriptor sets bind material textures and uniform buffers per draw call
4. `VulkanRenderer::submit_draw_call()` binds the material's pipeline and descriptor set

## Lighting

### Supported Light Types

| Type | Parameters | Shadows |
|------|-----------|---------|
| Directional | Direction, color, intensity | Yes (cascaded/PCF planned) |
| Point | Position, color, intensity, range | Yes (omnidirectional) |
| Spot | Position, direction, color, intensity, range, inner/outer cone | Yes |

### Light Data (`LightData`)

```cpp
struct LightData {
    std::string name;
    LightType type;           // Directional, Point, Spot
    glm::vec3 color;
    float intensity;
    glm::vec3 position;       // For point/spot
    glm::vec3 direction;      // For directional/spot
    float range;              // For point/spot
    float inner_cone;         // For spot
    float outer_cone;         // For spot
    bool cast_shadows;
};
```

### HDR and Tone Mapping

- **HDR**: Rendering target uses `R16G16B16A16_SFLOAT` format for high dynamic range
- **Tone mapping**: ACES or Reinhard tone mapping applied in fragment shader
- **Gamma correction**: sRGB output with gamma 2.2

### Shadow Mapping

- Shadow maps rendered from light's point of view
- Depth comparison sampling with PCF filtering
- Directional lights: orthographic shadow projection
- Point lights: cubemap shadow mapping (6 faces)
- Spot lights: perspective shadow projection

## Depth Buffering

- Depth format: `D32_SFLOAT`
- Depth test: `VK_COMPARE_OP_LESS`
- Depth write: Enabled for opaque objects
- Depth bias: Optional for shadow acne reduction
- Clear value: 1.0 (far plane)

## Multiple Objects

The engine supports rendering multiple meshes with different materials in a single frame:

1. Each mesh has its own vertex/index buffers
2. Each mesh references a material by name
3. Materials are resolved to graphics pipelines and descriptor sets
4. Draw calls are grouped by material/pipeline for minimal state changes
5. Per-object transform matrices are passed as push constants or uniform buffers

## ECS Transform Integration

The engine integrates with the ECS (`engine/ecs/ecs.h`) Transform component:

- `Transform` component provides position, rotation, scale per entity
- `VulkanRenderer` reads transforms from ECS to compute model matrices
- Model matrices are passed to shaders as uniform data
- Entities with `Transform` + `Mesh` components are automatically rendered

## Render Pass

A single render pass with:
- **Color attachment**: Swapchain image format (B8G8R8A8_UNORM or R16G16B16A16_SFLOAT for HDR)
- **Depth attachment**: D32_SFLOAT
- **Subpass**: Single subpass for forward rendering
- **Load op**: Clear (for first frame) or load (for subsequent)
- **Store op**: Store

## Frame Lifecycle

1. `VulkanRenderer::init()` - Initialize Vulkan instance, device, swapchain, pipelines
2. Per frame:
   a. `VulkanRenderer::record_frame(frame_index)` - Record command buffer
   b. `VulkanDevice::acquire_next_image()` - Get next swapchain image
   c. `VulkanQueue::submit()` - Submit command buffer
   d. `VulkanDevice::present()` - Present to surface
3. `VulkanRenderer::shutdown()` - Cleanup all Vulkan resources

## Limitations

- Single thread for command buffer submission
- No async compute
- No ray tracing
- No compute shaders
- No mesh shaders
- No variable rate shading
