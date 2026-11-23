# Vulkan Implementation

## Overview

The Vulkan backend is a real Vulkan 1.3 implementation using the official Khronos Vulkan-Headers and Vulkan-Loader. It provides a complete Rendering Hardware Interface (RHI) implementation with dynamic function loading, validation layers, debug messaging, swapchain management, and full resource lifecycle management.

## Vulkan Version

- **API Version**: Vulkan 1.3
- **Headers**: `third_party/Vulkan-Headers/` (cloned from KhronosGroup/Vulkan-Headers)
- **Loader**: `third_party/Vulkan-Loader/` (cloned from KhronosGroup/Vulkan-Loader)

## Dynamic Function Loading

Vulkan functions are loaded dynamically using `vkGetInstanceProcAddr` and `vkGetDeviceProcAddr` via the `VulkanFunctionLoader` class. This avoids linking against `libvulkan.so` at build time and allows the engine to run on systems with different Vulkan loader versions.

### Function Categories

| Category | Functions | Loading Point |
|----------|-----------|---------------|
| Instance-level | `vkDestroyInstance`, `vkEnumeratePhysicalDevices`, `vkCreateDevice`, `vkCreateDebugUtilsMessengerEXT`, etc. | After `vkCreateInstance` |
| Device-level | `vkGetDeviceQueue`, `vkCreateSwapchainKHR`, `vkCreateImage`, `vkAllocateMemory`, etc. | After `vkCreateDevice` |

## Initialization Sequence

```
VulkanRenderer::init()
  └── VulkanInstance::init()
      ├── vkCreateInstance (with validation layers if enabled)
      ├── Load instance-level function pointers
      ├── Create debug messenger (if validation enabled)
      └── Enumerate physical devices
  ├── Select physical device
  ├── VulkanDevice::init()
      ├── vkCreateDevice
      ├── Get graphics and present queues
      ├── Load device-level function pointers
      └── Create command pool
  ├── VulkanSwapchain::create_swapchain()
      ├── vkCreateSwapchainKHR
      ├── vkGetSwapchainImagesKHR
      └── Create image views
  ├── Create graphics pipeline
  └── Create descriptor set layout and pool
```

## Validation Layers

Validation layers are enabled when `RHIInstanceDesc::enable_validation_layers` is `true`. The layers are:

- `VK_LAYER_KHRONOS_validation` - Standard Vulkan validation layer

A `VkDebugUtilsMessengerEXT` is created to receive debug messages, which are logged through the engine's logging system.

## Surface and Window

### Surface Creation

`VulkanWindow::create_surface()` creates a `VkSurfaceKHR` for the platform. Currently supports:

- **Headless mode**: Creates a null `VkSurfaceKHR` (no presentation possible, for CI/headless testing only)
- **Future**: VK_KHR_display, Xlib, Wayland, Win32 surface extensions

### Surface Access

`VulkanSurface` is a friend of `VulkanWindow`, allowing `VulkanWindow::create_surface()` to directly set the private `vk_instance_`, `vk_surface_`, and `initialized_` members. Public accessors:
- `vk_surface()` - Returns the `VkSurfaceKHR` handle
- `is_initialized()` - Returns surface initialization status

## Device and Queue

### Physical Device Selection

The first physical device that supports:
- Graphics queue family
- Required device features (sampler anisotropy, etc.)
- Vulkan 1.3 or compatible

### Logical Device

Created with:
- Graphics and present queue families
- Required device extensions (`VK_KHR_swapchain`, etc.)
- Validation layer support (if enabled)

### Queues

- `graphics_queue_` - For graphics commands
- `present_queue_` - For presentation (may be same as graphics queue)

## Resource Management

### Buffers

`VulkanBuffer` wraps `VkBuffer` + `VkDeviceMemory`:
- `init(VkBuffer, VkDeviceMemory, uint64_t size)` - Wraps existing Vulkan objects
- `cleanup(VkDevice)` - Destroys buffer and frees memory
- `vk_buffer()` - Returns `VkBuffer` handle
- `vk_memory()` - Returns `VkDeviceMemory` handle

Buffer creation flow:
1. `VulkanDevice::create_buffer()` calls `vkCreateBuffer`
2. Queries memory requirements via `vkGetBufferMemoryRequirements`
3. Allocates memory via `vkAllocateMemory`
4. Binds memory via `vkBindBufferMemory`
5. Wraps in `VulkanBuffer` and returns as `RHIBuffer*`

### Textures

`VulkanTexture` wraps `VkImage` + `VkDeviceMemory` + `VkImageView`:
- `init(VkImage, VkDeviceMemory, VkImageView, format, extent)`
- `cleanup(VkDevice)` - Destroys image view, image, and memory

### Shader Modules

`VulkanShaderModule` wraps `VkShaderModule`:
- `init(VkShaderModule, stage, entry_point)`
- Created from SPIR-V bytecode via `vkCreateShaderModule`

### Pipelines

`VulkanGraphicsPipeline` wraps `VkPipeline`:
- `init(VkPipeline)`
- Created via `vkCreateGraphicsPipelines`

### Descriptor Sets

Descriptor set layout, pool, and sets are created using standard Vulkan descriptor APIs:
- `vkCreateDescriptorSetLayout`
- `vkCreateDescriptorPool`
- `vkAllocateDescriptorSets`
- `vkUpdateDescriptorSets`

## Command Buffers

`VulkanCommandBuffer` wraps `VkCommandBuffer`:
- `begin()` / `end()` - Command buffer lifecycle
- `begin_render_pass()` / `end_render_pass()` - Render pass boundaries
- `bind_pipeline()` - Bind graphics pipeline
- `bind_vertex_buffer()` / `bind_index_buffer()` - Bind buffers
- `bind_descriptor_set()` - Bind descriptor sets
- `set_viewport()` / `set_scissor()` - Set dynamic state
- `draw_indexed()` / `draw()` - Draw commands
- Memory barriers for buffer/image transitions

Command buffer recording flow:
1. `vkBeginCommandBuffer`
2. Record draw commands
3. `vkEndCommandBuffer`
4. Submit via `vkQueueSubmit`

## Swapchain

`VulkanSwapchain` wraps `VkSwapchainKHR`:
- `init(VkDevice, VkPhysicalDevice, VkSurfaceKHR, width, height, VkQueue, VkQueue)`
- `acquire_next_image()` - Via `vkAcquireNextImageKHR`
- `present()` - Via `vkQueuePresentKHR`
- `cleanup(VkDevice)` - Destroys swapchain and image views

Surface format selection prefers `B8G8R8A8_UNORM` with `VK_COLOR_SPACE_SRGB_NONLINEAR_KHR`.

Presentation mode prefers `VK_PRESENT_MODE_FIFO_KHR` (v-sync).

## Error Handling

All Vulkan API calls check their return value (`VkResult`). On `VK_SUCCESS`, execution continues. On any other result, a `Result<void>` with `ErrorCode::INIT_FAILED` is returned with a descriptive error message including the Vulkan function name and location.

Errors are never silently swallowed.

## Memory Properties

Memory types are selected based on `RHIMemoryProperty`:
- `DeviceLocal` - GPU-local memory (device local bit)
- `HostVisible` - CPU accessible (host visible bit)
- `HostCoherent` - Host coherent (host coherent bit)
- `HostCached` - Host cached (host cached bit)

## Code Review Findings & Fixes

During Phase 2.1 code review, the following issues were discovered and fixed:

| Issue | Severity | Fix |
|-------|----------|-----|
| `vkCreateInstance`, `vkEnumerateInstanceLayerProperties`, `vkEnumerateInstanceExtensionProperties` called before being loaded via `vkGetInstanceProcAddr` | Critical | Load global functions via `vkGetInstanceProcAddr(nullptr, ...)` before instance creation; store as `VulkanFunctionLoader::vkGetInstanceProcAddr_fn` |
| `vkGetInstanceProcAddr`, `vkGetDeviceProcAddr` called directly in loader templates | Critical | Store as static function pointers; use `VulkanFunctionLoader::vkGetInstanceProcAddr_fn` and `vkGetDeviceProcAddr_fn` in templates |
| `present_queue_family_` = `UINT32_MAX` used in device queue create info | High | Set to `graphics_queue_family_` when no dedicated present queue |
| `VulkanQueue::submit(RHICommandBuffer*)` pure virtual not implemented | High | Added single-argument overload that delegates to 4-argument version |
| `VulkanDevice::graphics_queue()` / `present_queue()` not defined out-of-line | High | Added out-of-line definitions returning `graphics_queue_` / `present_queue_` |
| `VkPipelineShaderStageCreateInfo::module` not set (left as VK_NULL_HANDLE) | Critical | Create `VkShaderModule` from SPIR-V inside `create_graphics_pipeline`, set `module` field, cleanup after pipeline creation |
| Vertex attribute offsets all 0, all formats R32G32B32A32_SFLOAT | High | Added `R32G32B32_SFLOAT` and `R32G32_SFLOAT` to `RHIFormat`; fixed offsets (0, 12, 24, 32) and formats |
| `create_framebuffer()` always returned error | High | Implemented `VulkanSwapchain::create_framebuffers()` with per-image `VulkanFramebuffer` objects |
| No synchronization (semaphores/fences) in frame lifecycle | Critical | Added image_available/render_finished semaphores and in_flight fence to frame acquire/submit/present |
| `vkGetPhysicalDeviceSurfaceSupportKHR` etc. not in function loader | High | Added to `VulkanFunctionLoader` static members and LOAD_INSTANCE_FUNC |
| `VulkanRenderer::shutdown()` wrong destruction order | Medium | Fixed to destroy pipeline resources before swapchain/surface, device before instance |
| `create_command_buffer` missing `reinterpret_cast` | Medium | Added explicit cast from `VulkanCommandBuffer*` to `RHICommandBuffer*` |
| Double `reinterpret_cast` in `create_pipeline_layout` | Medium | Removed unnecessary nested cast |
| `VulkanSwapchain::acquire_next_image`/`present` unused `RHISwapchain*` parameter | Low | Removed unused parameter from VulkanSwapchain methods |

## Limitations

1. **No SPIR-V compiler bundled**: Shaders must be pre-compiled with `glslangValidator` before running. See `scripts/compile_shaders.py`. CI workflows install `glslang-tools` for SPIR-V compilation.

2. **Headless surface**: `VulkanWindow::create_surface()` creates a null `VkSurfaceKHR` when no display or VK_KHR_display is available. This allows compilation and initialization testing on headless CI machines but cannot present frames. Real presentation requires a GPU with display or software Vulkan (Mesa lavapipe).

3. **No compute shaders**: Only graphics pipelines are implemented.

4. **No ray tracing**: No `VK_KHR_ray_tracing` pipeline support.

5. **No mesh shaders**: No `VK_EXT_mesh_shader` support.

6. **No runtime GPU in sandbox**: Cannot execute Vulkan API calls locally. All Vulkan validation requires CI runners with Vulkan ICD (Mesa lavapipe or hardware GPU).

## Build Configuration

```cmake
# Enable Vulkan backend
-DREALITY_BUILD_VULKAN=ON

# Vulkan headers path
-DVULKAN_HEADERS_DIR=third_party/Vulkan-Headers

# Vulkan loader path
-DVULKAN_LOADER_DIR=third_party/Vulkan-Loader
```

The `REALITY_HAS_VULKAN` preprocessor definition is automatically set when Vulkan is found.

## Files

| File | Lines | Purpose |
|------|-------|---------|
| `vulkan_rhi.h` | ~200 | Class declarations for all Vulkan RHI objects |
| `vulkan_rhi.cpp` | ~2000 | Implementation of all Vulkan RHI objects |
| `vulkan_renderer.h` | ~150 | VulkanRenderer class declaration |
| `vulkan_renderer.cpp` | ~600 | VulkanRenderer implementation (Renderer interface bridge) |
| `shaders/pbr.vert` | ~50 | PBR vertex shader (GLSL 450) |
| `shaders/pbr.frag` | ~100 | PBR fragment shader (GLSL 450) |
