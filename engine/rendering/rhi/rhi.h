#pragma once

#include "rhi_types.h"
#include "core/error.h"

namespace reality {

// === RHI Window / Surface Abstraction ===
// Provides window creation and surface management independent of graphics API

struct RHIWindowDesc {
    std::string title = "Reality Engine";
    uint32_t width = 1280;
    uint32_t height = 720;
    bool resizable = true;
    bool fullscreen = false;
    bool borderless = false;
};

class RHIWindow {
public:
    virtual ~RHIWindow() = default;

    virtual Result<void> create(const RHIWindowDesc& desc) = 0;
    virtual void destroy() = 0;
    virtual void* native_handle() const = 0;  // Platform-specific window handle
    virtual uint32_t width() const = 0;
    virtual uint32_t height() const = 0;
    virtual bool should_close() const = 0;
    virtual void poll_events() = 0;
    virtual void* get_instance_extension_names(std::vector<const char*>& extensions) = 0;
    virtual Result<void> create_surface(RHIInstance* instance, RHISurface** surface) = 0;
};

// === RHI Instance ===
// Entry point for a rendering backend

struct RHIInstanceDesc {
    std::string application_name = "Reality Engine";
    uint32_t application_version = 1;
    std::string engine_name = "Reality Engine";
    uint32_t engine_version = 1;
    bool enable_validation_layers = false;
};

class RHIInstance {
public:
    virtual ~RHIInstance() = default;

    virtual Result<void> init(const RHIInstanceDesc& desc) = 0;
    virtual void shutdown() = 0;
    virtual bool is_initialized() const = 0;
    virtual RHIBackend backend() const = 0;

    // Enumerate available physical devices
    virtual Result<void> enumerate_physical_devices() = 0;
    virtual uint32_t physical_device_count() const = 0;

    // Create logical device from selected physical device
    virtual Result<void> create_device(uint32_t physical_device_index, RHIDevice** device) = 0;
};

// === RHI Device ===
// Represents a GPU device

struct RHIDeviceFeatures {
    bool geometry_shader = false;
    bool tessellation_shader = false;
    bool fill_mode_non_solid = false;
    bool wide_lines = false;
    bool sampler_anisotropy = false;
    bool texture_compression_bc = false;
    bool texture_compression_etc2 = false;
    bool texture_compression_astc = false;
};

class RHIDevice {
public:
    virtual ~RHIDevice() = default;

    virtual Result<void> init(RHIInstance* instance, uint32_t physical_device_index) = 0;
    virtual void shutdown() = 0;
    virtual bool is_initialized() const = 0;

    // Queue access
    virtual RHIQueue* graphics_queue() const = 0;
    virtual RHIQueue* present_queue() const = 0;
    virtual uint32_t graphics_queue_family_index() const = 0;
    virtual uint32_t present_queue_family_index() const = 0;

    // Resource creation
    virtual Result<void> create_buffer(const RHIBufferDesc& desc, RHIBuffer** buffer) = 0;
    virtual Result<void> destroy_buffer(RHIBuffer* buffer) = 0;
    virtual Result<void> upload_buffer(RHIBuffer* buffer, const void* data, uint64_t size, uint64_t offset = 0) = 0;

    virtual Result<void> create_texture(const RHITextureDesc& desc, RHITexture** texture) = 0;
    virtual Result<void> destroy_texture(RHITexture* texture) = 0;

    virtual Result<void> create_shader_module(const RHIShaderDesc& desc, RHIShaderModule** module) = 0;
    virtual Result<void> destroy_shader_module(RHIShaderModule* module) = 0;

    virtual Result<void> create_pipeline_layout(RHIDescriptorSetLayout** layout) = 0;
    virtual Result<void> destroy_pipeline_layout(RHIPipelineLayout* layout) = 0;

    virtual Result<void> create_graphics_pipeline(const RHIGraphicsPipelineDesc& desc,
                                                   RHIPipelineLayout* layout,
                                                   RHIRenderPass* render_pass,
                                                   RHIGraphicsPipeline** pipeline) = 0;
    virtual Result<void> destroy_graphics_pipeline(RHIGraphicsPipeline* pipeline) = 0;

    virtual Result<void> create_render_pass(RHIRenderPass** render_pass) = 0;
    virtual Result<void> destroy_render_pass(RHIRenderPass* render_pass) = 0;

    virtual Result<void> create_framebuffer(RHIFramebuffer** framebuffer) = 0;
    virtual Result<void> destroy_framebuffer(RHIFramebuffer* framebuffer) = 0;

    virtual Result<void> create_command_buffer(RHICommandBuffer** cmd_buffer) = 0;
    virtual Result<void> destroy_command_buffer(RHICommandBuffer* cmd_buffer) = 0;

    virtual Result<void> create_descriptor_set_layout(RHIDescriptorSetLayout** layout) = 0;
    virtual Result<void> destroy_descriptor_set_layout(RHIDescriptorSetLayout* layout) = 0;

    virtual Result<void> create_descriptor_pool(RHIDescriptorPool** pool) = 0;
    virtual Result<void> destroy_descriptor_pool(RHIDescriptorPool* pool) = 0;

    virtual Result<void> allocate_descriptor_sets(RHIDescriptorPool* pool,
                                                   RHIDescriptorSetLayout* layout,
                                                   RHIDescriptorSet** set) = 0;
    virtual Result<void> free_descriptor_sets(RHIDescriptorPool* pool,
                                              RHIDescriptorSet* set) = 0;

    virtual Result<void> create_sampler(RHISampler** sampler) = 0;
    virtual Result<void> destroy_sampler(RHISampler* sampler) = 0;

    // Swapchain
    virtual Result<void> create_swapchain(RHISurface* surface, const RHISwapchainDesc& desc,
                                           RHISwapchain** swapchain) = 0;
    virtual Result<void> destroy_swapchain(RHISwapchain* swapchain) = 0;
    virtual Result<void> acquire_next_image(RHISwapchain* swapchain, uint32_t* image_index) = 0;
    virtual Result<void> present(RHISwapchain* swapchain, uint32_t image_index) = 0;

    // Device properties
    virtual std::string device_name() const = 0;
    virtual uint32_t vendor_id() const = 0;
    virtual uint32_t device_id() const = 0;
    virtual RHIDeviceFeatures features() const = 0;

    // Synchronization primitives
    virtual Result<void> wait_idle() = 0;
};

// === RHI Queue ===
class RHIQueue {
public:
    virtual ~RHIQueue() = default;
    virtual Result<void> submit(RHICommandBuffer* cmd_buffer) = 0;
    virtual Result<void> wait_idle() = 0;
};

// Vulkan-specific submit with synchronization (used by VulkanRenderer)
// Defined in vulkan_rhi.h as an overload on VulkanQueue

// === RHI Surface ===
class RHISurface {
public:
    virtual ~RHISurface() = default;
    virtual Result<void> init(RHIInstance* instance, RHIWindow* window) = 0;
    virtual void destroy() = 0;
    virtual bool is_initialized() const = 0;
};

// === Command Buffer ===
class RHICommandBuffer {
public:
    virtual ~RHICommandBuffer() = default;

    virtual Result<void> begin() = 0;
    virtual Result<void> end() = 0;
    virtual Result<void> reset() = 0;

    // Render pass
    virtual Result<void> begin_render_pass(RHIRenderPass* render_pass,
                                            RHIFramebuffer* framebuffer,
                                            const RHIExtent2D& render_area,
                                            const std::vector<RHIColor>& clear_colors,
                                            float clear_depth,
                                            uint8_t clear_stencil) = 0;
    virtual Result<void> end_render_pass() = 0;

    // Drawing
    virtual Result<void> bind_pipeline(RHIGraphicsPipeline* pipeline) = 0;
    virtual Result<void> bind_vertex_buffer(uint32_t binding, RHIBuffer* buffer, uint64_t offset) = 0;
    virtual Result<void> bind_index_buffer(RHIBuffer* buffer, RHIFormat format) = 0;
    virtual Result<void> bind_descriptor_set(RHIPipelineLayout* layout,
                                              RHIDescriptorSet* set,
                                              uint32_t first_set,
                                              const std::vector<uint32_t>& dynamic_offsets) = 0;
    virtual Result<void> set_viewport(const RHIViewport& viewport) = 0;
    virtual Result<void> set_scissor(const RHIScissor& scissor) = 0;
    virtual Result<void> draw_indexed(uint32_t index_count, uint32_t instance_count,
                                       uint32_t first_index, uint32_t vertex_offset,
                                       uint32_t first_instance) = 0;
    virtual Result<void> draw(uint32_t vertex_count, uint32_t instance_count,
                               uint32_t first_vertex, uint32_t first_instance) = 0;

    // Barriers
    virtual Result<void> buffer_memory_barrier(RHIBuffer* buffer,
                                                uint32_t src_access_mask,
                                                uint32_t dst_access_mask,
                                                uint32_t src_stage,
                                                uint32_t dst_stage) = 0;
    virtual Result<void> image_memory_barrier(RHITexture* texture,
                                               uint32_t src_access_mask,
                                               uint32_t dst_access_mask,
                                               uint32_t src_stage,
                                               uint32_t dst_stage) = 0;
};

// === Descriptor types ===
struct RHIBufferInfo {
    RHIBuffer* buffer = nullptr;
    uint64_t offset = 0;
    uint64_t range = 0;
};

struct RHITextureInfo {
    RHITexture* texture = nullptr;
    RHISampler* sampler = nullptr;
};

struct RHIWriteDescriptorSet {
    RHIDescriptorSet* set = nullptr;
    uint32_t binding = 0;
    uint32_t array_element = 0;
    uint32_t descriptor_count = 1;
    bool is_buffer = false;
    bool is_texture = false;
    RHIBufferInfo buffer_info{};
    RHITextureInfo texture_info{};
};

// === RHI Resource base classes (complete for backend inheritance) ====

class RHIBuffer {
public:
    virtual ~RHIBuffer() = default;
};

class RHITexture {
public:
    virtual ~RHITexture() = default;
};

class RHIShaderModule {
public:
    virtual ~RHIShaderModule() = default;
};

class RHIPipelineLayout {
public:
    virtual ~RHIPipelineLayout() = default;
};

class RHIGraphicsPipeline {
public:
    virtual ~RHIGraphicsPipeline() = default;
};

class RHIRenderPass {
public:
    virtual ~RHIRenderPass() = default;
};

class RHIFramebuffer {
public:
    virtual ~RHIFramebuffer() = default;
};

class RHIDescriptorSetLayout {
public:
    virtual ~RHIDescriptorSetLayout() = default;
};

class RHIDescriptorPool {
public:
    virtual ~RHIDescriptorPool() = default;
};

class RHIDescriptorSet {
public:
    virtual ~RHIDescriptorSet() = default;
};

class RHISampler {
public:
    virtual ~RHISampler() = default;
};

class RHISwapchain {
public:
    virtual ~RHISwapchain() = default;
};

} // namespace reality