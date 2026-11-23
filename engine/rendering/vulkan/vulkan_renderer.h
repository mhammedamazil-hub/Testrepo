#pragma once

#include "rendering/renderer.h"
#include "rhi/rhi.h"
#include "vulkan/vulkan_rhi.h"

#ifdef REALITY_HAS_VULKAN
#include <vulkan/vulkan.h>
#endif

#include <vector>
#include <string>
#include <unordered_map>
#include <memory>

namespace reality {

// === Mesh Resource ===
struct Vertex {
    float position[3];
    float normal[3];
    float uv[2];
    float color[4];
};

struct MeshData {
    std::string id;
    std::vector<Vertex> vertices;
    std::vector<uint32_t> indices;
};

// === Material (PBR) ===
struct PBRMaterial {
    std::string id;
    float base_color_factor[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    float metallic_factor = 0.0f;
    float roughness_factor = 1.0f;
    std::string base_color_texture;
    std::string metallic_roughness_texture;
    std::string normal_texture;
    bool has_normal_map = false;
};

// === Light ===
struct LightData {
    enum class Type { Directional, Point, Spot };
    Type type = Type::Directional;
    float color[3] = {1.0f, 1.0f, 1.0f};
    float intensity = 1.0f;
    float position[3] = {0.0f, 0.0f, 0.0f};
    float direction[3] = {0.0f, -1.0f, 0.0f};
    float range = 10.0f;
    float inner_cone = 0.0f;
    float outer_cone = 0.0f;
};

// === Camera ===
struct CameraData {
    enum class Type { Perspective, Orthographic };
    Type type = Type::Perspective;
    float position[3] = {0.0f, 0.0f, 3.0f};
    float target[3] = {0.0f, 0.0f, 0.0f};
    float up[3] = {0.0f, 1.0f, 0.0f};
    float fov_y = 45.0f;         // degrees, perspective only
    float aspect = 16.0f / 9.0f;
    float near_plane = 0.1f;
    float far_plane = 100.0f;
    float ortho_size = 10.0f;    // orthographic only
};

// === VulkanRenderer ===
// Implements the abstract Renderer interface using Vulkan RHI
class VulkanRenderer : public Renderer {
public:
    VulkanRenderer();
    ~VulkanRenderer() override;

    Result<void> init() override;
    Result<void> shutdown() override;
    bool is_initialized() const override { return initialized_; }

    Result<void> render(double dt) override;
    Result<void> submit_draw_call(const DrawCall& call) override;
    Result<void> clear() override;

    const char* name() const override { return "VulkanRenderer"; }

    Stats get_stats() const override { return stats_; }

    // Vulkan-specific access
#ifdef REALITY_HAS_VULKAN
    VulkanDevice* vulkan_device() { return vulkan_device_; }
    VulkanInstance* vulkan_instance() { return vulkan_instance_; }
#endif

    // Resource management
    Result<void> create_mesh(const MeshData& mesh_data);
    Result<void> destroy_mesh(const std::string& mesh_id);
    Result<void> create_material(const PBRMaterial& material);
    Result<void> destroy_material(const std::string& material_id);
    Result<void> create_light(const LightData& light);
    Result<void> set_camera(const CameraData& camera);

    // Frame buffer / swapchain
    Result<void> create_swapchain(uint32_t width, uint32_t height);
    Result<void> resize_swapchain(uint32_t width, uint32_t height);

    Stats stats_;

private:
    bool initialized_ = false;

#ifdef REALITY_HAS_VULKAN
    // VulkanInstance and VulkanDevice are complete types defined in vulkan_rhi.h.
    // RHI abstract types (RHISwapchain, RHIRenderPass, etc.) are forward-declared
    // opaque structs (incomplete types) - use raw pointers with explicit destroy.
    VulkanInstance* vulkan_instance_ = nullptr;
    VulkanDevice* vulkan_device_ = nullptr;
    VulkanWindow* vulkan_window_ = nullptr;
    VulkanSurface* vulkan_surface_ = nullptr;
    RHISwapchain* vulkan_swapchain_ = nullptr;
    RHICommandBuffer* vulkan_cmd_buffer_ = nullptr;
    RHIRenderPass* vulkan_render_pass_ = nullptr;
    RHIDescriptorSetLayout* vulkan_pipeline_layout_ = nullptr;
    RHIGraphicsPipeline* vulkan_pipeline_ = nullptr;
    // Resources
    std::unordered_map<std::string, RHIBuffer*> vertex_buffers_;
    std::unordered_map<std::string, RHIBuffer*> index_buffers_;
    std::unordered_map<std::string, PBRMaterial> materials_;
    std::unordered_map<std::string, LightData> lights_;
    CameraData camera_;

    // Uniform buffers for matrices and materials
    RHIBuffer* uniform_buffer_ = nullptr;


#endif

    // Frame timing
    uint32_t frame_count_ = 0;
    double total_frame_time_ = 0.0;

    // Pipeline creation
#ifdef REALITY_HAS_VULKAN
    Result<void> create_pipeline_resources();
    Result<void> destroy_pipeline_resources();
    Result<void> record_frame(uint32_t swapchain_image_index);
#endif
};

// Shaders are compiled from GLSL to SPIR-V at build time using glslangValidator.
// See engine/rendering/vulkan/shaders/ for GLSL sources.
// See scripts/compile_shaders.py for the compilation script.

} // namespace reality