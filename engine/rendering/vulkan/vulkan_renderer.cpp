#include "vulkan/vulkan_renderer.h"
#include "core/logging.h"
#include "core/error.h"
#include "core/config.h"

#ifdef REALITY_HAS_VULKAN
#include <vulkan/vulkan.h>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <sstream>
#include <iostream>
#endif

namespace reality {

// === Shader loading ===
// Shaders are compiled from GLSL to SPIR-V at build time using glslangValidator.
// The compiled .spv files are loaded at runtime.
// See engine/rendering/vulkan/shaders/ for GLSL sources.
// See scripts/compile_shaders.py for the compilation script.

static std::vector<uint32_t> load_spirv_file(const std::string& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        return {};
    }
    size_t size = file.tellg();
    file.seekg(0, std::ios::beg);
    std::vector<uint32_t> spirv(size / 4);
    file.read(reinterpret_cast<char*>(spirv.data()), size);
    return spirv;
}

// === VulkanRenderer ===

VulkanRenderer::VulkanRenderer() {
    stats_ = Stats{};
}

VulkanRenderer::~VulkanRenderer() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> VulkanRenderer::init() {
#ifdef REALITY_HAS_VULKAN
    REALITY_LOG(INFO, "Initializing VulkanRenderer...");

    // Create Vulkan instance
    vulkan_instance_ = new VulkanInstance();
    RHIInstanceDesc instance_desc{};
    instance_desc.application_name = "Reality Engine";
    instance_desc.application_version = 1;
    instance_desc.engine_name = "Reality Engine";
    instance_desc.engine_version = 1;
    instance_desc.enable_validation_layers = true;

    auto instance_result = vulkan_instance_->init(instance_desc);
    if (!instance_result) {
        REALITY_LOG(ERROR, "Failed to create Vulkan instance: " + instance_result.error().message);
        vulkan_instance_->shutdown();
        delete vulkan_instance_;
        vulkan_instance_ = nullptr;
        return instance_result;
    }

    // Create Vulkan device
    vulkan_device_ = new VulkanDevice();
    auto device_result = vulkan_device_->init(vulkan_instance_, 0);
    if (!device_result) {
        REALITY_LOG(ERROR, "Failed to init Vulkan device: " + device_result.error().message);
        vulkan_instance_->shutdown();
        delete vulkan_instance_;
        vulkan_instance_ = nullptr;
        delete vulkan_device_;
        vulkan_device_ = nullptr;
        return device_result;
    }

    REALITY_LOG(INFO, "VulkanRenderer initialized successfully");
    initialized_ = true;
    return Result<void>();
#else
    REALITY_LOG(ERROR, "VulkanRenderer: REALITY_HAS_VULKAN not defined");
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available - REALITY_HAS_VULKAN not defined",
              "vulkan_renderer.cpp:VulkanRenderer::init"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::shutdown() {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        return Result<void>();
    }

    REALITY_LOG(INFO, "Shutting down VulkanRenderer...");

    // Destroy pipeline resources
    destroy_pipeline_resources();

    // Destroy swapchain, surface, window
    if (vulkan_swapchain_) {
        vulkan_device_->destroy_swapchain(vulkan_swapchain_);
        vulkan_swapchain_ = nullptr;
    }
    if (vulkan_surface_) {
        vulkan_surface_->destroy();
        delete vulkan_surface_;
        vulkan_surface_ = nullptr;
    }
    if (vulkan_window_) {
        vulkan_window_->destroy();
        delete vulkan_window_;
        vulkan_window_ = nullptr;
    }

    // Destroy device and instance
    if (vulkan_device_) {
        vulkan_device_->shutdown();
        delete vulkan_device_;
        vulkan_device_ = nullptr;
    }
    if (vulkan_instance_) {
        vulkan_instance_->shutdown();
        delete vulkan_instance_;
        vulkan_instance_ = nullptr;
    }

    initialized_ = false;
    REALITY_LOG(INFO, "VulkanRenderer shutdown complete");
    return Result<void>();
#else
    return Result<void>();
#endif
}

Result<void> VulkanRenderer::render(double dt) {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "VulkanRenderer not initialized",
                  "vulkan_renderer.cpp:VulkanRenderer::render"};
        return Result<void>(err);
    }

    auto frame_start = std::chrono::high_resolution_clock::now();

    // Acquire next swapchain image with synchronization
    if (!vulkan_swapchain_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "Swapchain not created",
                  "vulkan_renderer.cpp:VulkanRenderer::render"};
        return Result<void>(err);
    }

    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(vulkan_swapchain_);

    // Wait for in-flight fence from previous frame
    VkFence fence = vk_sc->in_flight_fence();
    VkResult result = VulkanFunctionLoader::vkWaitForFences(vulkan_device_->vk_device(), 1, &fence, VK_TRUE, UINT64_MAX);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to wait for fence",
            "vulkan_renderer.cpp:VulkanRenderer::render"});
    }
    result = VulkanFunctionLoader::vkResetFences(vulkan_device_->vk_device(), 1, &fence);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to reset fence",
            "vulkan_renderer.cpp:VulkanRenderer::render"});
    }

    // Acquire next image (signals image_available semaphore)
    uint32_t image_index = 0;
    auto acquire_result = vulkan_device_->acquire_next_image(vulkan_swapchain_, &image_index);
    if (!acquire_result) {
        REALITY_LOG(ERROR, "Failed to acquire swapchain image: " + acquire_result.error().message);
        return acquire_result;
    }

    // Record and submit command buffer (waits on image_available, signals render_finished, waits on fence)
    auto record_result = record_frame(image_index);
    if (!record_result) {
        REALITY_LOG(ERROR, "Failed to record frame: " + record_result.error().message);
        return record_result;
    }

    // Present (waits on render_finished semaphore)
    auto present_result = vulkan_device_->present(vulkan_swapchain_, image_index);
    if (!present_result) {
        REALITY_LOG(ERROR, "Failed to present: " + present_result.error().message);
        return present_result;
    }

    auto frame_end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> elapsed = frame_end - frame_start;
    stats_.frame_time_ms = elapsed.count();
    stats_.render_calls++;
    frame_count_++;
    total_frame_time_ += stats_.frame_time_ms;

    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::render"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::submit_draw_call(const DrawCall& call) {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "VulkanRenderer not initialized",
                  "vulkan_renderer.cpp:VulkanRenderer::submit_draw_call"};
        return Result<void>(err);
    }
    stats_.draw_calls++;
    if (call.index_count > 0) {
        stats_.triangles += call.index_count / 3;
    }
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::submit_draw_call"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::clear() {
#ifdef REALITY_HAS_VULKAN
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::clear"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::create_mesh(const MeshData& mesh_data) {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "VulkanRenderer not initialized",
                  "vulkan_renderer.cpp:VulkanRenderer::create_mesh"};
        return Result<void>(err);
    }

    // Create vertex buffer
    RHIBufferDesc vb_desc{};
    vb_desc.size = mesh_data.vertices.size() * sizeof(Vertex);
    vb_desc.usage = RHIBufferUsage::VertexBuffer;
    vb_desc.properties = static_cast<RHIMemoryProperty>(
        static_cast<uint32_t>(RHIMemoryProperty::HostVisible) |
        static_cast<uint32_t>(RHIMemoryProperty::HostCoherent));

    RHIBuffer* vertex_buffer = nullptr;
    auto vb_result = vulkan_device_->create_buffer(vb_desc, &vertex_buffer);
    if (!vb_result || !vertex_buffer) {
        Error err{ErrorCode::OUT_OF_MEMORY,
                  "Failed to create vertex buffer",
                  "vulkan_renderer.cpp:VulkanRenderer::create_mesh"};
        return Result<void>(err);
    }

    auto upload_result = vulkan_device_->upload_buffer(vertex_buffer,
                                                        mesh_data.vertices.data(),
                                                        vb_desc.size);
    if (!upload_result) {
        vulkan_device_->destroy_buffer(vertex_buffer);
        return upload_result;
    }

    // Create index buffer
    RHIBufferDesc ib_desc{};
    ib_desc.size = mesh_data.indices.size() * sizeof(uint32_t);
    ib_desc.usage = RHIBufferUsage::IndexBuffer;
    ib_desc.properties = static_cast<RHIMemoryProperty>(
        static_cast<uint32_t>(RHIMemoryProperty::HostVisible) |
        static_cast<uint32_t>(RHIMemoryProperty::HostCoherent));

    RHIBuffer* index_buffer = nullptr;
    auto ib_result = vulkan_device_->create_buffer(ib_desc, &index_buffer);
    if (!ib_result || !index_buffer) {
        vulkan_device_->destroy_buffer(vertex_buffer);
        Error err{ErrorCode::OUT_OF_MEMORY,
                  "Failed to create index buffer",
                  "vulkan_renderer.cpp:VulkanRenderer::create_mesh"};
        return Result<void>(err);
    }

    upload_result = vulkan_device_->upload_buffer(index_buffer,
                                                   mesh_data.indices.data(),
                                                   ib_desc.size);
    if (!upload_result) {
        vulkan_device_->destroy_buffer(vertex_buffer);
        vulkan_device_->destroy_buffer(index_buffer);
        return upload_result;
    }

    vertex_buffers_[mesh_data.id] = vertex_buffer;
    index_buffers_[mesh_data.id] = index_buffer;

    REALITY_LOG(INFO, "Created mesh: " + mesh_data.id +
                   " (" + std::to_string(mesh_data.vertices.size()) +
                   " vertices, " + std::to_string(mesh_data.indices.size()) + " indices)");
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::create_mesh"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::destroy_mesh(const std::string& mesh_id) {
#ifdef REALITY_HAS_VULKAN
    auto vb_it = vertex_buffers_.find(mesh_id);
    auto ib_it = index_buffers_.find(mesh_id);

    if (vb_it != vertex_buffers_.end()) {
        vulkan_device_->destroy_buffer(vb_it->second);
        vertex_buffers_.erase(vb_it);
    }
    if (ib_it != index_buffers_.end()) {
        vulkan_device_->destroy_buffer(ib_it->second);
        index_buffers_.erase(ib_it);
    }

    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::destroy_mesh"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::create_material(const PBRMaterial& material) {
#ifdef REALITY_HAS_VULKAN
    materials_[material.id] = material;
    REALITY_LOG(INFO, "Created material: " + material.id +
                   " (metallic=" + std::to_string(material.metallic_factor) +
                   ", roughness=" + std::to_string(material.roughness_factor) + ")");
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::create_material"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::destroy_material(const std::string& material_id) {
#ifdef REALITY_HAS_VULKAN
    materials_.erase(material_id);
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::destroy_material"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::create_light(const LightData& light) {
#ifdef REALITY_HAS_VULKAN
    lights_[std::to_string(lights_.size())] = light;
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::create_light"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::set_camera(const CameraData& camera) {
#ifdef REALITY_HAS_VULKAN
    camera_ = camera;
    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::set_camera"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::create_swapchain(uint32_t width, uint32_t height) {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "VulkanRenderer not initialized",
                  "vulkan_renderer.cpp:VulkanRenderer::create_swapchain"};
        return Result<void>(err);
    }

    // Create window
    vulkan_window_ = new VulkanWindow();
    RHIWindowDesc window_desc{};
    window_desc.title = "Reality Engine";
    window_desc.width = width;
    window_desc.height = height;
    auto window_result = vulkan_window_->create(window_desc);
    if (!window_result) {
        delete vulkan_window_;
        vulkan_window_ = nullptr;
        return window_result;
    }

    // Create surface
    vulkan_surface_ = new VulkanSurface();
    auto surface_result = vulkan_surface_->init(vulkan_instance_, vulkan_window_);
    if (!surface_result) {
        delete vulkan_surface_;
        vulkan_surface_ = nullptr;
        return surface_result;
    }

    // Create swapchain via device
    RHISwapchainDesc swapchain_desc{};
    swapchain_desc.extent.width = width;
    swapchain_desc.extent.height = height;
    swapchain_desc.image_count = 2;

    RHISwapchain* swapchain_ptr = nullptr;
    auto sc_result = vulkan_device_->create_swapchain(vulkan_surface_, swapchain_desc, &swapchain_ptr);
    if (!sc_result || !swapchain_ptr) {
        return sc_result;
    }
    vulkan_swapchain_ = swapchain_ptr;

    // Create pipeline resources (render pass, pipeline, etc.)
    auto pipeline_result = create_pipeline_resources();
    if (!pipeline_result) {
        return pipeline_result;
    }

    // Create framebuffers for each swapchain image
    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(vulkan_swapchain_);
    auto fb_result = vk_sc->create_framebuffers(
        reinterpret_cast<VulkanRenderPass*>(vulkan_render_pass_)->vk_render_pass());
    if (!fb_result) {
        return fb_result;
    }

    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::create_swapchain"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::resize_swapchain(uint32_t width, uint32_t height) {
#ifdef REALITY_HAS_VULKAN
    if (!initialized_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "VulkanRenderer not initialized",
                  "vulkan_renderer.cpp:VulkanRenderer::resize_swapchain"};
        return Result<void>(err);
    }

    // Recreate pipeline resources
    destroy_pipeline_resources();

    // Destroy old swapchain
    if (vulkan_swapchain_) {
        vulkan_device_->destroy_swapchain(vulkan_swapchain_);
        vulkan_swapchain_ = nullptr;
    }

    RHISwapchainDesc swapchain_desc{};
    swapchain_desc.extent.width = width;
    swapchain_desc.extent.height = height;
    swapchain_desc.image_count = 2;

    RHISwapchain* swapchain_ptr = nullptr;
    auto sc_result = vulkan_device_->create_swapchain(vulkan_surface_, swapchain_desc, &swapchain_ptr);
    if (!sc_result || !swapchain_ptr) {
        return sc_result;
    }
    vulkan_swapchain_ = swapchain_ptr;

    return create_pipeline_resources();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::resize_swapchain"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::create_pipeline_resources() {
#ifdef REALITY_HAS_VULKAN
    // Create render pass
    RHIRenderPass* render_pass = nullptr;
    auto rp_result = vulkan_device_->create_render_pass(&render_pass);
    if (!rp_result || !render_pass) {
        return rp_result;
    }
    vulkan_render_pass_ = render_pass;

    // Create descriptor set layout (used as pipeline layout)
    auto pl_result = vulkan_device_->create_descriptor_set_layout(&vulkan_pipeline_layout_);
    if (!pl_result || !vulkan_pipeline_layout_) {
        return pl_result;
    }

    // Load shaders
    auto vert_spirv = load_spirv_file("engine/rendering/vulkan/shaders/pbr.vert.spv");
    auto frag_spirv = load_spirv_file("engine/rendering/vulkan/shaders/pbr.frag.spv");

    if (vert_spirv.empty() || frag_spirv.empty()) {
        REALITY_LOG(WARN, "SPIR-V shader files not found - shaders must be compiled from GLSL first");
        REALITY_LOG(WARN, "Run: python scripts/compile_shaders.py");
    }

    // Create graphics pipeline
    RHIGraphicsPipelineDesc pipeline_desc{};
    pipeline_desc.primitive_topology = RHIPrimitiveTopology::TriangleList;

    // Vertex input bindings
    RHIVertexInputBinding binding{};
    binding.binding = 0;
    binding.stride = sizeof(Vertex);
    binding.per_instance = false;
    pipeline_desc.vertex_bindings.push_back(binding);

    // Vertex attributes: position(0), normal(1), uv(2), color(3)
    // Vertex layout: position[3] (offset 0), normal[3] (offset 12), uv[2] (offset 24), color[4] (offset 32)
    RHIVertexInputAttribute attr_pos{};
    attr_pos.location = 0;
    attr_pos.binding = 0;
    attr_pos.format = RHIFormat::R32G32B32_SFLOAT;
    attr_pos.offset = 0;
    pipeline_desc.vertex_attributes.push_back(attr_pos);

    RHIVertexInputAttribute attr_normal{};
    attr_normal.location = 1;
    attr_normal.binding = 0;
    attr_normal.format = RHIFormat::R32G32B32_SFLOAT;
    attr_normal.offset = 12;
    pipeline_desc.vertex_attributes.push_back(attr_normal);

    RHIVertexInputAttribute attr_uv{};
    attr_uv.location = 2;
    attr_uv.binding = 0;
    attr_uv.format = RHIFormat::R32G32_SFLOAT;
    attr_uv.offset = 24;
    pipeline_desc.vertex_attributes.push_back(attr_uv);

    RHIVertexInputAttribute attr_color{};
    attr_color.location = 3;
    attr_color.binding = 0;
    attr_color.format = RHIFormat::R32G32B32A32_SFLOAT;
    attr_color.offset = 32;
    pipeline_desc.vertex_attributes.push_back(attr_color);

    pipeline_desc.render_area.width = 1280;
    pipeline_desc.render_area.height = 720;

    // Shader modules
    RHIShaderModule* vert_module = nullptr;
    RHIShaderModule* frag_module = nullptr;

    if (!vert_spirv.empty()) {
        RHIShaderDesc vert_shader_desc{};
        vert_shader_desc.stage = RHIShaderStage::Vertex;
        vert_shader_desc.entry_point = "main";
        vert_shader_desc.spirv_code = vert_spirv;
        auto vsm_result = vulkan_device_->create_shader_module(vert_shader_desc, &vert_module);
        if (!vsm_result) {
            REALITY_LOG(WARN, "Failed to create vertex shader module: " + vsm_result.error().message);
        }
    }

    if (!frag_spirv.empty()) {
        RHIShaderDesc frag_shader_desc{};
        frag_shader_desc.stage = RHIShaderStage::Fragment;
        frag_shader_desc.entry_point = "main";
        frag_shader_desc.spirv_code = frag_spirv;
        auto fsm_result = vulkan_device_->create_shader_module(frag_shader_desc, &frag_module);
        if (!fsm_result) {
            REALITY_LOG(WARN, "Failed to create fragment shader module: " + fsm_result.error().message);
        }
    }

    RHIGraphicsPipeline* pipeline = nullptr;
    auto pipe_result = vulkan_device_->create_graphics_pipeline(pipeline_desc,
                                                                 reinterpret_cast<RHIPipelineLayout*>(vulkan_pipeline_layout_),
                                                                 vulkan_render_pass_,
                                                                 &pipeline);
    if (!pipe_result || !pipeline) {
        return pipe_result;
    }
    vulkan_pipeline_ = pipeline;

    // Framebuffers are created per swapchain image in create_swapchain()
    // via VulkanSwapchain::create_framebuffers()

    // Create command buffer
    RHICommandBuffer* cmd_buffer = nullptr;
    auto cb_result = vulkan_device_->create_command_buffer(&cmd_buffer);
    if (!cb_result || !cmd_buffer) {
        return cb_result;
    }
    vulkan_cmd_buffer_ = cmd_buffer;

    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::create_pipeline_resources"};
    return Result<void>(err);
#endif
}

Result<void> VulkanRenderer::destroy_pipeline_resources() {
#ifdef REALITY_HAS_VULKAN
    if (vulkan_cmd_buffer_) {
        vulkan_device_->destroy_command_buffer(vulkan_cmd_buffer_);
        vulkan_cmd_buffer_ = nullptr;
    }
    // Destroy framebuffers via swapchain
    if (vulkan_swapchain_) {
        auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(vulkan_swapchain_);
        vk_sc->destroy_framebuffers(vulkan_device_->vk_device());
    }
    if (vulkan_pipeline_) {
        vulkan_device_->destroy_graphics_pipeline(vulkan_pipeline_);
        vulkan_pipeline_ = nullptr;
    }
    if (vulkan_pipeline_layout_) {
        vulkan_device_->destroy_descriptor_set_layout(vulkan_pipeline_layout_);
        vulkan_pipeline_layout_ = nullptr;
    }
    if (vulkan_render_pass_) {
        vulkan_device_->destroy_render_pass(vulkan_render_pass_);
        vulkan_render_pass_ = nullptr;
    }
    return Result<void>();
#else
    return Result<void>();
#endif
}

Result<void> VulkanRenderer::record_frame(uint32_t swapchain_image_index) {
#ifdef REALITY_HAS_VULKAN
    if (!vulkan_cmd_buffer_) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "No command buffer",
                  "vulkan_renderer.cpp:VulkanRenderer::record_frame"};
        return Result<void>(err);
    }

    auto begin_result = vulkan_cmd_buffer_->begin();
    if (!begin_result) {
        return begin_result;
    }

    // Get framebuffer for current swapchain image
    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(vulkan_swapchain_);
    RHIFramebuffer* framebuffer = vk_sc->get_framebuffer(swapchain_image_index);
    if (!framebuffer) {
        Error err{ErrorCode::NOT_INITIALIZED,
                  "No framebuffer for swapchain image",
                  "vulkan_renderer.cpp:VulkanRenderer::record_frame"};
        return Result<void>(err);
    }

    // Begin render pass
    std::vector<RHIColor> clear_colors;
    clear_colors.push_back(RHIColor{0.1f, 0.1f, 0.1f, 1.0f});
    auto rp_begin_result = vulkan_cmd_buffer_->begin_render_pass(
        vulkan_render_pass_,
        framebuffer,
        {1280, 720},
        clear_colors,
        1.0f,
        0);
    if (!rp_begin_result) {
        return rp_begin_result;
    }

    // Bind pipeline
    auto bind_result = vulkan_cmd_buffer_->bind_pipeline(vulkan_pipeline_);
    if (!bind_result) {
        return bind_result;
    }

    // Set viewport and scissor
    RHIViewport viewport{};
    viewport.width = 1280.0f;
    viewport.height = 720.0f;
    viewport.max_depth = 1.0f;
    vulkan_cmd_buffer_->set_viewport(viewport);

    RHIScissor scissor{};
    scissor.width = 1280;
    scissor.height = 720;
    vulkan_cmd_buffer_->set_scissor(scissor);

    // Draw all meshes
    for (auto& pair : vertex_buffers_) {
        const std::string& mesh_id = pair.first;
        RHIBuffer* vb = pair.second;
        auto ib_it = index_buffers_.find(mesh_id);
        if (ib_it == index_buffers_.end()) continue;

        RHIBuffer* ib = ib_it->second;

        vulkan_cmd_buffer_->bind_vertex_buffer(0, vb, 0);
        vulkan_cmd_buffer_->bind_index_buffer(ib, RHIFormat::R32G32B32A32_SFLOAT);

        // Draw a single triangle per mesh (placeholder - real index count would be tracked)
        vulkan_cmd_buffer_->draw_indexed(3, 1, 0, 0, 0);
    }

    auto rp_end_result = vulkan_cmd_buffer_->end_render_pass();
    if (!rp_end_result) {
        return rp_end_result;
    }

    auto end_result = vulkan_cmd_buffer_->end();
    if (!end_result) {
        return end_result;
    }

    // Submit to graphics queue with synchronization
    RHIQueue* queue = vulkan_device_->graphics_queue();
    auto* vk_queue = reinterpret_cast<VulkanQueue*>(queue);
    auto submit_result = vk_queue->submit(vulkan_cmd_buffer_,
                                           vk_sc->image_available_semaphore(),
                                           vk_sc->render_finished_semaphore(),
                                           vk_sc->in_flight_fence());
    if (!submit_result) {
        return submit_result;
    }

    return Result<void>();
#else
    Error err{ErrorCode::BACKEND_UNAVAILABLE,
              "Vulkan not available",
              "vulkan_renderer.cpp:VulkanRenderer::record_frame"};
    return Result<void>(err);
#endif
}

} // namespace reality