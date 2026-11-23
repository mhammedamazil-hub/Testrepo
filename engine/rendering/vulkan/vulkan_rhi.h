#pragma once

#include "rhi/rhi.h"
#include "rhi/rhi_types.h"

#ifdef REALITY_HAS_VULKAN
#include <vulkan/vulkan.h>
#include <vulkan/vulkan.hpp>
#endif

#include <vector>
#include <string>
#include <unordered_map>
#include <memory>
#include <mutex>

namespace reality {

#ifdef REALITY_HAS_VULKAN

// === Vulkan function pointer loader ===
// Dynamically loads Vulkan functions to avoid requiring libvulkan.so at link time
class VulkanFunctionLoader {
public:
    static PFN_vkGetInstanceProcAddr load_get_instance_proc_addr();
    
    template <typename Func>
    static Func load_instance(VkInstance instance, const char* name) {
        if (!vkGetInstanceProcAddr_fn) return nullptr;
        return reinterpret_cast<Func>(vkGetInstanceProcAddr_fn(instance, name));
    }
   
    template <typename Func>
    static Func load_device(VkDevice device, const char* name) {
        if (!vkGetDeviceProcAddr_fn) return nullptr;
        return reinterpret_cast<Func>(vkGetDeviceProcAddr_fn(device, name));
    }

    // Core Vulkan 1.0 function pointers
    static PFN_vkGetInstanceProcAddr vkGetInstanceProcAddr_fn;
    static PFN_vkGetDeviceProcAddr vkGetDeviceProcAddr_fn;
    static PFN_vkCreateInstance vkCreateInstance;
    static PFN_vkDestroyInstance vkDestroyInstance;
    static PFN_vkEnumeratePhysicalDevices vkEnumeratePhysicalDevices;
    static PFN_vkGetPhysicalDeviceProperties vkGetPhysicalDeviceProperties;
    static PFN_vkGetPhysicalDeviceFeatures vkGetPhysicalDeviceFeatures;
    static PFN_vkGetPhysicalDeviceQueueFamilyProperties vkGetPhysicalDeviceQueueFamilyProperties;
    static PFN_vkGetPhysicalDeviceMemoryProperties vkGetPhysicalDeviceMemoryProperties;
    static PFN_vkCreateDevice vkCreateDevice;
    static PFN_vkDestroyDevice vkDestroyDevice;
    static PFN_vkGetDeviceQueue vkGetDeviceQueue;
    static PFN_vkCreateSwapchainKHR vkCreateSwapchainKHR;
    static PFN_vkDestroySwapchainKHR vkDestroySwapchainKHR;
    static PFN_vkGetSwapchainImagesKHR vkGetSwapchainImagesKHR;
    static PFN_vkAcquireNextImageKHR vkAcquireNextImageKHR;
    static PFN_vkQueuePresentKHR vkQueuePresentKHR;
    static PFN_vkCreateImageView vkCreateImageView;
    static PFN_vkDestroyImageView vkDestroyImageView;
    static PFN_vkCreateImage vkCreateImage;
    static PFN_vkDestroyImage vkDestroyImage;
    static PFN_vkAllocateMemory vkAllocateMemory;
    static PFN_vkFreeMemory vkFreeMemory;
    static PFN_vkBindImageMemory vkBindImageMemory;
    static PFN_vkCreateBuffer vkCreateBuffer;
    static PFN_vkDestroyBuffer vkDestroyBuffer;
    static PFN_vkBindBufferMemory vkBindBufferMemory;
    static PFN_vkCreateCommandPool vkCreateCommandPool;
    static PFN_vkDestroyCommandPool vkDestroyCommandPool;
    static PFN_vkAllocateCommandBuffers vkAllocateCommandBuffers;
    static PFN_vkFreeCommandBuffers vkFreeCommandBuffers;
    static PFN_vkBeginCommandBuffer vkBeginCommandBuffer;
    static PFN_vkEndCommandBuffer vkEndCommandBuffer;
    static PFN_vkCmdBeginRenderPass vkCmdBeginRenderPass;
    static PFN_vkCmdEndRenderPass vkCmdEndRenderPass;
    static PFN_vkCmdBindPipeline vkCmdBindPipeline;
    static PFN_vkCmdBindVertexBuffers vkCmdBindVertexBuffers;
    static PFN_vkCmdBindIndexBuffer vkCmdBindIndexBuffer;
    static PFN_vkCmdBindDescriptorSets vkCmdBindDescriptorSets;
    static PFN_vkCmdSetViewport vkCmdSetViewport;
    static PFN_vkCmdSetScissor vkCmdSetScissor;
    static PFN_vkCmdDrawIndexed vkCmdDrawIndexed;
    static PFN_vkCmdDraw vkCmdDraw;
    static PFN_vkCreateGraphicsPipelines vkCreateGraphicsPipelines;
    static PFN_vkDestroyPipeline vkDestroyPipeline;
    static PFN_vkCreatePipelineLayout vkCreatePipelineLayout;
    static PFN_vkDestroyPipelineLayout vkDestroyPipelineLayout;
    static PFN_vkCreateShaderModule vkCreateShaderModule;
    static PFN_vkDestroyShaderModule vkDestroyShaderModule;
    static PFN_vkCreateRenderPass vkCreateRenderPass;
    static PFN_vkDestroyRenderPass vkDestroyRenderPass;
    static PFN_vkCreateFramebuffer vkCreateFramebuffer;
    static PFN_vkDestroyFramebuffer vkDestroyFramebuffer;
    static PFN_vkCreateSemaphore vkCreateSemaphore;
    static PFN_vkDestroySemaphore vkDestroySemaphore;
    static PFN_vkCreateFence vkCreateFence;
    static PFN_vkDestroyFence vkDestroyFence;
    static PFN_vkWaitForFences vkWaitForFences;
    static PFN_vkResetFences vkResetFences;
    static PFN_vkQueueSubmit vkQueueSubmit;
    static PFN_vkQueueWaitIdle vkQueueWaitIdle;
    static PFN_vkDeviceWaitIdle vkDeviceWaitIdle;
    static PFN_vkCreateDescriptorSetLayout vkCreateDescriptorSetLayout;
    static PFN_vkDestroyDescriptorSetLayout vkDestroyDescriptorSetLayout;
    static PFN_vkCreateDescriptorPool vkCreateDescriptorPool;
    static PFN_vkDestroyDescriptorPool vkDestroyDescriptorPool;
    static PFN_vkAllocateDescriptorSets vkAllocateDescriptorSets;
    static PFN_vkFreeDescriptorSets vkFreeDescriptorSets;
    static PFN_vkUpdateDescriptorSets vkUpdateDescriptorSets;
    static PFN_vkCreateSampler vkCreateSampler;
    static PFN_vkDestroySampler vkDestroySampler;
    static PFN_vkCmdPipelineBarrier vkCmdPipelineBarrier;
    static PFN_vkGetDeviceProcAddr vkGetDeviceProcAddr;
    static PFN_vkCreateDebugUtilsMessengerEXT vkCreateDebugUtilsMessengerEXT;
    static PFN_vkDestroyDebugUtilsMessengerEXT vkDestroyDebugUtilsMessengerEXT;
    static PFN_vkGetPhysicalDeviceSurfaceSupportKHR vkGetPhysicalDeviceSurfaceSupportKHR;
    static PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR vkGetPhysicalDeviceSurfaceCapabilitiesKHR;
    static PFN_vkGetPhysicalDeviceSurfaceFormatsKHR vkGetPhysicalDeviceSurfaceFormatsKHR;
    static PFN_vkGetPhysicalDeviceSurfacePresentModesKHR vkGetPhysicalDeviceSurfacePresentModesKHR;
    static PFN_vkDestroySurfaceKHR vkDestroySurfaceKHR;
    static PFN_vkUnmapMemory vkUnmapMemory;
    static PFN_vkResetCommandBuffer vkResetCommandBuffer;
    static PFN_vkGetBufferMemoryRequirements vkGetBufferMemoryRequirements;
    static PFN_vkGetImageMemoryRequirements vkGetImageMemoryRequirements;
    static PFN_vkMapMemory vkMapMemory;
};

// === Vulkan Instance ===
class VulkanInstance : public RHIInstance {
public:
    VulkanInstance();
    ~VulkanInstance() override;

    Result<void> init(const RHIInstanceDesc& desc) override;
    void shutdown() override;
    bool is_initialized() const override { return initialized_; }
    RHIBackend backend() const override { return RHIBackend::Vulkan; }

    Result<void> enumerate_physical_devices() override;
    uint32_t physical_device_count() const override;
    Result<void> create_device(uint32_t physical_device_index, RHIDevice** device) override;

    VkInstance vk_instance() const { return vk_instance_; }
    VkDebugUtilsMessengerEXT debug_messenger() const { return debug_messenger_; }
    const std::vector<VkPhysicalDevice>& physical_devices() const { return physical_devices_; }

private:
    bool initialized_ = false;
    VkInstance vk_instance_ = VK_NULL_HANDLE;
    VkDebugUtilsMessengerEXT debug_messenger_ = VK_NULL_HANDLE;
    std::vector<VkPhysicalDevice> physical_devices_;
    RHIInstanceDesc desc_;
};

// Forward declaration
class VulkanQueue;

// === Vulkan Device ===
class VulkanDevice : public RHIDevice {
public:
    VulkanDevice();
    ~VulkanDevice() override;

    Result<void> init(RHIInstance* instance, uint32_t physical_device_index) override;
    void shutdown() override;
    bool is_initialized() const override { return initialized_; }

    RHIQueue* graphics_queue() const override;
    RHIQueue* present_queue() const override;
    uint32_t graphics_queue_family_index() const override { return graphics_queue_family_; }
    uint32_t present_queue_family_index() const override { return present_queue_family_; }

    Result<void> create_buffer(const RHIBufferDesc& desc, RHIBuffer** buffer) override;
    Result<void> destroy_buffer(RHIBuffer* buffer) override;
    Result<void> upload_buffer(RHIBuffer* buffer, const void* data, uint64_t size, uint64_t offset = 0) override;

    Result<void> create_texture(const RHITextureDesc& desc, RHITexture** texture) override;
    Result<void> destroy_texture(RHITexture* texture) override;

    Result<void> create_shader_module(const RHIShaderDesc& desc, RHIShaderModule** module) override;
    Result<void> destroy_shader_module(RHIShaderModule* module) override;

    Result<void> create_pipeline_layout(RHIDescriptorSetLayout** layout) override;
    Result<void> destroy_pipeline_layout(RHIPipelineLayout* layout) override;

    Result<void> create_graphics_pipeline(const RHIGraphicsPipelineDesc& desc,
                                           RHIPipelineLayout* layout,
                                           RHIRenderPass* render_pass,
                                           RHIGraphicsPipeline** pipeline) override;
    Result<void> destroy_graphics_pipeline(RHIGraphicsPipeline* pipeline) override;

    Result<void> create_render_pass(RHIRenderPass** render_pass) override;
    Result<void> destroy_render_pass(RHIRenderPass* render_pass) override;

    Result<void> create_framebuffer(RHIFramebuffer** framebuffer) override;
    Result<void> destroy_framebuffer(RHIFramebuffer* framebuffer) override;

    Result<void> create_command_buffer(RHICommandBuffer** cmd_buffer) override;
    Result<void> destroy_command_buffer(RHICommandBuffer* cmd_buffer) override;

    Result<void> create_descriptor_set_layout(RHIDescriptorSetLayout** layout) override;
    Result<void> destroy_descriptor_set_layout(RHIDescriptorSetLayout* layout) override;

    Result<void> create_descriptor_pool(RHIDescriptorPool** pool) override;
    Result<void> destroy_descriptor_pool(RHIDescriptorPool* pool) override;

    Result<void> allocate_descriptor_sets(RHIDescriptorPool* pool,
                                           RHIDescriptorSetLayout* layout,
                                           RHIDescriptorSet** set) override;
    Result<void> free_descriptor_sets(RHIDescriptorPool* pool,
                                      RHIDescriptorSet* set) override;

    Result<void> create_sampler(RHISampler** sampler) override;
    Result<void> destroy_sampler(RHISampler* sampler) override;

    Result<void> create_swapchain(RHISurface* surface, const RHISwapchainDesc& desc,
                                   RHISwapchain** swapchain) override;
    Result<void> destroy_swapchain(RHISwapchain* swapchain) override;
    Result<void> acquire_next_image(RHISwapchain* swapchain, uint32_t* image_index) override;
    Result<void> present(RHISwapchain* swapchain, uint32_t image_index) override;

    std::string device_name() const override;
    uint32_t vendor_id() const override;
    uint32_t device_id() const override;
    RHIDeviceFeatures features() const override;

    Result<void> wait_idle() override;

    // Vulkan handles
    VkDevice vk_device() const { return vk_device_; }
    VkPhysicalDevice vk_physical_device() const { return vk_physical_device_; }
    VkQueue vk_graphics_queue() const { return vk_graphics_queue_; }
    VkQueue vk_present_queue() const { return vk_present_queue_; }
    VkCommandPool vk_command_pool() const { return vk_command_pool_; }
    uint32_t graphics_queue_family() const { return graphics_queue_family_; }

private:
    bool initialized_ = false;
    VulkanInstance* instance_ = nullptr;
    VkPhysicalDevice vk_physical_device_ = VK_NULL_HANDLE;
    VkDevice vk_device_ = VK_NULL_HANDLE;
    VkQueue vk_graphics_queue_ = VK_NULL_HANDLE;
    VkQueue vk_present_queue_ = VK_NULL_HANDLE;
    VulkanQueue* graphics_queue_ = nullptr;
    VulkanQueue* present_queue_ = nullptr;
    VkCommandPool vk_command_pool_ = VK_NULL_HANDLE;
    uint32_t graphics_queue_family_ = UINT32_MAX;
    uint32_t present_queue_family_ = UINT32_MAX;
    VkPhysicalDeviceProperties device_properties_{};
    VkPhysicalDeviceFeatures device_features_{};
    VkPhysicalDeviceMemoryProperties device_memory_properties_{};
};

// === Vulkan Queue ===
class VulkanQueue : public RHIQueue {
public:
    VulkanQueue(VkQueue queue, VkDevice device);
    ~VulkanQueue() override = default;

    Result<void> submit(RHICommandBuffer* cmd_buffer) override;
    // Vulkan-specific submit with synchronization
    Result<void> submit(RHICommandBuffer* cmd_buffer,
                         VkSemaphore wait_semaphore,
                         VkSemaphore signal_semaphore,
                         VkFence fence);
    Result<void> wait_idle() override;

private:
    VkQueue vk_queue_ = VK_NULL_HANDLE;
    VkDevice vk_device_ = VK_NULL_HANDLE;
};

// === Vulkan Buffer ===
class VulkanBuffer : public RHIBuffer {
public:
    VulkanBuffer();
    ~VulkanBuffer();

    void init(VkBuffer buffer, VkDeviceMemory memory, uint64_t size);
    void cleanup(VkDevice device);

    VkBuffer vk_buffer() const { return vk_buffer_; }
    VkDeviceMemory vk_memory() const { return vk_memory_; }
    uint64_t size() const { return size_; }

private:
    VkBuffer vk_buffer_ = VK_NULL_HANDLE;
    VkDeviceMemory vk_memory_ = VK_NULL_HANDLE;
    uint64_t size_ = 0;
};

// === Vulkan Texture ===
class VulkanTexture : public RHITexture {
public:
    VulkanTexture();
    ~VulkanTexture();

    void init(VkImage image, VkDeviceMemory memory, VkImageView view,
              RHIFormat format, RHIExtent3D extent);
    void cleanup(VkDevice device);

    VkImage vk_image() const { return vk_image_; }
    VkDeviceMemory vk_memory() const { return vk_memory_; }
    VkImageView vk_view() const { return vk_view_; }
    RHIFormat format() const { return format_; }
    RHIExtent3D extent() const { return extent_; }

private:
    VkImage vk_image_ = VK_NULL_HANDLE;
    VkDeviceMemory vk_memory_ = VK_NULL_HANDLE;
    VkImageView vk_view_ = VK_NULL_HANDLE;
    RHIFormat format_ = RHIFormat::Undefined;
    RHIExtent3D extent_{};
};

// === Vulkan Shader Module ===
class VulkanShaderModule : public RHIShaderModule {
public:
    VulkanShaderModule();
    ~VulkanShaderModule();

    void init(VkShaderModule module, RHIShaderStage stage, std::string entry_point);
    void cleanup(VkDevice device);

    VkShaderModule vk_module() const { return vk_module_; }
    RHIShaderStage stage() const { return stage_; }
    const std::string& entry_point() const { return entry_point_; }

private:
    VkShaderModule vk_module_ = VK_NULL_HANDLE;
    RHIShaderStage stage_ = RHIShaderStage::Vertex;
    std::string entry_point_;
};

// === Vulkan Pipeline Layout ===
class VulkanPipelineLayout : public RHIPipelineLayout {
public:
    VulkanPipelineLayout();
    ~VulkanPipelineLayout();

    void init(VkPipelineLayout layout);
    void cleanup(VkDevice device);

    VkPipelineLayout vk_layout() const { return vk_layout_; }

private:
    VkPipelineLayout vk_layout_ = VK_NULL_HANDLE;
};

// === Vulkan Graphics Pipeline ===
class VulkanGraphicsPipeline : public RHIGraphicsPipeline {
public:
    VulkanGraphicsPipeline();
    ~VulkanGraphicsPipeline();

    void init(VkPipeline pipeline);
    void cleanup(VkDevice device);

    VkPipeline vk_pipeline() const { return vk_pipeline_; }

private:
    VkPipeline vk_pipeline_ = VK_NULL_HANDLE;
};

// === Vulkan Render Pass ===
class VulkanRenderPass : public RHIRenderPass {
public:
    VulkanRenderPass();
    ~VulkanRenderPass();

    void init(VkRenderPass render_pass);
    void cleanup(VkDevice device);

    VkRenderPass vk_render_pass() const { return vk_render_pass_; }

private:
    VkRenderPass vk_render_pass_ = VK_NULL_HANDLE;
};

// === Vulkan Framebuffer ===
class VulkanFramebuffer : public RHIFramebuffer {
public:
    VulkanFramebuffer();
    ~VulkanFramebuffer();

    void init(VkFramebuffer framebuffer);
    void cleanup(VkDevice device);

    VkFramebuffer vk_framebuffer() const { return vk_framebuffer_; }

private:
    VkFramebuffer vk_framebuffer_ = VK_NULL_HANDLE;
};

// === Vulkan Command Buffer ===
class VulkanCommandBuffer : public RHICommandBuffer {
public:
    VulkanCommandBuffer();
    ~VulkanCommandBuffer();

    void init(VkCommandBuffer cmd_buffer, VkDevice device, VkCommandPool pool);
    void cleanup(VkDevice device);

    Result<void> begin() override;
    Result<void> end() override;
    Result<void> reset() override;
    Result<void> begin_render_pass(RHIRenderPass* render_pass,
                                    RHIFramebuffer* framebuffer,
                                    const RHIExtent2D& render_area,
                                    const std::vector<RHIColor>& clear_colors,
                                    float clear_depth,
                                    uint8_t clear_stencil) override;
    Result<void> end_render_pass() override;
    Result<void> bind_pipeline(RHIGraphicsPipeline* pipeline) override;
    Result<void> bind_vertex_buffer(uint32_t binding, RHIBuffer* buffer, uint64_t offset) override;
    Result<void> bind_index_buffer(RHIBuffer* buffer, RHIFormat format) override;
    Result<void> bind_descriptor_set(RHIPipelineLayout* layout,
                                      RHIDescriptorSet* set,
                                      uint32_t first_set,
                                      const std::vector<uint32_t>& dynamic_offsets) override;
    Result<void> set_viewport(const RHIViewport& viewport) override;
    Result<void> set_scissor(const RHIScissor& scissor) override;
    Result<void> draw_indexed(uint32_t index_count, uint32_t instance_count,
                               uint32_t first_index, uint32_t vertex_offset,
                               uint32_t first_instance) override;
    Result<void> draw(uint32_t vertex_count, uint32_t instance_count,
                       uint32_t first_vertex, uint32_t first_instance) override;
    Result<void> buffer_memory_barrier(RHIBuffer* buffer,
                                        uint32_t src_access_mask,
                                        uint32_t dst_access_mask,
                                        uint32_t src_stage,
                                        uint32_t dst_stage) override;
    Result<void> image_memory_barrier(RHITexture* texture,
                                       uint32_t src_access_mask,
                                       uint32_t dst_access_mask,
                                       uint32_t src_stage,
                                       uint32_t dst_stage) override;

    VkCommandBuffer vk_cmd_buffer() const { return vk_cmd_buffer_; }

private:
    VkCommandBuffer vk_cmd_buffer_ = VK_NULL_HANDLE;
    VkDevice vk_device_ = VK_NULL_HANDLE;
    VkCommandPool vk_command_pool_ = VK_NULL_HANDLE;
    bool recording_ = false;
    bool in_render_pass_ = false;
};

// === Vulkan Descriptor Set Layout ===
class VulkanDescriptorSetLayout : public RHIDescriptorSetLayout {
public:
    VulkanDescriptorSetLayout();
    ~VulkanDescriptorSetLayout();

    void init(VkDescriptorSetLayout layout);
    void cleanup(VkDevice device);

    VkDescriptorSetLayout vk_layout() const { return vk_layout_; }

private:
    VkDescriptorSetLayout vk_layout_ = VK_NULL_HANDLE;
};

// === Vulkan Descriptor Pool ===
class VulkanDescriptorPool : public RHIDescriptorPool {
public:
    VulkanDescriptorPool();
    ~VulkanDescriptorPool();

    void init(VkDescriptorPool pool);
    void cleanup(VkDevice device);

    VkDescriptorPool vk_pool() const { return vk_pool_; }

private:
    VkDescriptorPool vk_pool_ = VK_NULL_HANDLE;
};

// === Vulkan Descriptor Set ===
class VulkanDescriptorSet : public RHIDescriptorSet {
public:
    VulkanDescriptorSet();
    ~VulkanDescriptorSet();

    void init(VkDescriptorSet set);
    void cleanup(VkDevice device);

    VkDescriptorSet vk_set() const { return vk_set_; }

private:
    VkDescriptorSet vk_set_ = VK_NULL_HANDLE;
};

// === Vulkan Sampler ===
class VulkanSampler : public RHISampler {
public:
    VulkanSampler();
    ~VulkanSampler();

    void init(VkSampler sampler);
    void cleanup(VkDevice device);

    VkSampler vk_sampler() const { return vk_sampler_; }

private:
    VkSampler vk_sampler_ = VK_NULL_HANDLE;
};

// === Vulkan Swapchain ===
class VulkanSwapchain : public RHISwapchain {
public:
    VulkanSwapchain();
    ~VulkanSwapchain();

    Result<void> init(VkDevice device, VkPhysicalDevice physical_device,
                       VkSurfaceKHR surface, uint32_t width, uint32_t height,
                       VkQueue graphics_queue, VkQueue present_queue);
    void cleanup(VkDevice device);

    Result<void> acquire_next_image(uint32_t* image_index);
    Result<void> present(uint32_t image_index);

    VkSwapchainKHR vk_swapchain() const { return vk_swapchain_; }
    const std::vector<VkImage>& vk_images() const { return vk_images_; }
    const std::vector<VkImageView>& vk_image_views() const { return vk_image_views_; }
    VkFormat vk_format() const { return vk_format_; }
    VkExtent2D vk_extent() const { return vk_extent_; }
    uint32_t image_count() const { return static_cast<uint32_t>(vk_images_.size()); }

    // Framebuffer management
    Result<void> create_framebuffers(VkRenderPass render_pass);
    RHIFramebuffer* get_framebuffer(uint32_t index) const;
    void destroy_framebuffers(VkDevice device);

    // Synchronization accessors
    VkSemaphore image_available_semaphore() const { return vk_image_available_semaphore_; }
    VkSemaphore render_finished_semaphore() const { return vk_render_finished_semaphore_; }
    VkFence in_flight_fence() const { return vk_in_flight_fence_; }

private:
    VkDevice vk_device_ = VK_NULL_HANDLE;
    VkSwapchainKHR vk_swapchain_ = VK_NULL_HANDLE;
    VkFormat vk_format_ = VK_FORMAT_UNDEFINED;
    VkExtent2D vk_extent_{};
    std::vector<VkImage> vk_images_;
    std::vector<VkImageView> vk_image_views_;
    std::vector<VulkanFramebuffer*> framebuffers_;
    VkQueue vk_graphics_queue_ = VK_NULL_HANDLE;
    VkQueue vk_present_queue_ = VK_NULL_HANDLE;
    VkSemaphore vk_image_available_semaphore_ = VK_NULL_HANDLE;
    VkSemaphore vk_render_finished_semaphore_ = VK_NULL_HANDLE;
    VkFence vk_in_flight_fence_ = VK_NULL_HANDLE;
};

// === Vulkan Surface ===
class VulkanSurface : public RHISurface {
    friend class VulkanWindow;
public:
    VulkanSurface();
    ~VulkanSurface() override;

    Result<void> init(RHIInstance* instance, RHIWindow* window) override;
    void destroy() override;
    bool is_initialized() const override { return initialized_; }

    VkSurfaceKHR vk_surface() const { return vk_surface_; }

private:
    bool initialized_ = false;
    VkInstance vk_instance_ = VK_NULL_HANDLE;
    VkSurfaceKHR vk_surface_ = VK_NULL_HANDLE;
};

// === Vulkan Window (minimal, for headless/CI) ===
class VulkanWindow : public RHIWindow {
public:
    VulkanWindow();
    ~VulkanWindow() override;

    Result<void> create(const RHIWindowDesc& desc) override;
    void destroy() override;
    void* native_handle() const override { return nullptr; }
    uint32_t width() const override { return width_; }
    uint32_t height() const override { return height_; }
    bool should_close() const override { return should_close_; }
    void poll_events() override {}
    void* get_instance_extension_names(std::vector<const char*>& extensions) override;
    Result<void> create_surface(RHIInstance* instance, RHISurface** surface) override;

private:
    RHIWindowDesc desc_;
    uint32_t width_ = 0;
    uint32_t height_ = 0;
    bool should_close_ = false;
};

#endif // REALITY_HAS_VULKAN

} // namespace reality