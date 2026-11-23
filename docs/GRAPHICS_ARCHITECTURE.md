# Graphics Architecture

## Overview

The Reality Engine graphics subsystem is a modular Rendering Hardware Interface (RHI) with multiple backends. The architecture separates platform-agnostic rendering concepts from API-specific implementations, enabling the engine to support Vulkan, headless/offscreen rendering, and future backends (DirectX, Metal, OpenGL) without changing renderer-level code.

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Application / Game Logic                                   │
├─────────────────────────────────────────────────────────────┤
│  Renderer (VulkanRenderer / HeadlessRenderer)               │
│  - Scene graph, mesh/material/light management              │
│  - Camera matrices, draw call recording                     │
├─────────────────────────────────────────────────────────────┤
│  RHI (Rendering Hardware Interface)                         │
│  - Abstract interfaces: RHIInstance, RHIDevice, RHIQueue,   │
│    RHIBuffer, RHITexture, RHIGraphicsPipeline, etc.         │
│  - Resource descriptors and creation parameters             │
├─────────────────────────────────────────────────────────────┤
│  Backend Implementations                                    │
│  - Vulkan: VulkanInstance, VulkanDevice, VulkanQueue,       │
│    VulkanBuffer, VulkanTexture, etc.                        │
│  - Headless: HeadlessRenderer (no-op for CI)                │
└─────────────────────────────────────────────────────────────┘
```

## Components

### RHI Abstraction (`engine/rendering/rhi/`)

| File | Purpose |
|------|---------|
| `rhi_types.h` | Common types: enums, descriptors, math types |
| `rhi.h` | Abstract base classes for all RHI objects |

The RHI defines opaque interface classes that backends implement. Each RHI object has a virtual destructor, enabling safe inheritance by backend implementations.

### Vulkan Backend (`engine/rendering/vulkan/`)

| File | Purpose |
|------|---------|
| `vulkan_rhi.h` | Vulkan backend class declarations |
| `vulkan_rhi.cpp` | Vulkan backend implementation (real Vulkan 1.3 API) |
| `vulkan_renderer.h` | VulkanRenderer class bridging Renderer interface |
| `vulkan_renderer.cpp` | VulkanRenderer implementation |
| `shaders/pbr.vert` | PBR vertex shader (GLSL) |
| `shaders/pbr.frag` | PBR fragment shader (GLSL) |

### Vulkan Backend Classes

| Class | RHI Base | Responsibility |
|-------|----------|----------------|
| `VulkanInstance` | `RHIInstance` | VkInstance creation, debug messenger, physical device enumeration |
| `VulkanDevice` | `RHIDevice` | Logical device, queues, memory management, resource creation |
| `VulkanQueue` | `RHIQueue` | Queue submission, wait idle |
| `VulkanSwapchain` | `RHISwapchain` | Swapchain creation, image acquisition, presentation |
| `VulkanBuffer` | `RHIBuffer` | Buffer creation, memory binding |
| `VulkanTexture` | `RHITexture` | Image, image view, memory creation |
| `VulkanShaderModule` | `RHIShaderModule` | SPIR-V shader module creation |
| `VulkanPipelineLayout` | `RHIPipelineLayout` | Pipeline layout creation |
| `VulkanGraphicsPipeline` | `RHIGraphicsPipeline` | Graphics pipeline creation |
| `VulkanRenderPass` | `RHIRenderPass` | Render pass creation |
| `VulkanFramebuffer` | `RHIFramebuffer` | Framebuffer creation |
| `VulkanCommandBuffer` | `RHICommandBuffer` | Command buffer recording |
| `VulkanDescriptorSetLayout` | `RHIDescriptorSetLayout` | Descriptor set layout |
| `VulkanDescriptorPool` | `RHIDescriptorPool` | Descriptor pool |
| `VulkanDescriptorSet` | `RHIDescriptorSet` | Descriptor set allocation |
| `VulkanSampler` | `RHISampler` | Sampler creation |
| `VulkanSurface` | `RHISurface` | Surface creation (VkSurfaceKHR) |
| `VulkanWindow` | `RHIWindow` | Window abstraction (headless) |

### VulkanRenderer (`engine/rendering/vulkan/vulkan_renderer.*`)

The VulkanRenderer bridges the high-level `Renderer` interface (`engine/rendering/renderer.h`) with the Vulkan RHI. It manages:

- **Mesh resources**: Vertex/index buffer creation and GPU upload
- **Materials**: PBR material pipeline and descriptor set creation
- **Lights**: Directional, point, spot light uniform buffers
- **Camera**: View/projection matrix computation
- **Frame recording**: Command buffer recording and submission
- **Swapchain**: Image acquisition and presentation

### Headless Renderer (`engine/rendering/headless_renderer.*`)

Preserved from Phase 1. A no-op rendering backend for CI environments without GPU/display. Implements the same `Renderer` interface without any graphics API calls.

## Backend Selection

The backend is selected at runtime via the `--renderer` command-line option:

```
./reality_runtime --renderer vulkan     # Vulkan backend (requires GPU)
./reality_runtime --renderer headless   # Headless backend (CI-safe)
```

Or via the `--vulkan` flag for explicit Vulkan selection.

## Memory Management

All RHI resources use explicit lifetime management:
- Backend classes (`VulkanBuffer`, `VulkanTexture`, etc.) own their Vulkan handles (`VkBuffer`, `VkImage`, etc.)
- `init()` creates Vulkan resources
- `cleanup(VkDevice)` destroys Vulkan resources
- Destructors call `cleanup()` automatically
- RHI-level creation functions return base-class pointers via `reinterpret_cast`
- RHI-level destruction functions `reinterpret_cast` back and `delete` the object

## Error Handling

All RHI operations return `Result<void>` (from `engine/core/error.h`), which is either success or an `Error` with an error code and descriptive message. Errors are never silently swallowed.

## Thread Safety

The RHI is designed for single-threaded rendering command submission. Multi-threaded command buffer recording is supported via `VulkanCommandBuffer` objects, but submission to a `VulkanQueue` should be synchronized externally.

## Build Configuration

| CMake Variable | Description | Default |
|----------------|-------------|---------|
| `REALITY_BUILD_VULKAN` | Enable Vulkan backend | ON |
| `REALITY_HAS_VULKAN` | Preprocessor definition (set automatically when Vulkan found) | - |
| `VULKAN_HEADERS_DIR` | Path to Vulkan-Headers | `third_party/Vulkan-Headers` |
| `VULKAN_LOADER_DIR` | Path to Vulkan-Loader | `third_party/Vulkan-Loader` |

## Third-Party Dependencies

| Dependency | Source | Purpose |
|------------|--------|---------|
| Vulkan-Headers | `github.com/KhronosGroup/Vulkan-Headers` | Vulkan 1.3 API headers |
| Vulkan-Loader | `github.com/KhronosGroup/Vulkan-Loader` | Vulkan runtime loader |

## Limitations

- No SPIR-V compiler bundled; shaders must be pre-compiled with `glslangValidator`
- Headless backend creates a null `VkSurfaceKHR` - presentation requires a real display or VK_KHR_display
- Windows MinGW + Jolt Physics build issue is under investigation (do not remove Windows support)
- No runtime GPU available in CI sandbox; validation layer tests require graphics-capable runners
