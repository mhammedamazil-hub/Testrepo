#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <memory>

namespace reality {

// === Result type for RHI operations ===
struct RHIResult {
    bool ok = true;
    std::string error_message;
    
    static RHIResult success() { return RHIResult{true, ""}; }
    static RHIResult failure(const std::string& msg) { return RHIResult{false, msg}; }
};

// === Backend identification ===
enum class RHIBackend {
    Unknown,
    Vulkan,
    Headless,  // No-op for CI/headless
};

// === Common types ===
struct RHIExtent2D {
    uint32_t width = 0;
    uint32_t height = 0;
};

struct RHIExtent3D {
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t depth = 1;
};

struct RHIColor {
    float r = 0.0f;
    float g = 0.0f;
    float b = 0.0f;
    float a = 1.0f;
};

struct RHIViewport {
    float x = 0.0f;
    float y = 0.0f;
    float width = 0.0f;
    float height = 0.0f;
    float min_depth = 0.0f;
    float max_depth = 1.0f;
};

struct RHIScissor {
    int32_t x = 0;
    int32_t y = 0;
    uint32_t width = 0;
    uint32_t height = 0;
};

// === Buffer types ===
enum class RHIBufferUsage : uint32_t {
    None = 0,
    VertexBuffer = 1 << 0,
    IndexBuffer = 1 << 1,
    UniformBuffer = 1 << 2,
    StorageBuffer = 1 << 3,
    TransferSrc = 1 << 4,
    TransferDst = 1 << 5,
    IndirectBuffer = 1 << 6,
};

enum class RHIMemoryProperty : uint32_t {
    None = 0,
    DeviceLocal = 1 << 0,
    HostVisible = 1 << 1,
    HostCoherent = 1 << 2,
    HostCached = 1 << 3,
    LazilyAllocated = 1 << 4,
};

struct RHIBufferDesc {
    uint64_t size = 0;
    RHIBufferUsage usage = RHIBufferUsage::None;
    RHIMemoryProperty properties = RHIMemoryProperty::None;
};

// === Texture types ===
enum class RHIFormat {
    Undefined,
    R8G8B8A8_UNORM,
    B8G8R8A8_UNORM,
    R32G32B32A32_SFLOAT,
    R32G32B32_SFLOAT,
    R32G32_SFLOAT,
    D32_SFLOAT,
    D24_UNORM_S8_UINT,
    R8G8B8A8_SRGB,
    B8G8R8A8_SRGB,
};

enum class RHIImageUsage : uint32_t {
    None = 0,
    Sampled = 1 << 0,
    Storage = 1 << 1,
    ColorAttachment = 1 << 2,
    DepthStencilAttachment = 1 << 3,
    TransferSrc = 1 << 4,
    TransferDst = 1 << 5,
};

struct RHITextureDesc {
    RHIExtent3D extent{};
    RHIFormat format = RHIFormat::Undefined;
    RHIImageUsage usage = RHIImageUsage::None;
    uint32_t mip_levels = 1;
    uint32_t array_layers = 1;
    uint32_t samples = 1;
};

// === Shader types ===
enum class RHIShaderStage : uint32_t {
    Vertex = 1 << 0,
    Fragment = 1 << 1,
    Compute = 1 << 2,
};

struct RHIShaderDesc {
    RHIShaderStage stage = RHIShaderStage::Vertex;
    std::string entry_point = "main";
    std::vector<uint32_t> spirv_code;  // SPIR-V bytecode
    std::string source_code;  // GLSL source (for debugging/fallback)
};

// === Pipeline types ===
enum class RHIPrimitiveTopology {
    TriangleList,
    TriangleStrip,
    LineList,
    PointList,
};

enum class RHIPolygonMode {
    Fill,
    Line,
    Point,
};

enum class RHICullMode {
    None,
    Front,
    Back,
    FrontAndBack,
};

enum class RHICompareOp {
    Never,
    Less,
    Equal,
    LessOrEqual,
    Greater,
    NotEqual,
    GreaterOrEqual,
    Always,
};

struct RHIVertexInputBinding {
    uint32_t binding = 0;
    uint32_t stride = 0;
    bool per_instance = false;
};

struct RHIVertexInputAttribute {
    uint32_t location = 0;
    uint32_t binding = 0;
    RHIFormat format = RHIFormat::Undefined;
    uint32_t offset = 0;
};

struct RHIRasterizerDesc {
    RHIPolygonMode polygon_mode = RHIPolygonMode::Fill;
    RHICullMode cull_mode = RHICullMode::Back;
    bool front_counter_clockwise = true;
    float depth_bias_constant = 0.0f;
};

struct RHIDepthStencilDesc {
    bool depth_test_enable = true;
    bool depth_write_enable = true;
    RHICompareOp depth_compare_op = RHICompareOp::Less;
    bool depth_bounds_test_enable = false;
    bool stencil_test_enable = false;
};

struct RHIColorBlendAttachment {
    bool blend_enable = false;
    uint32_t color_write_mask = 0xF;  // R, G, B, A
};

struct RHIColorBlendDesc {
    bool logic_op_enable = false;
    std::vector<RHIColorBlendAttachment> attachments;
};

struct RHIGraphicsPipelineDesc {
    std::vector<RHIShaderDesc> shaders;
    RHIPrimitiveTopology primitive_topology = RHIPrimitiveTopology::TriangleList;
    std::vector<RHIVertexInputBinding> vertex_bindings;
    std::vector<RHIVertexInputAttribute> vertex_attributes;
    RHIRasterizerDesc rasterizer{};
    RHIDepthStencilDesc depth_stencil{};
    RHIColorBlendDesc color_blend{};
    RHIExtent2D render_area{};
    uint32_t subpass = 0;
};

// === Command buffer types ===
enum class RHICommandBufferLevel {
    Primary,
    Secondary,
};

struct RHICommandBufferDesc {
    RHICommandBufferLevel level = RHICommandBufferLevel::Primary;
};

// === Swapchain types ===
struct RHISwapchainDesc {
    // Set by the backend based on surface capabilities
    RHIExtent2D extent{};
    RHIFormat format = RHIFormat::B8G8R8A8_UNORM;
    uint32_t image_count = 2;
    bool present_mode_fifo = true;  // V-sync
};

// === Abstract handles (opaque pointers) ===
struct RHIInstance;
struct RHIDevice;
struct RHIQueue;
struct RHISwapchain;
struct RHIBuffer;
struct RHITexture;
struct RHIShader;
struct RHIShaderModule;
struct RHIPipelineLayout;
struct RHIGraphicsPipeline;
struct RHICommandBuffer;
struct RHIFramebuffer;
struct RHIRenderPass;
struct RHIDescriptorSetLayout;
struct RHIDescriptorSet;
struct RHIDescriptorPool;
struct RHISampler;

// === Abstract surface/window handle ===
struct RHISurface;
struct RHIWindow;

} // namespace reality