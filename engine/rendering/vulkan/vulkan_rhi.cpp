#include "vulkan/vulkan_rhi.h"
#include "core/logging.h"
#include "core/error.h"

#ifdef REALITY_HAS_VULKAN

#define VMA_IMPLEMENTATION

#include <algorithm>
#include <cstring>
#include <set>
#include <iostream>

namespace reality {

// === Vulkan Function Loader Static Members ===
PFN_vkCreateInstance VulkanFunctionLoader::vkCreateInstance = nullptr;
PFN_vkDestroyInstance VulkanFunctionLoader::vkDestroyInstance = nullptr;
PFN_vkEnumeratePhysicalDevices VulkanFunctionLoader::vkEnumeratePhysicalDevices = nullptr;
PFN_vkGetPhysicalDeviceProperties VulkanFunctionLoader::vkGetPhysicalDeviceProperties = nullptr;
PFN_vkGetPhysicalDeviceFeatures VulkanFunctionLoader::vkGetPhysicalDeviceFeatures = nullptr;
PFN_vkGetPhysicalDeviceQueueFamilyProperties VulkanFunctionLoader::vkGetPhysicalDeviceQueueFamilyProperties = nullptr;
PFN_vkGetPhysicalDeviceMemoryProperties VulkanFunctionLoader::vkGetPhysicalDeviceMemoryProperties = nullptr;
PFN_vkCreateDevice VulkanFunctionLoader::vkCreateDevice = nullptr;
PFN_vkDestroyDevice VulkanFunctionLoader::vkDestroyDevice = nullptr;
PFN_vkGetDeviceQueue VulkanFunctionLoader::vkGetDeviceQueue = nullptr;
PFN_vkCreateSwapchainKHR VulkanFunctionLoader::vkCreateSwapchainKHR = nullptr;
PFN_vkDestroySwapchainKHR VulkanFunctionLoader::vkDestroySwapchainKHR = nullptr;
PFN_vkGetSwapchainImagesKHR VulkanFunctionLoader::vkGetSwapchainImagesKHR = nullptr;
PFN_vkAcquireNextImageKHR VulkanFunctionLoader::vkAcquireNextImageKHR = nullptr;
PFN_vkQueuePresentKHR VulkanFunctionLoader::vkQueuePresentKHR = nullptr;
PFN_vkCreateImageView VulkanFunctionLoader::vkCreateImageView = nullptr;
PFN_vkDestroyImageView VulkanFunctionLoader::vkDestroyImageView = nullptr;
PFN_vkCreateImage VulkanFunctionLoader::vkCreateImage = nullptr;
PFN_vkDestroyImage VulkanFunctionLoader::vkDestroyImage = nullptr;
PFN_vkAllocateMemory VulkanFunctionLoader::vkAllocateMemory = nullptr;
PFN_vkFreeMemory VulkanFunctionLoader::vkFreeMemory = nullptr;
PFN_vkBindImageMemory VulkanFunctionLoader::vkBindImageMemory = nullptr;
PFN_vkCreateBuffer VulkanFunctionLoader::vkCreateBuffer = nullptr;
PFN_vkDestroyBuffer VulkanFunctionLoader::vkDestroyBuffer = nullptr;
PFN_vkBindBufferMemory VulkanFunctionLoader::vkBindBufferMemory = nullptr;
PFN_vkCreateCommandPool VulkanFunctionLoader::vkCreateCommandPool = nullptr;
PFN_vkDestroyCommandPool VulkanFunctionLoader::vkDestroyCommandPool = nullptr;
PFN_vkAllocateCommandBuffers VulkanFunctionLoader::vkAllocateCommandBuffers = nullptr;
PFN_vkFreeCommandBuffers VulkanFunctionLoader::vkFreeCommandBuffers = nullptr;
PFN_vkBeginCommandBuffer VulkanFunctionLoader::vkBeginCommandBuffer = nullptr;
PFN_vkEndCommandBuffer VulkanFunctionLoader::vkEndCommandBuffer = nullptr;
PFN_vkCmdBeginRenderPass VulkanFunctionLoader::vkCmdBeginRenderPass = nullptr;
PFN_vkCmdEndRenderPass VulkanFunctionLoader::vkCmdEndRenderPass = nullptr;
PFN_vkCmdBindPipeline VulkanFunctionLoader::vkCmdBindPipeline = nullptr;
PFN_vkCmdBindVertexBuffers VulkanFunctionLoader::vkCmdBindVertexBuffers = nullptr;
PFN_vkCmdBindIndexBuffer VulkanFunctionLoader::vkCmdBindIndexBuffer = nullptr;
PFN_vkCmdBindDescriptorSets VulkanFunctionLoader::vkCmdBindDescriptorSets = nullptr;
PFN_vkCmdSetViewport VulkanFunctionLoader::vkCmdSetViewport = nullptr;
PFN_vkCmdSetScissor VulkanFunctionLoader::vkCmdSetScissor = nullptr;
PFN_vkCmdDrawIndexed VulkanFunctionLoader::vkCmdDrawIndexed = nullptr;
PFN_vkCmdDraw VulkanFunctionLoader::vkCmdDraw = nullptr;
PFN_vkCreateGraphicsPipelines VulkanFunctionLoader::vkCreateGraphicsPipelines = nullptr;
PFN_vkDestroyPipeline VulkanFunctionLoader::vkDestroyPipeline = nullptr;
PFN_vkCreatePipelineLayout VulkanFunctionLoader::vkCreatePipelineLayout = nullptr;
PFN_vkDestroyPipelineLayout VulkanFunctionLoader::vkDestroyPipelineLayout = nullptr;
PFN_vkCreateShaderModule VulkanFunctionLoader::vkCreateShaderModule = nullptr;
PFN_vkDestroyShaderModule VulkanFunctionLoader::vkDestroyShaderModule = nullptr;
PFN_vkCreateRenderPass VulkanFunctionLoader::vkCreateRenderPass = nullptr;
PFN_vkDestroyRenderPass VulkanFunctionLoader::vkDestroyRenderPass = nullptr;
PFN_vkCreateFramebuffer VulkanFunctionLoader::vkCreateFramebuffer = nullptr;
PFN_vkDestroyFramebuffer VulkanFunctionLoader::vkDestroyFramebuffer = nullptr;
PFN_vkCreateSemaphore VulkanFunctionLoader::vkCreateSemaphore = nullptr;
PFN_vkDestroySemaphore VulkanFunctionLoader::vkDestroySemaphore = nullptr;
PFN_vkCreateFence VulkanFunctionLoader::vkCreateFence = nullptr;
PFN_vkDestroyFence VulkanFunctionLoader::vkDestroyFence = nullptr;
PFN_vkWaitForFences VulkanFunctionLoader::vkWaitForFences = nullptr;
PFN_vkResetFences VulkanFunctionLoader::vkResetFences = nullptr;
PFN_vkQueueSubmit VulkanFunctionLoader::vkQueueSubmit = nullptr;
PFN_vkQueueWaitIdle VulkanFunctionLoader::vkQueueWaitIdle = nullptr;
PFN_vkDeviceWaitIdle VulkanFunctionLoader::vkDeviceWaitIdle = nullptr;
PFN_vkCreateDescriptorSetLayout VulkanFunctionLoader::vkCreateDescriptorSetLayout = nullptr;
PFN_vkDestroyDescriptorSetLayout VulkanFunctionLoader::vkDestroyDescriptorSetLayout = nullptr;
PFN_vkCreateDescriptorPool VulkanFunctionLoader::vkCreateDescriptorPool = nullptr;
PFN_vkDestroyDescriptorPool VulkanFunctionLoader::vkDestroyDescriptorPool = nullptr;
PFN_vkAllocateDescriptorSets VulkanFunctionLoader::vkAllocateDescriptorSets = nullptr;
PFN_vkFreeDescriptorSets VulkanFunctionLoader::vkFreeDescriptorSets = nullptr;
PFN_vkUpdateDescriptorSets VulkanFunctionLoader::vkUpdateDescriptorSets = nullptr;
PFN_vkCreateSampler VulkanFunctionLoader::vkCreateSampler = nullptr;
PFN_vkDestroySampler VulkanFunctionLoader::vkDestroySampler = nullptr;
PFN_vkCmdPipelineBarrier VulkanFunctionLoader::vkCmdPipelineBarrier = nullptr;
PFN_vkGetDeviceProcAddr VulkanFunctionLoader::vkGetDeviceProcAddr = nullptr;
PFN_vkGetInstanceProcAddr VulkanFunctionLoader::vkGetInstanceProcAddr_fn = nullptr;
PFN_vkGetDeviceProcAddr VulkanFunctionLoader::vkGetDeviceProcAddr_fn = nullptr;
PFN_vkCreateDebugUtilsMessengerEXT VulkanFunctionLoader::vkCreateDebugUtilsMessengerEXT = nullptr;
PFN_vkDestroyDebugUtilsMessengerEXT VulkanFunctionLoader::vkDestroyDebugUtilsMessengerEXT = nullptr;
PFN_vkGetPhysicalDeviceSurfaceSupportKHR VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceSupportKHR = nullptr;
PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceCapabilitiesKHR = nullptr;
PFN_vkGetPhysicalDeviceSurfaceFormatsKHR VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceFormatsKHR = nullptr;
PFN_vkGetPhysicalDeviceSurfacePresentModesKHR VulkanFunctionLoader::vkGetPhysicalDeviceSurfacePresentModesKHR = nullptr;
PFN_vkDestroySurfaceKHR VulkanFunctionLoader::vkDestroySurfaceKHR = nullptr;
PFN_vkUnmapMemory VulkanFunctionLoader::vkUnmapMemory = nullptr;
PFN_vkResetCommandBuffer VulkanFunctionLoader::vkResetCommandBuffer = nullptr;
PFN_vkGetBufferMemoryRequirements VulkanFunctionLoader::vkGetBufferMemoryRequirements = nullptr;
PFN_vkGetImageMemoryRequirements VulkanFunctionLoader::vkGetImageMemoryRequirements = nullptr;
PFN_vkMapMemory VulkanFunctionLoader::vkMapMemory = nullptr;

PFN_vkGetInstanceProcAddr VulkanFunctionLoader::load_get_instance_proc_addr() {
    // Try to load libvulkan.so dynamically
    #ifdef _WIN32
        HMODULE lib = LoadLibraryA("vulkan-1.dll");
    #elif defined(__APPLE__)
        void* lib = dlopen("libvulkan.1.dylib", RTLD_NOW | RTLD_LOCAL);
    #else
        void* lib = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
        if (!lib) lib = dlopen("libvulkan.so", RTLD_NOW | RTLD_LOCAL);
    #endif
    if (!lib) {
        REALITY_LOG(WARN, "Vulkan: Could not load libvulkan.so - Vulkan runtime unavailable");
        return nullptr;
    }
    #ifdef _WIN32
        auto proc = (PROC)GetProcAddress(lib, "vkGetInstanceProcAddr");
    #else
        auto proc = dlsym(lib, "vkGetInstanceProcAddr");
    #endif
    return reinterpret_cast<PFN_vkGetInstanceProcAddr>(proc);
}

// Helper: check if a layer is available
static bool layer_available(const std::vector<VkLayerProperties>& layers, const char* name) {
    for (const auto& lp : layers) {
        if (strcmp(lp.layerName, name) == 0) return true;
    }
    return false;
}

// Helper: check if an extension is available
static bool extension_available(const std::vector<VkExtensionProperties>& exts, const char* name) {
    for (const auto& ep : exts) {
        if (strcmp(ep.extensionName, name) == 0) return true;
    }
    return false;
}

// === Vulkan Instance ===

VulkanInstance::VulkanInstance() = default;

VulkanInstance::~VulkanInstance() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> VulkanInstance::init(const RHIInstanceDesc& desc) {
    desc_ = desc;

    // Load vkGetInstanceProcAddr
    VulkanFunctionLoader::vkGetInstanceProcAddr_fn = VulkanFunctionLoader::load_get_instance_proc_addr();
    if (!VulkanFunctionLoader::vkGetInstanceProcAddr_fn) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to load vkGetInstanceProcAddr - is libvulkan installed?",
            "vulkan_rhi.cpp:VulkanInstance::init"});
    }

    // Load global-level Vulkan functions (required before instance creation).
    // These are obtained via vkGetInstanceProcAddr(nullptr, ...).
    auto load_global_func = [](const char* name) -> PFN_vkVoidFunction {
        return VulkanFunctionLoader::vkGetInstanceProcAddr_fn(nullptr, name);
    };

    PFN_vkEnumerateInstanceLayerProperties vkEnumerateInstanceLayerProperties_fn =
        reinterpret_cast<PFN_vkEnumerateInstanceLayerProperties>(load_global_func("vkEnumerateInstanceLayerProperties"));
    PFN_vkEnumerateInstanceExtensionProperties vkEnumerateInstanceExtensionProperties_fn =
        reinterpret_cast<PFN_vkEnumerateInstanceExtensionProperties>(load_global_func("vkEnumerateInstanceExtensionProperties"));
    PFN_vkCreateInstance vkCreateInstance_fn =
        reinterpret_cast<PFN_vkCreateInstance>(load_global_func("vkCreateInstance"));

    if (!vkEnumerateInstanceLayerProperties_fn || !vkEnumerateInstanceExtensionProperties_fn || !vkCreateInstance_fn) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to load global-level Vulkan functions",
            "vulkan_rhi.cpp:VulkanInstance::init"});
    }

    // Store global function pointers in the loader for reuse
    VulkanFunctionLoader::vkCreateInstance = vkCreateInstance_fn;

    // Enumerate instance layers
    uint32_t layer_count = 0;
    vkEnumerateInstanceLayerProperties_fn(&layer_count, nullptr);
    std::vector<VkLayerProperties> available_layers(layer_count);
    if (layer_count > 0) {
        vkEnumerateInstanceLayerProperties_fn(&layer_count, available_layers.data());
    }

    // Enumerate instance extensions
    uint32_t ext_count = 0;
    vkEnumerateInstanceExtensionProperties_fn(nullptr, &ext_count, nullptr);
    std::vector<VkExtensionProperties> available_extensions(ext_count);
    if (ext_count > 0) {
        vkEnumerateInstanceExtensionProperties_fn(nullptr, &ext_count, available_extensions.data());
    }

    // Determine validation layers
    std::vector<const char*> enabled_layers;
    if (desc.enable_validation_layers) {
        const char* validation_layers[] = {
            "VK_LAYER_KHRONOS_validation",
        };
        for (const char* layer : validation_layers) {
            if (layer_available(available_layers, layer)) {
                enabled_layers.push_back(layer);
                REALITY_LOG(INFO, "Vulkan: enabled validation layer: " + std::string(layer));
            } else {
                REALITY_LOG(WARN, "Vulkan: validation layer not available: " + std::string(layer));
            }
        }
    }

    // Determine required extensions
    std::vector<const char*> enabled_extensions = {
        VK_KHR_SURFACE_EXTENSION_NAME,
    };

    // Add debug utils extension if validation enabled
    if (desc.enable_validation_layers) {
        if (extension_available(available_extensions, VK_EXT_DEBUG_UTILS_EXTENSION_NAME)) {
            enabled_extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
        }
    }

    // Create Vulkan instance
    VkApplicationInfo app_info{};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = desc.application_name.c_str();
    app_info.applicationVersion = desc.application_version;
    app_info.pEngineName = desc.engine_name.c_str();
    app_info.engineVersion = desc.engine_version;
    app_info.apiVersion = VK_API_VERSION_1_3;

    VkInstanceCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create_info.pApplicationInfo = &app_info;
    create_info.enabledLayerCount = static_cast<uint32_t>(enabled_layers.size());
    create_info.ppEnabledLayerNames = enabled_layers.data();
    create_info.enabledExtensionCount = static_cast<uint32_t>(enabled_extensions.size());
    create_info.ppEnabledExtensionNames = enabled_extensions.data();

    VkResult result = vkCreateInstance_fn(&create_info, nullptr, &vk_instance_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create instance: " + std::to_string(result),
            "vulkan_rhi.cpp:VulkanInstance::init"});
    }

    // Load instance-level function pointers
    #define LOAD_INSTANCE_FUNC(name) \
        VulkanFunctionLoader::name = VulkanFunctionLoader::load_instance<decltype(VulkanFunctionLoader::name)>(vk_instance_, #name);

    LOAD_INSTANCE_FUNC(vkDestroyInstance);
    LOAD_INSTANCE_FUNC(vkEnumeratePhysicalDevices);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceProperties);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceFeatures);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceQueueFamilyProperties);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceMemoryProperties);
    LOAD_INSTANCE_FUNC(vkCreateDevice);
    LOAD_INSTANCE_FUNC(vkDestroyDevice);
    LOAD_INSTANCE_FUNC(vkGetDeviceQueue);
    LOAD_INSTANCE_FUNC(vkCreateDebugUtilsMessengerEXT);
    LOAD_INSTANCE_FUNC(vkDestroyDebugUtilsMessengerEXT);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceSurfaceSupportKHR);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceSurfaceCapabilitiesKHR);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceSurfaceFormatsKHR);
    LOAD_INSTANCE_FUNC(vkGetPhysicalDeviceSurfacePresentModesKHR);
    LOAD_INSTANCE_FUNC(vkDestroySurfaceKHR);
    #undef LOAD_INSTANCE_FUNC

    // Create debug messenger if validation enabled
    if (desc.enable_validation_layers && vkCreateDebugUtilsMessengerEXT) {
        VkDebugUtilsMessengerCreateInfoEXT debug_create_info{};
        debug_create_info.sType = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT;
        debug_create_info.messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_VERBOSE_BIT_EXT |
                                            VK_DEBUG_UTILS_MESSAGE_SEVERITY_INFO_BIT_EXT |
                                            VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT |
                                            VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT;
        debug_create_info.messageType = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT |
                                        VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT |
                                        VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT;
        debug_create_info.pfnUserCallback = [](VkDebugUtilsMessageSeverityFlagBitsEXT,
                                               VkDebugUtilsMessageTypeFlagsEXT,
                                               const VkDebugUtilsMessengerCallbackDataEXT* pCallbackData,
                                               void*) -> VkBool32 {
            std::cerr << "[Vulkan Validation] " << pCallbackData->pMessage << std::endl;
            return VK_FALSE;
        };
        VulkanFunctionLoader::vkCreateDebugUtilsMessengerEXT(vk_instance_, &debug_create_info, nullptr, &debug_messenger_);
    }

    initialized_ = true;
    REALITY_LOG(INFO, "Vulkan: instance created successfully");
    return Result<void>();
}

void VulkanInstance::shutdown() {
    if (debug_messenger_ != VK_NULL_HANDLE && vkDestroyDebugUtilsMessengerEXT) {
        VulkanFunctionLoader::vkDestroyDebugUtilsMessengerEXT(vk_instance_, debug_messenger_, nullptr);
        debug_messenger_ = VK_NULL_HANDLE;
    }
    if (vk_instance_ != VK_NULL_HANDLE && vkDestroyInstance) {
        VulkanFunctionLoader::vkDestroyInstance(vk_instance_, nullptr);
        vk_instance_ = VK_NULL_HANDLE;
    }
    initialized_ = false;
}

Result<void> VulkanInstance::enumerate_physical_devices() {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan instance not initialized",
            "vulkan_rhi.cpp:VulkanInstance::enumerate_physical_devices"});
    }

    uint32_t device_count = 0;
    VkResult result = VulkanFunctionLoader::vkEnumeratePhysicalDevices(vk_instance_, &device_count, nullptr);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to enumerate physical devices",
            "vulkan_rhi.cpp:VulkanInstance::enumerate_physical_devices"});
    }

    physical_devices_.resize(device_count);
    if (device_count > 0) {
        result = VulkanFunctionLoader::vkEnumeratePhysicalDevices(vk_instance_, &device_count, physical_devices_.data());
        if (result != VK_SUCCESS) {
            return Result<void>(Error{ErrorCode::INIT_FAILED,
                "Vulkan: failed to get physical devices",
                "vulkan_rhi.cpp:VulkanInstance::enumerate_physical_devices"});
        }
    }

    REALITY_LOG(INFO, "Vulkan: found " + std::to_string(device_count) + " physical device(s)");
    return Result<void>();
}

uint32_t VulkanInstance::physical_device_count() const {
    return static_cast<uint32_t>(physical_devices_.size());
}

Result<void> VulkanInstance::create_device(uint32_t physical_device_index, RHIDevice** device) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan instance not initialized",
            "vulkan_rhi.cpp:VulkanInstance::create_device"});
    }
    if (physical_device_index >= physical_devices_.size()) {
        return Result<void>(Error{ErrorCode::INVALID_PARAMETER,
            "Vulkan: physical device index out of range",
            "vulkan_rhi.cpp:VulkanInstance::create_device"});
    }

    auto* vulkan_device = new VulkanDevice();
    auto result = vulkan_device->init(this, physical_device_index);
    if (!result.ok()) {
        delete vulkan_device;
        return result;
    }
    *device = vulkan_device;
    return Result<void>();
}

// === Vulkan Device ===

VulkanDevice::VulkanDevice() = default;

RHIQueue* VulkanDevice::graphics_queue() const {
    return graphics_queue_;
}

RHIQueue* VulkanDevice::present_queue() const {
    return present_queue_;
}

VulkanDevice::~VulkanDevice() {
    if (initialized_) {
        shutdown();
    }
}

Result<void> VulkanDevice::init(RHIInstance* instance, uint32_t physical_device_index) {
    instance_ = reinterpret_cast<VulkanInstance*>(instance);
    vk_physical_device_ = instance_->physical_devices()[physical_device_index];

    // Get device properties and features
    VulkanFunctionLoader::vkGetPhysicalDeviceProperties(vk_physical_device_, &device_properties_);
    VulkanFunctionLoader::vkGetPhysicalDeviceFeatures(vk_physical_device_, &device_features_);
    VulkanFunctionLoader::vkGetPhysicalDeviceMemoryProperties(vk_physical_device_, &device_memory_properties_);

    REALITY_LOG(INFO, "Vulkan: selected device: " + std::string(device_properties_.deviceName));

    // Find queue families
    uint32_t queue_family_count = 0;
    VulkanFunctionLoader::vkGetPhysicalDeviceQueueFamilyProperties(vk_physical_device_, &queue_family_count, nullptr);
    std::vector<VkQueueFamilyProperties> queue_families(queue_family_count);
    VulkanFunctionLoader::vkGetPhysicalDeviceQueueFamilyProperties(vk_physical_device_, &queue_family_count, queue_families.data());

    graphics_queue_family_ = UINT32_MAX;
    present_queue_family_ = UINT32_MAX;

    for (uint32_t i = 0; i < queue_family_count; i++) {
        if (queue_families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            graphics_queue_family_ = i;
            break;
        }
    }

    if (graphics_queue_family_ == UINT32_MAX) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: no graphics queue family found",
            "vulkan_rhi.cpp:VulkanDevice::init"});
    }

    // Use graphics queue family for presentation as well (common case)
    present_queue_family_ = graphics_queue_family_;

    // Create logical device
    std::vector<VkDeviceQueueCreateInfo> queue_create_infos;
    std::set<uint32_t> unique_queue_families = {graphics_queue_family_, present_queue_family_};

    float queue_priority = 1.0f;
    for (uint32_t queue_family : unique_queue_families) {
        VkDeviceQueueCreateInfo queue_create_info{};
        queue_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queue_create_info.queueFamilyIndex = queue_family;
        queue_create_info.queueCount = 1;
        queue_create_info.pQueuePriorities = &queue_priority;
        queue_create_infos.push_back(queue_create_info);
    }

    // Device features to enable
    VkPhysicalDeviceFeatures enabled_features{};
    enabled_features.samplerAnisotropy = device_features_.samplerAnisotropy;
    enabled_features.fillModeNonSolid = device_features_.fillModeNonSolid;

    // Device extensions
    std::vector<const char*> device_extensions = {
        VK_KHR_SWAPCHAIN_EXTENSION_NAME,
    };

    VkDeviceCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    create_info.pQueueCreateInfos = queue_create_infos.data();
    create_info.queueCreateInfoCount = static_cast<uint32_t>(queue_create_infos.size());
    create_info.pEnabledFeatures = &enabled_features;
    create_info.enabledExtensionCount = static_cast<uint32_t>(device_extensions.size());
    create_info.ppEnabledExtensionNames = device_extensions.data();

    VkResult result = VulkanFunctionLoader::vkCreateDevice(vk_physical_device_, &create_info, nullptr, &vk_device_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create logical device: " + std::to_string(result),
            "vulkan_rhi.cpp:VulkanDevice::init"});
    }

    // Load vkGetDeviceProcAddr (needed for load_device template)
    // vkGetInstanceProcAddr takes VkInstance, not VkDevice
    VulkanFunctionLoader::vkGetDeviceProcAddr_fn =
        reinterpret_cast<PFN_vkGetDeviceProcAddr>(
            VulkanFunctionLoader::vkGetInstanceProcAddr_fn(instance_->vk_instance(), "vkGetDeviceProcAddr"));
    if (!VulkanFunctionLoader::vkGetDeviceProcAddr_fn) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to load vkGetDeviceProcAddr",
            "vulkan_rhi.cpp:VulkanDevice::init"});
    }

    // Load device-level function pointers
    #define LOAD_DEVICE_FUNC(name) \
        VulkanFunctionLoader::name = VulkanFunctionLoader::load_device<decltype(VulkanFunctionLoader::name)>(vk_device_, #name);

    LOAD_DEVICE_FUNC(vkGetDeviceQueue);
    LOAD_DEVICE_FUNC(vkCreateSwapchainKHR);
    LOAD_DEVICE_FUNC(vkDestroySwapchainKHR);
    LOAD_DEVICE_FUNC(vkGetSwapchainImagesKHR);
    LOAD_DEVICE_FUNC(vkAcquireNextImageKHR);
    LOAD_DEVICE_FUNC(vkQueuePresentKHR);
    LOAD_DEVICE_FUNC(vkCreateImageView);
    LOAD_DEVICE_FUNC(vkDestroyImageView);
    LOAD_DEVICE_FUNC(vkCreateImage);
    LOAD_DEVICE_FUNC(vkDestroyImage);
    LOAD_DEVICE_FUNC(vkAllocateMemory);
    LOAD_DEVICE_FUNC(vkFreeMemory);
    LOAD_DEVICE_FUNC(vkBindImageMemory);
    LOAD_DEVICE_FUNC(vkCreateBuffer);
    LOAD_DEVICE_FUNC(vkDestroyBuffer);
    LOAD_DEVICE_FUNC(vkBindBufferMemory);
    LOAD_DEVICE_FUNC(vkCreateCommandPool);
    LOAD_DEVICE_FUNC(vkDestroyCommandPool);
    LOAD_DEVICE_FUNC(vkAllocateCommandBuffers);
    LOAD_DEVICE_FUNC(vkFreeCommandBuffers);
    LOAD_DEVICE_FUNC(vkBeginCommandBuffer);
    LOAD_DEVICE_FUNC(vkEndCommandBuffer);
    LOAD_DEVICE_FUNC(vkCmdBeginRenderPass);
    LOAD_DEVICE_FUNC(vkCmdEndRenderPass);
    LOAD_DEVICE_FUNC(vkCmdBindPipeline);
    LOAD_DEVICE_FUNC(vkCmdBindVertexBuffers);
    LOAD_DEVICE_FUNC(vkCmdBindIndexBuffer);
    LOAD_DEVICE_FUNC(vkCmdBindDescriptorSets);
    LOAD_DEVICE_FUNC(vkCmdSetViewport);
    LOAD_DEVICE_FUNC(vkCmdSetScissor);
    LOAD_DEVICE_FUNC(vkCmdDrawIndexed);
    LOAD_DEVICE_FUNC(vkCmdDraw);
    LOAD_DEVICE_FUNC(vkCreateGraphicsPipelines);
    LOAD_DEVICE_FUNC(vkDestroyPipeline);
    LOAD_DEVICE_FUNC(vkCreatePipelineLayout);
    LOAD_DEVICE_FUNC(vkDestroyPipelineLayout);
    LOAD_DEVICE_FUNC(vkCreateShaderModule);
    LOAD_DEVICE_FUNC(vkDestroyShaderModule);
    LOAD_DEVICE_FUNC(vkCreateRenderPass);
    LOAD_DEVICE_FUNC(vkDestroyRenderPass);
    LOAD_DEVICE_FUNC(vkCreateFramebuffer);
    LOAD_DEVICE_FUNC(vkDestroyFramebuffer);
    LOAD_DEVICE_FUNC(vkCreateSemaphore);
    LOAD_DEVICE_FUNC(vkDestroySemaphore);
    LOAD_DEVICE_FUNC(vkCreateFence);
    LOAD_DEVICE_FUNC(vkDestroyFence);
    LOAD_DEVICE_FUNC(vkWaitForFences);
    LOAD_DEVICE_FUNC(vkResetFences);
    LOAD_DEVICE_FUNC(vkQueueSubmit);
    LOAD_DEVICE_FUNC(vkQueueWaitIdle);
    LOAD_DEVICE_FUNC(vkDeviceWaitIdle);
    LOAD_DEVICE_FUNC(vkCreateDescriptorSetLayout);
    LOAD_DEVICE_FUNC(vkDestroyDescriptorSetLayout);
    LOAD_DEVICE_FUNC(vkCreateDescriptorPool);
    LOAD_DEVICE_FUNC(vkDestroyDescriptorPool);
    LOAD_DEVICE_FUNC(vkAllocateDescriptorSets);
    LOAD_DEVICE_FUNC(vkFreeDescriptorSets);
    LOAD_DEVICE_FUNC(vkUpdateDescriptorSets);
    LOAD_DEVICE_FUNC(vkCreateSampler);
    LOAD_DEVICE_FUNC(vkDestroySampler);
    LOAD_DEVICE_FUNC(vkCmdPipelineBarrier);
    LOAD_DEVICE_FUNC(vkGetDeviceProcAddr);
    #undef LOAD_DEVICE_FUNC

    // Get queues
    VulkanFunctionLoader::vkGetDeviceQueue(vk_device_, graphics_queue_family_, 0, &vk_graphics_queue_);
    VulkanFunctionLoader::vkGetDeviceQueue(vk_device_, present_queue_family_, 0, &vk_present_queue_);

    // Create command pool
    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.queueFamilyIndex = graphics_queue_family_;
    pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    result = VulkanFunctionLoader::vkCreateCommandPool(vk_device_, &pool_info, nullptr, &vk_command_pool_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create command pool",
            "vulkan_rhi.cpp:VulkanDevice::init"});
    }

    initialized_ = true;
    REALITY_LOG(INFO, "Vulkan: logical device created successfully");
    return Result<void>();
}

void VulkanDevice::shutdown() {
    if (vk_command_pool_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyCommandPool(vk_device_, vk_command_pool_, nullptr);
        vk_command_pool_ = VK_NULL_HANDLE;
    }
    if (vk_device_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyDevice(vk_device_, nullptr);
        vk_device_ = VK_NULL_HANDLE;
    }
    initialized_ = false;
}

// ... implementations for all other methods ...
// Buffer operations
Result<void> VulkanDevice::create_buffer(const RHIBufferDesc& desc, RHIBuffer** buffer) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_buffer"});
    }

    VkBufferUsageFlags usage = 0;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::VertexBuffer))
        usage |= VK_BUFFER_USAGE_VERTEX_BUFFER_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::IndexBuffer))
        usage |= VK_BUFFER_USAGE_INDEX_BUFFER_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::UniformBuffer))
        usage |= VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::StorageBuffer))
        usage |= VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::TransferSrc))
        usage |= VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIBufferUsage::TransferDst))
        usage |= VK_BUFFER_USAGE_TRANSFER_DST_BIT;

    VkBufferCreateInfo buffer_info{};
    buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer_info.size = desc.size;
    buffer_info.usage = usage;
    buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    VkBuffer vk_buffer = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateBuffer(vk_device_, &buffer_info, nullptr, &vk_buffer);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create buffer",
            "vulkan_rhi.cpp:VulkanDevice::create_buffer"});
    }

    // Allocate memory
    VkMemoryRequirements mem_requirements;
    VulkanFunctionLoader::vkGetBufferMemoryRequirements(vk_device_, vk_buffer, &mem_requirements);

    VkMemoryPropertyFlags props = 0;
    if (static_cast<uint32_t>(desc.properties) & static_cast<uint32_t>(RHIMemoryProperty::DeviceLocal))
        props |= VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
    if (static_cast<uint32_t>(desc.properties) & static_cast<uint32_t>(RHIMemoryProperty::HostVisible))
        props |= VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT;
    if (static_cast<uint32_t>(desc.properties) & static_cast<uint32_t>(RHIMemoryProperty::HostCoherent))
        props |= VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;

    uint32_t memory_type_index = UINT32_MAX;
    for (uint32_t i = 0; i < device_memory_properties_.memoryTypeCount; i++) {
        if ((mem_requirements.memoryTypeBits & (1 << i)) &&
            ((device_memory_properties_.memoryTypes[i].propertyFlags & props) == props)) {
            memory_type_index = i;
            break;
        }
    }

    if (memory_type_index == UINT32_MAX) {
        VulkanFunctionLoader::vkDestroyBuffer(vk_device_, vk_buffer, nullptr);
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: no suitable memory type for buffer",
            "vulkan_rhi.cpp:VulkanDevice::create_buffer"});
    }

    VkMemoryAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc_info.allocationSize = mem_requirements.size;
    alloc_info.memoryTypeIndex = memory_type_index;

    VkDeviceMemory memory = VK_NULL_HANDLE;
    result = VulkanFunctionLoader::vkAllocateMemory(vk_device_, &alloc_info, nullptr, &memory);
    if (result != VK_SUCCESS) {
        VulkanFunctionLoader::vkDestroyBuffer(vk_device_, vk_buffer, nullptr);
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to allocate buffer memory",
            "vulkan_rhi.cpp:VulkanDevice::create_buffer"});
    }

    VulkanFunctionLoader::vkBindBufferMemory(vk_device_, vk_buffer, memory, 0);

    auto* vulkan_buffer = new VulkanBuffer();
    vulkan_buffer->init(vk_buffer, memory, desc.size);
    *buffer = reinterpret_cast<RHIBuffer*>(vulkan_buffer);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_buffer(RHIBuffer* buffer) {
    if (!buffer) return Result<void>();
    auto* vk_buf = reinterpret_cast<VulkanBuffer*>(buffer);
    vk_buf->cleanup(vk_device_);
    delete vk_buf;
    return Result<void>();
}

Result<void> VulkanDevice::upload_buffer(RHIBuffer* buffer, const void* data, uint64_t size, uint64_t offset) {
    auto* vk_buf = reinterpret_cast<VulkanBuffer*>(buffer);
    void* mapped;
    VkResult result = VulkanFunctionLoader::vkMapMemory(vk_device_, vk_buf->vk_memory(), offset, size, 0, &mapped);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to map buffer memory",
            "vulkan_rhi.cpp:VulkanDevice::upload_buffer"});
    }
    memcpy(mapped, data, static_cast<size_t>(size));
    VulkanFunctionLoader::vkUnmapMemory(vk_device_, vk_buf->vk_memory());
    return Result<void>();
}

// Texture operations
Result<void> VulkanDevice::create_texture(const RHITextureDesc& desc, RHITexture** texture) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    VkFormat vk_format = VK_FORMAT_UNDEFINED;
    switch (desc.format) {
        case RHIFormat::R8G8B8A8_UNORM: vk_format = VK_FORMAT_R8G8B8A8_UNORM; break;
        case RHIFormat::B8G8R8A8_UNORM: vk_format = VK_FORMAT_B8G8R8A8_UNORM; break;
        case RHIFormat::R32G32B32A32_SFLOAT: vk_format = VK_FORMAT_R32G32B32A32_SFLOAT; break;
        case RHIFormat::R32G32B32_SFLOAT: vk_format = VK_FORMAT_R32G32B32_SFLOAT; break;
        case RHIFormat::R32G32_SFLOAT: vk_format = VK_FORMAT_R32G32_SFLOAT; break;
        case RHIFormat::D32_SFLOAT: vk_format = VK_FORMAT_D32_SFLOAT; break;
        case RHIFormat::D24_UNORM_S8_UINT: vk_format = VK_FORMAT_D24_UNORM_S8_UINT; break;
        case RHIFormat::R8G8B8A8_SRGB: vk_format = VK_FORMAT_R8G8B8A8_SRGB; break;
        case RHIFormat::B8G8R8A8_SRGB: vk_format = VK_FORMAT_B8G8R8A8_SRGB; break;
        default:
            return Result<void>(Error{ErrorCode::INVALID_PARAMETER,
                "Vulkan: unsupported texture format",
                "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    VkImageUsageFlags usage = 0;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIImageUsage::Sampled))
        usage |= VK_IMAGE_USAGE_SAMPLED_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIImageUsage::ColorAttachment))
        usage |= VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIImageUsage::DepthStencilAttachment))
        usage |= VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIImageUsage::TransferSrc))
        usage |= VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    if (static_cast<uint32_t>(desc.usage) & static_cast<uint32_t>(RHIImageUsage::TransferDst))
        usage |= VK_IMAGE_USAGE_TRANSFER_DST_BIT;

    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.extent.width = desc.extent.width;
    image_info.extent.height = desc.extent.height;
    image_info.extent.depth = desc.extent.depth;
    image_info.mipLevels = desc.mip_levels;
    image_info.arrayLayers = desc.array_layers;
    image_info.format = vk_format;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    image_info.usage = usage;
    image_info.samples = static_cast<VkSampleCountFlagBits>(desc.samples);
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    VkImage image = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateImage(vk_device_, &image_info, nullptr, &image);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create image",
            "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    VkMemoryRequirements mem_requirements;
    VulkanFunctionLoader::vkGetImageMemoryRequirements(vk_device_, image, &mem_requirements);

    VkMemoryPropertyFlags props = VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;
    uint32_t memory_type_index = UINT32_MAX;
    for (uint32_t i = 0; i < device_memory_properties_.memoryTypeCount; i++) {
        if ((mem_requirements.memoryTypeBits & (1 << i)) &&
            ((device_memory_properties_.memoryTypes[i].propertyFlags & props) == props)) {
            memory_type_index = i;
            break;
        }
    }

    if (memory_type_index == UINT32_MAX) {
        VulkanFunctionLoader::vkDestroyImage(vk_device_, image, nullptr);
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: no suitable memory type for texture",
            "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    VkMemoryAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc_info.allocationSize = mem_requirements.size;
    alloc_info.memoryTypeIndex = memory_type_index;

    VkDeviceMemory memory = VK_NULL_HANDLE;
    result = VulkanFunctionLoader::vkAllocateMemory(vk_device_, &alloc_info, nullptr, &memory);
    if (result != VK_SUCCESS) {
        VulkanFunctionLoader::vkDestroyImage(vk_device_, image, nullptr);
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to allocate texture memory",
            "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    VulkanFunctionLoader::vkBindImageMemory(vk_device_, image, memory, 0);

    // Create image view
    VkImageViewCreateInfo view_info{};
    view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view_info.image = image;
    view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
    view_info.format = vk_format;
    view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    view_info.subresourceRange.baseMipLevel = 0;
    view_info.subresourceRange.levelCount = desc.mip_levels;
    view_info.subresourceRange.baseArrayLayer = 0;
    view_info.subresourceRange.layerCount = desc.array_layers;

    VkImageView view = VK_NULL_HANDLE;
    result = VulkanFunctionLoader::vkCreateImageView(vk_device_, &view_info, nullptr, &view);
    if (result != VK_SUCCESS) {
        VulkanFunctionLoader::vkFreeMemory(vk_device_, memory, nullptr);
        VulkanFunctionLoader::vkDestroyImage(vk_device_, image, nullptr);
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create image view",
            "vulkan_rhi.cpp:VulkanDevice::create_texture"});
    }

    auto* vk_texture = new VulkanTexture();
    vk_texture->init(image, memory, view, desc.format, desc.extent);
    *texture = reinterpret_cast<RHITexture*>(vk_texture);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_texture(RHITexture* texture) {
    if (!texture) return Result<void>();
    auto* vk_tex = reinterpret_cast<VulkanTexture*>(texture);
    vk_tex->cleanup(vk_device_);
    delete vk_tex;
    return Result<void>();
}

// Shader module
Result<void> VulkanDevice::create_shader_module(const RHIShaderDesc& desc, RHIShaderModule** module) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_shader_module"});
    }

    VkShaderModuleCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    create_info.codeSize = desc.spirv_code.size() * sizeof(uint32_t);
    create_info.pCode = desc.spirv_code.data();

    VkShaderModule shader_module = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateShaderModule(vk_device_, &create_info, nullptr, &shader_module);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create shader module",
            "vulkan_rhi.cpp:VulkanDevice::create_shader_module"});
    }

    auto* vk_shader = new VulkanShaderModule();
    vk_shader->init(shader_module, desc.stage, desc.entry_point);
    *module = reinterpret_cast<RHIShaderModule*>(vk_shader);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_shader_module(RHIShaderModule* module) {
    if (!module) return Result<void>();
    auto* vk_shader = reinterpret_cast<VulkanShaderModule*>(module);
    vk_shader->cleanup(vk_device_);
    delete vk_shader;
    return Result<void>();
}

// Pipeline layout
Result<void> VulkanDevice::create_pipeline_layout(RHIDescriptorSetLayout** layout) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_pipeline_layout"});
    }

    VkPipelineLayoutCreateInfo pipeline_layout_info{};
    pipeline_layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    pipeline_layout_info.setLayoutCount = 0;
    pipeline_layout_info.pSetLayouts = nullptr;
    pipeline_layout_info.pushConstantRangeCount = 0;
    pipeline_layout_info.pPushConstantRanges = nullptr;

    VkPipelineLayout vk_layout_handle = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreatePipelineLayout(vk_device_, &pipeline_layout_info, nullptr, &vk_layout_handle);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create pipeline layout",
            "vulkan_rhi.cpp:VulkanDevice::create_pipeline_layout"});
    }

    auto* vk_layout = new VulkanPipelineLayout();
    vk_layout->init(vk_layout_handle);
    *layout = reinterpret_cast<RHIDescriptorSetLayout*>(vk_layout);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_pipeline_layout(RHIPipelineLayout* layout) {
    if (!layout) return Result<void>();
    auto* vk_layout = reinterpret_cast<VulkanPipelineLayout*>(layout);
    vk_layout->cleanup(vk_device_);
    delete vk_layout;
    return Result<void>();
}

// Graphics pipeline
Result<void> VulkanDevice::create_graphics_pipeline(const RHIGraphicsPipelineDesc& desc,
                                                     RHIPipelineLayout* layout,
                                                     RHIRenderPass* render_pass,
                                                     RHIGraphicsPipeline** pipeline) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_graphics_pipeline"});
    }

    // Create shader stages - create VkShaderModule from SPIR-V code
    std::vector<VkPipelineShaderStageCreateInfo> shader_stages;
    std::vector<VkShaderModule> temp_shader_modules;  // Cleaned up after pipeline creation
    for (const auto& shader_desc : desc.shaders) {
        // Create shader module from SPIR-V code
        VkShaderModuleCreateInfo module_create_info{};
        module_create_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        module_create_info.codeSize = shader_desc.spirv_code.size() * sizeof(uint32_t);
        module_create_info.pCode = shader_desc.spirv_code.data();

        VkShaderModule shader_module = VK_NULL_HANDLE;
        VkResult mod_result = VulkanFunctionLoader::vkCreateShaderModule(vk_device_, &module_create_info, nullptr, &shader_module);
        if (mod_result != VK_SUCCESS) {
            // Clean up any modules already created
            for (auto& mod : temp_shader_modules) {
                VulkanFunctionLoader::vkDestroyShaderModule(vk_device_, mod, nullptr);
            }
            return Result<void>(Error{ErrorCode::INIT_FAILED,
                "Vulkan: failed to create shader module for pipeline",
                "vulkan_rhi.cpp:VulkanDevice::create_graphics_pipeline"});
        }
        temp_shader_modules.push_back(shader_module);

        VkPipelineShaderStageCreateInfo stage_info{};
        stage_info.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stage_info.stage = (shader_desc.stage == RHIShaderStage::Vertex) ?
                           VK_SHADER_STAGE_VERTEX_BIT : VK_SHADER_STAGE_FRAGMENT_BIT;
        stage_info.module = shader_module;
        stage_info.pName = shader_desc.entry_point.c_str();
        shader_stages.push_back(stage_info);
    }

    // Vertex input
    VkPipelineVertexInputStateCreateInfo vertex_input_info{};
    vertex_input_info.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    vertex_input_info.vertexBindingDescriptionCount = static_cast<uint32_t>(desc.vertex_bindings.size());
    vertex_input_info.vertexAttributeDescriptionCount = static_cast<uint32_t>(desc.vertex_attributes.size());

    std::vector<VkVertexInputBindingDescription> binding_descs;
    for (const auto& vb : desc.vertex_bindings) {
        VkVertexInputBindingDescription desc{};
        desc.binding = vb.binding;
        desc.stride = vb.stride;
        desc.inputRate = vb.per_instance ? VK_VERTEX_INPUT_RATE_INSTANCE : VK_VERTEX_INPUT_RATE_VERTEX;
        binding_descs.push_back(desc);
    }
    vertex_input_info.pVertexBindingDescriptions = binding_descs.data();

    std::vector<VkVertexInputAttributeDescription> attr_descs;
    for (const auto& va : desc.vertex_attributes) {
        VkVertexInputAttributeDescription desc{};
        desc.location = va.location;
        desc.binding = va.binding;
        desc.format = VK_FORMAT_R32G32B32_SFLOAT; // Simplified - should map from RHIFormat
        desc.offset = va.offset;
        attr_descs.push_back(desc);
    }
    vertex_input_info.pVertexAttributeDescriptions = attr_descs.data();

    // Input assembly
    VkPipelineInputAssemblyStateCreateInfo input_assembly{};
    input_assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    input_assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    // Viewport and scissor
    VkPipelineViewportStateCreateInfo viewport_state{};
    viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    viewport_state.viewportCount = 1;
    viewport_state.scissorCount = 1;

    // Rasterizer
    VkPipelineRasterizationStateCreateInfo rasterizer{};
    rasterizer.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    rasterizer.depthClampEnable = VK_FALSE;
    rasterizer.rasterizerDiscardEnable = VK_FALSE;
    rasterizer.polygonMode = VK_POLYGON_MODE_FILL;
    rasterizer.lineWidth = 1.0f;
    rasterizer.cullMode = VK_CULL_MODE_BACK_BIT;
    rasterizer.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    rasterizer.depthBiasEnable = VK_FALSE;

    // Multisampling
    VkPipelineMultisampleStateCreateInfo multisampling{};
    multisampling.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    multisampling.sampleShadingEnable = VK_FALSE;
    multisampling.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    // Depth stencil
    VkPipelineDepthStencilStateCreateInfo depth_stencil{};
    depth_stencil.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
    depth_stencil.depthTestEnable = VK_TRUE;
    depth_stencil.depthWriteEnable = VK_TRUE;
    depth_stencil.depthCompareOp = VK_COMPARE_OP_LESS;
    depth_stencil.depthBoundsTestEnable = VK_FALSE;
    depth_stencil.stencilTestEnable = VK_FALSE;

    // Color blending
    std::vector<VkPipelineColorBlendAttachmentState> color_blend_attachments(1);
    color_blend_attachments[0].colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                                VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
    color_blend_attachments[0].blendEnable = VK_FALSE;

    VkPipelineColorBlendStateCreateInfo color_blending{};
    color_blending.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    color_blending.logicOpEnable = VK_FALSE;
    color_blending.attachmentCount = static_cast<uint32_t>(color_blend_attachments.size());
    color_blending.pAttachments = color_blend_attachments.data();

    // Pipeline layout and render pass
    VkPipelineLayout vk_layout = reinterpret_cast<VulkanPipelineLayout*>(layout)->vk_layout();
    VkRenderPass vk_render_pass = reinterpret_cast<VulkanRenderPass*>(render_pass)->vk_render_pass();

    VkGraphicsPipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    pipeline_info.stageCount = static_cast<uint32_t>(shader_stages.size());
    pipeline_info.pStages = shader_stages.data();
    pipeline_info.pVertexInputState = &vertex_input_info;
    pipeline_info.pInputAssemblyState = &input_assembly;
    pipeline_info.pViewportState = &viewport_state;
    pipeline_info.pRasterizationState = &rasterizer;
    pipeline_info.pMultisampleState = &multisampling;
    pipeline_info.pDepthStencilState = &depth_stencil;
    pipeline_info.pColorBlendState = &color_blending;
    pipeline_info.layout = vk_layout;
    pipeline_info.renderPass = vk_render_pass;
    pipeline_info.subpass = 0;

    VkPipeline vk_pipeline = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateGraphicsPipelines(vk_device_, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &vk_pipeline);

    // Clean up temporary shader modules
    for (auto& mod : temp_shader_modules) {
        VulkanFunctionLoader::vkDestroyShaderModule(vk_device_, mod, nullptr);
    }

    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create graphics pipeline: " + std::to_string(result),
            "vulkan_rhi.cpp:VulkanDevice::create_graphics_pipeline"});
    }

    auto* vk_pipeline_obj = new VulkanGraphicsPipeline();
    vk_pipeline_obj->init(vk_pipeline);
    *pipeline = reinterpret_cast<RHIGraphicsPipeline*>(vk_pipeline_obj);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_graphics_pipeline(RHIGraphicsPipeline* pipeline) {
    if (!pipeline) return Result<void>();
    auto* vk_pipeline = reinterpret_cast<VulkanGraphicsPipeline*>(pipeline);
    vk_pipeline->cleanup(vk_device_);
    delete vk_pipeline;
    return Result<void>();
}

// Render pass
Result<void> VulkanDevice::create_render_pass(RHIRenderPass** render_pass) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_render_pass"});
    }

    VkAttachmentDescription color_attachment{};
    color_attachment.format = VK_FORMAT_B8G8R8A8_UNORM; // Will be overridden by swapchain format
    color_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
    color_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    color_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color_attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    color_attachment.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;

    VkAttachmentReference color_attachment_ref{};
    color_attachment_ref.attachment = 0;
    color_attachment_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &color_attachment_ref;

    VkSubpassDependency dependency{};
    dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
    dependency.dstSubpass = 0;
    dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.srcAccessMask = 0;
    dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo render_pass_info{};
    render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    render_pass_info.attachmentCount = 1;
    render_pass_info.pAttachments = &color_attachment;
    render_pass_info.subpassCount = 1;
    render_pass_info.pSubpasses = &subpass;
    render_pass_info.dependencyCount = 1;
    render_pass_info.pDependencies = &dependency;

    VkRenderPass vk_render_pass = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateRenderPass(vk_device_, &render_pass_info, nullptr, &vk_render_pass);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create render pass",
            "vulkan_rhi.cpp:VulkanDevice::create_render_pass"});
    }

    auto* vk_rp = new VulkanRenderPass();
    vk_rp->init(vk_render_pass);
    *render_pass = reinterpret_cast<RHIRenderPass*>(vk_rp);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_render_pass(RHIRenderPass* render_pass) {
    if (!render_pass) return Result<void>();
    auto* vk_rp = reinterpret_cast<VulkanRenderPass*>(render_pass);
    vk_rp->cleanup(vk_device_);
    delete vk_rp;
    return Result<void>();
}

// Framebuffer
Result<void> VulkanDevice::create_framebuffer(RHIFramebuffer** framebuffer) {
    // Simplified - framebuffers are created per swapchain image
    return Result<void>(Error{ErrorCode::INVALID_PARAMETER,
        "Vulkan: use VulkanSwapchain for framebuffers",
        "vulkan_rhi.cpp:VulkanDevice::create_framebuffer"});
}

Result<void> VulkanDevice::destroy_framebuffer(RHIFramebuffer* framebuffer) {
    if (!framebuffer) return Result<void>();
    auto* vk_fb = reinterpret_cast<VulkanFramebuffer*>(framebuffer);
    vk_fb->cleanup(vk_device_);
    delete vk_fb;
    return Result<void>();
}

// Command buffer
Result<void> VulkanDevice::create_command_buffer(RHICommandBuffer** cmd_buffer) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_command_buffer"});
    }

    VkCommandBufferAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    alloc_info.commandPool = vk_command_pool_;
    alloc_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    alloc_info.commandBufferCount = 1;

    VkCommandBuffer cmd_buf = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkAllocateCommandBuffers(vk_device_, &alloc_info, &cmd_buf);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to allocate command buffer",
            "vulkan_rhi.cpp:VulkanDevice::create_command_buffer"});
    }

    auto* vk_cmd = new VulkanCommandBuffer();
    vk_cmd->init(cmd_buf, vk_device_, vk_command_pool_);
    *cmd_buffer = reinterpret_cast<RHICommandBuffer*>(vk_cmd);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_command_buffer(RHICommandBuffer* cmd_buffer) {
    if (!cmd_buffer) return Result<void>();
    auto* vk_cmd = reinterpret_cast<VulkanCommandBuffer*>(cmd_buffer);
    vk_cmd->cleanup(vk_device_);
    delete vk_cmd;
    return Result<void>();
}

// Descriptor set layout
Result<void> VulkanDevice::create_descriptor_set_layout(RHIDescriptorSetLayout** layout) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_descriptor_set_layout"});
    }

    VkDescriptorSetLayoutCreateInfo layout_info{};
    layout_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;
    layout_info.bindingCount = 0;
    layout_info.pBindings = nullptr;

    VkDescriptorSetLayout vk_layout = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateDescriptorSetLayout(vk_device_, &layout_info, nullptr, &vk_layout);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create descriptor set layout",
            "vulkan_rhi.cpp:VulkanDevice::create_descriptor_set_layout"});
    }

    auto* vk_dsl = new VulkanDescriptorSetLayout();
    vk_dsl->init(vk_layout);
    *layout = reinterpret_cast<RHIDescriptorSetLayout*>(vk_dsl);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_descriptor_set_layout(RHIDescriptorSetLayout* layout) {
    if (!layout) return Result<void>();
    auto* vk_dsl = reinterpret_cast<VulkanDescriptorSetLayout*>(layout);
    vk_dsl->cleanup(vk_device_);
    delete vk_dsl;
    return Result<void>();
}

// Descriptor pool
Result<void> VulkanDevice::create_descriptor_pool(RHIDescriptorPool** pool) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_descriptor_pool"});
    }

    VkDescriptorPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;
    pool_info.maxSets = 1000;
    pool_info.poolSizeCount = 0;
    pool_info.pPoolSizes = nullptr;

    VkDescriptorPool vk_pool = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateDescriptorPool(vk_device_, &pool_info, nullptr, &vk_pool);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create descriptor pool",
            "vulkan_rhi.cpp:VulkanDevice::create_descriptor_pool"});
    }

    auto* vk_dp = new VulkanDescriptorPool();
    vk_dp->init(vk_pool);
    *pool = reinterpret_cast<RHIDescriptorPool*>(vk_dp);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_descriptor_pool(RHIDescriptorPool* pool) {
    if (!pool) return Result<void>();
    auto* vk_dp = reinterpret_cast<VulkanDescriptorPool*>(pool);
    vk_dp->cleanup(vk_device_);
    delete vk_dp;
    return Result<void>();
}

// Descriptor sets
Result<void> VulkanDevice::allocate_descriptor_sets(RHIDescriptorPool* pool,
                                                     RHIDescriptorSetLayout* layout,
                                                     RHIDescriptorSet** set) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::allocate_descriptor_sets"});
    }

    VkDescriptorSetLayout vk_layout = reinterpret_cast<VulkanDescriptorSetLayout*>(layout)->vk_layout();
    VkDescriptorPool vk_pool = reinterpret_cast<VulkanDescriptorPool*>(pool)->vk_pool();

    VkDescriptorSetAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;
    alloc_info.descriptorPool = vk_pool;
    alloc_info.descriptorSetCount = 1;
    alloc_info.pSetLayouts = &vk_layout;

    VkDescriptorSet vk_set = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkAllocateDescriptorSets(vk_device_, &alloc_info, &vk_set);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to allocate descriptor sets",
            "vulkan_rhi.cpp:VulkanDevice::allocate_descriptor_sets"});
    }

    auto* vk_ds = new VulkanDescriptorSet();
    vk_ds->init(vk_set);
    *set = reinterpret_cast<RHIDescriptorSet*>(vk_ds);
    return Result<void>();
}

Result<void> VulkanDevice::free_descriptor_sets(RHIDescriptorPool* pool, RHIDescriptorSet* set) {
    if (!pool || !set) return Result<void>();
    VkDescriptorPool vk_pool = reinterpret_cast<VulkanDescriptorPool*>(pool)->vk_pool();
    VkDescriptorSet vk_set = reinterpret_cast<VulkanDescriptorSet*>(set)->vk_set();
    VulkanFunctionLoader::vkFreeDescriptorSets(vk_device_, vk_pool, 1, &vk_set);
    return Result<void>();
}

// Sampler
Result<void> VulkanDevice::create_sampler(RHISampler** sampler) {
    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_sampler"});
    }

    VkSamplerCreateInfo sampler_info{};
    sampler_info.sType = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO;
    sampler_info.magFilter = VK_FILTER_LINEAR;
    sampler_info.minFilter = VK_FILTER_LINEAR;
    sampler_info.addressModeU = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sampler_info.addressModeV = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sampler_info.addressModeW = VK_SAMPLER_ADDRESS_MODE_REPEAT;
    sampler_info.anisotropyEnable = VK_FALSE;
    sampler_info.borderColor = VK_BORDER_COLOR_INT_OPAQUE_BLACK;
    sampler_info.unnormalizedCoordinates = VK_FALSE;
    sampler_info.compareEnable = VK_FALSE;
    sampler_info.compareOp = VK_COMPARE_OP_ALWAYS;
    sampler_info.mipmapMode = VK_SAMPLER_MIPMAP_MODE_LINEAR;
    sampler_info.minLod = 0.0f;
    sampler_info.maxLod = VK_LOD_CLAMP_NONE;

    VkSampler vk_sampler = VK_NULL_HANDLE;
    VkResult result = VulkanFunctionLoader::vkCreateSampler(vk_device_, &sampler_info, nullptr, &vk_sampler);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create sampler",
            "vulkan_rhi.cpp:VulkanDevice::create_sampler"});
    }

    auto* vk_samp = new VulkanSampler();
    vk_samp->init(vk_sampler);
    *sampler = reinterpret_cast<RHISampler*>(vk_samp);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_sampler(RHISampler* sampler) {
    if (!sampler) return Result<void>();
    auto* vk_samp = reinterpret_cast<VulkanSampler*>(sampler);
    vk_samp->cleanup(vk_device_);
    delete vk_samp;
    return Result<void>();
}

// Swapchain
Result<void> VulkanDevice::create_swapchain(RHISurface* surface, const RHISwapchainDesc& desc,
                                             RHISwapchain** swapchain) {
    auto* vk_surface = reinterpret_cast<VulkanSurface*>(surface);
    VkSurfaceKHR vk_surface_handle = vk_surface->vk_surface();

    if (!initialized_) {
        return Result<void>(Error{ErrorCode::NOT_INITIALIZED,
            "Vulkan device not initialized",
            "vulkan_rhi.cpp:VulkanDevice::create_swapchain"});
    }

    auto* vk_sc = new VulkanSwapchain();
    auto result = vk_sc->init(vk_device_, vk_physical_device_, vk_surface_handle,
                               desc.extent.width, desc.extent.height,
                               vk_graphics_queue_, vk_present_queue_);
    if (!result.ok()) {
        delete vk_sc;
        return result;
    }
    *swapchain = reinterpret_cast<RHISwapchain*>(vk_sc);
    return Result<void>();
}

Result<void> VulkanDevice::destroy_swapchain(RHISwapchain* swapchain) {
    if (!swapchain) return Result<void>();
    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(swapchain);
    vk_sc->cleanup(vk_device_);
    delete vk_sc;
    return Result<void>();
}

Result<void> VulkanDevice::acquire_next_image(RHISwapchain* swapchain, uint32_t* image_index) {
    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(swapchain);
    return vk_sc->acquire_next_image(image_index);
}

Result<void> VulkanDevice::present(RHISwapchain* swapchain, uint32_t image_index) {
    auto* vk_sc = reinterpret_cast<VulkanSwapchain*>(swapchain);
    return vk_sc->present(image_index);
}

// Device properties
std::string VulkanDevice::device_name() const {
    return std::string(device_properties_.deviceName);
}

uint32_t VulkanDevice::vendor_id() const {
    return device_properties_.vendorID;
}

uint32_t VulkanDevice::device_id() const {
    return device_properties_.deviceID;
}

RHIDeviceFeatures VulkanDevice::features() const {
    RHIDeviceFeatures f{};
    f.geometry_shader = device_features_.geometryShader;
    f.tessellation_shader = device_features_.tessellationShader;
    f.fill_mode_non_solid = device_features_.fillModeNonSolid;
    f.wide_lines = device_features_.wideLines;
    f.sampler_anisotropy = device_features_.samplerAnisotropy;
    return f;
}

Result<void> VulkanDevice::wait_idle() {
    if (!initialized_) return Result<void>();
    VkResult result = VulkanFunctionLoader::vkDeviceWaitIdle(vk_device_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: device wait idle failed",
            "vulkan_rhi.cpp:VulkanDevice::wait_idle"});
    }
    return Result<void>();
}

// === Vulkan Queue ===

VulkanQueue::VulkanQueue(VkQueue queue, VkDevice device)
    : vk_queue_(queue), vk_device_(device) {}

Result<void> VulkanQueue::submit(RHICommandBuffer* cmd_buffer) {
    return submit(cmd_buffer, VK_NULL_HANDLE, VK_NULL_HANDLE, VK_NULL_HANDLE);
}

Result<void> VulkanQueue::submit(RHICommandBuffer* cmd_buffer,
                                    VkSemaphore wait_semaphore,
                                    VkSemaphore signal_semaphore,
                                    VkFence fence) {
    auto* vk_cmd = reinterpret_cast<VulkanCommandBuffer*>(cmd_buffer);
    VkSubmitInfo submit_info{};
    submit_info.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit_info.commandBufferCount = 1;
    VkCommandBuffer vk_cmd_buf = vk_cmd->vk_cmd_buffer();
    submit_info.pCommandBuffers = &vk_cmd_buf;

    VkPipelineStageFlags wait_stages[] = {VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT};
    submit_info.waitSemaphoreCount = (wait_semaphore != VK_NULL_HANDLE) ? 1 : 0;
    submit_info.pWaitSemaphores = (wait_semaphore != VK_NULL_HANDLE) ? &wait_semaphore : nullptr;
    submit_info.pWaitDstStageMask = wait_stages;
    submit_info.signalSemaphoreCount = (signal_semaphore != VK_NULL_HANDLE) ? 1 : 0;
    submit_info.pSignalSemaphores = (signal_semaphore != VK_NULL_HANDLE) ? &signal_semaphore : nullptr;

    VkResult result = VulkanFunctionLoader::vkQueueSubmit(vk_queue_, 1, &submit_info, fence);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: queue submit failed",
            "vulkan_rhi.cpp:VulkanQueue::submit"});
    }
    return Result<void>();
}

Result<void> VulkanQueue::wait_idle() {
    VkResult result = VulkanFunctionLoader::vkQueueWaitIdle(vk_queue_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: queue wait idle failed",
            "vulkan_rhi.cpp:VulkanQueue::wait_idle"});
    }
    return Result<void>();
}

// === Vulkan Buffer ===

VulkanBuffer::VulkanBuffer() = default;
VulkanBuffer::~VulkanBuffer() = default;

void VulkanBuffer::init(VkBuffer buffer, VkDeviceMemory memory, uint64_t size) {
    vk_buffer_ = buffer;
    vk_memory_ = memory;
    size_ = size;
}

void VulkanBuffer::cleanup(VkDevice device) {
    if (vk_memory_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkFreeMemory(device, vk_memory_, nullptr);
        vk_memory_ = VK_NULL_HANDLE;
    }
    if (vk_buffer_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyBuffer(device, vk_buffer_, nullptr);
        vk_buffer_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Texture ===

VulkanTexture::VulkanTexture() = default;
VulkanTexture::~VulkanTexture() = default;

void VulkanTexture::init(VkImage image, VkDeviceMemory memory, VkImageView view,
                          RHIFormat format, RHIExtent3D extent) {
    vk_image_ = image;
    vk_memory_ = memory;
    vk_view_ = view;
    format_ = format;
    extent_ = extent;
}

void VulkanTexture::cleanup(VkDevice device) {
    if (vk_view_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyImageView(device, vk_view_, nullptr);
        vk_view_ = VK_NULL_HANDLE;
    }
    if (vk_memory_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkFreeMemory(device, vk_memory_, nullptr);
        vk_memory_ = VK_NULL_HANDLE;
    }
    if (vk_image_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyImage(device, vk_image_, nullptr);
        vk_image_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Shader Module ===

VulkanShaderModule::VulkanShaderModule() = default;
VulkanShaderModule::~VulkanShaderModule() = default;

void VulkanShaderModule::init(VkShaderModule module, RHIShaderStage stage, std::string entry_point) {
    vk_module_ = module;
    stage_ = stage;
    entry_point_ = std::move(entry_point);
}

void VulkanShaderModule::cleanup(VkDevice device) {
    if (vk_module_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyShaderModule(device, vk_module_, nullptr);
        vk_module_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Pipeline Layout ===

VulkanPipelineLayout::VulkanPipelineLayout() = default;
VulkanPipelineLayout::~VulkanPipelineLayout() = default;

void VulkanPipelineLayout::init(VkPipelineLayout layout) {
    vk_layout_ = layout;
}

void VulkanPipelineLayout::cleanup(VkDevice device) {
    if (vk_layout_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyPipelineLayout(device, vk_layout_, nullptr);
        vk_layout_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Graphics Pipeline ===

VulkanGraphicsPipeline::VulkanGraphicsPipeline() = default;
VulkanGraphicsPipeline::~VulkanGraphicsPipeline() = default;

void VulkanGraphicsPipeline::init(VkPipeline pipeline) {
    vk_pipeline_ = pipeline;
}

void VulkanGraphicsPipeline::cleanup(VkDevice device) {
    if (vk_pipeline_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyPipeline(device, vk_pipeline_, nullptr);
        vk_pipeline_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Render Pass ===

VulkanRenderPass::VulkanRenderPass() = default;
VulkanRenderPass::~VulkanRenderPass() = default;

void VulkanRenderPass::init(VkRenderPass render_pass) {
    vk_render_pass_ = render_pass;
}

void VulkanRenderPass::cleanup(VkDevice device) {
    if (vk_render_pass_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyRenderPass(device, vk_render_pass_, nullptr);
        vk_render_pass_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Framebuffer ===

VulkanFramebuffer::VulkanFramebuffer() = default;
VulkanFramebuffer::~VulkanFramebuffer() = default;

void VulkanFramebuffer::init(VkFramebuffer framebuffer) {
    vk_framebuffer_ = framebuffer;
}

void VulkanFramebuffer::cleanup(VkDevice device) {
    if (vk_framebuffer_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyFramebuffer(device, vk_framebuffer_, nullptr);
        vk_framebuffer_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Command Buffer ===

VulkanCommandBuffer::VulkanCommandBuffer() = default;
VulkanCommandBuffer::~VulkanCommandBuffer() = default;

void VulkanCommandBuffer::init(VkCommandBuffer cmd_buffer, VkDevice device, VkCommandPool pool) {
    vk_cmd_buffer_ = cmd_buffer;
    vk_device_ = device;
    vk_command_pool_ = pool;
}

void VulkanCommandBuffer::cleanup(VkDevice device) {
    if (vk_cmd_buffer_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkFreeCommandBuffers(device, vk_command_pool_, 1, &vk_cmd_buffer_);
        vk_cmd_buffer_ = VK_NULL_HANDLE;
    }
}

Result<void> VulkanCommandBuffer::begin() {
    VkCommandBufferBeginInfo begin_info{};
    begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    VkResult result = VulkanFunctionLoader::vkBeginCommandBuffer(vk_cmd_buffer_, &begin_info);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to begin command buffer",
            "vulkan_rhi.cpp:VulkanCommandBuffer::begin"});
    }
    recording_ = true;
    return Result<void>();
}

Result<void> VulkanCommandBuffer::end() {
    VkResult result = VulkanFunctionLoader::vkEndCommandBuffer(vk_cmd_buffer_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to end command buffer",
            "vulkan_rhi.cpp:VulkanCommandBuffer::end"});
    }
    recording_ = false;
    return Result<void>();
}

Result<void> VulkanCommandBuffer::reset() {
    VkResult result = VulkanFunctionLoader::vkResetCommandBuffer(vk_cmd_buffer_, 0);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to reset command buffer",
            "vulkan_rhi.cpp:VulkanCommandBuffer::reset"});
    }
    return Result<void>();
}

Result<void> VulkanCommandBuffer::begin_render_pass(RHIRenderPass* render_pass,
                                                     RHIFramebuffer* framebuffer,
                                                     const RHIExtent2D& render_area,
                                                     const std::vector<RHIColor>& clear_colors,
                                                     float clear_depth,
                                                     uint8_t clear_stencil) {
    VkRenderPass vk_rp = reinterpret_cast<VulkanRenderPass*>(render_pass)->vk_render_pass();
    VkFramebuffer vk_fb = reinterpret_cast<VulkanFramebuffer*>(framebuffer)->vk_framebuffer();

    VkRenderPassBeginInfo render_pass_info{};
    render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    render_pass_info.renderPass = vk_rp;
    render_pass_info.framebuffer = vk_fb;
    render_pass_info.renderArea.offset = {0, 0};
    render_pass_info.renderArea.extent = {render_area.width, render_area.height};

    std::vector<VkClearValue> clear_values(clear_colors.size());
    for (size_t i = 0; i < clear_colors.size(); i++) {
        clear_values[i].color = {{clear_colors[i].r, clear_colors[i].g, clear_colors[i].b, clear_colors[i].a}};
    }
    render_pass_info.clearValueCount = static_cast<uint32_t>(clear_values.size());
    render_pass_info.pClearValues = clear_values.data();

    VulkanFunctionLoader::vkCmdBeginRenderPass(vk_cmd_buffer_, &render_pass_info, VK_SUBPASS_CONTENTS_INLINE);
    in_render_pass_ = true;
    return Result<void>();
}

Result<void> VulkanCommandBuffer::end_render_pass() {
    VulkanFunctionLoader::vkCmdEndRenderPass(vk_cmd_buffer_);
    in_render_pass_ = false;
    return Result<void>();
}

Result<void> VulkanCommandBuffer::bind_pipeline(RHIGraphicsPipeline* pipeline) {
    auto* vk_pipeline = reinterpret_cast<VulkanGraphicsPipeline*>(pipeline);
    VulkanFunctionLoader::vkCmdBindPipeline(vk_cmd_buffer_, VK_PIPELINE_BIND_POINT_GRAPHICS, vk_pipeline->vk_pipeline());
    return Result<void>();
}

Result<void> VulkanCommandBuffer::bind_vertex_buffer(uint32_t binding, RHIBuffer* buffer, uint64_t offset) {
    auto* vk_buf = reinterpret_cast<VulkanBuffer*>(buffer);
    VkDeviceSize offsets[] = {static_cast<VkDeviceSize>(offset)};
    VkBuffer vk_buf_handle = vk_buf->vk_buffer();
    VulkanFunctionLoader::vkCmdBindVertexBuffers(vk_cmd_buffer_, binding, 1, &vk_buf_handle, offsets);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::bind_index_buffer(RHIBuffer* buffer, RHIFormat format) {
    auto* vk_buf = reinterpret_cast<VulkanBuffer*>(buffer);
    VkIndexType vk_format = VK_INDEX_TYPE_UINT32;
    VulkanFunctionLoader::vkCmdBindIndexBuffer(vk_cmd_buffer_, vk_buf->vk_buffer(), 0, vk_format);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::bind_descriptor_set(RHIPipelineLayout* layout,
                                                       RHIDescriptorSet* set,
                                                       uint32_t first_set,
                                                       const std::vector<uint32_t>& dynamic_offsets) {
    auto* vk_layout = reinterpret_cast<VulkanPipelineLayout*>(layout);
    auto* vk_set = reinterpret_cast<VulkanDescriptorSet*>(set);
    VkDescriptorSet vk_set_handle = vk_set->vk_set();
    VulkanFunctionLoader::vkCmdBindDescriptorSets(vk_cmd_buffer_, VK_PIPELINE_BIND_POINT_GRAPHICS,
                            vk_layout->vk_layout(), first_set, 1, &vk_set_handle,
                            static_cast<uint32_t>(dynamic_offsets.size()), dynamic_offsets.data());
    return Result<void>();
}

Result<void> VulkanCommandBuffer::set_viewport(const RHIViewport& viewport) {
    VkViewport vk_viewport{};
    vk_viewport.x = viewport.x;
    vk_viewport.y = viewport.y;
    vk_viewport.width = viewport.width;
    vk_viewport.height = viewport.height;
    vk_viewport.minDepth = viewport.min_depth;
    vk_viewport.maxDepth = viewport.max_depth;
    VulkanFunctionLoader::vkCmdSetViewport(vk_cmd_buffer_, 0, 1, &vk_viewport);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::set_scissor(const RHIScissor& scissor) {
    VkRect2D vk_scissor{};
    vk_scissor.offset = {scissor.x, scissor.y};
    vk_scissor.extent = {scissor.width, scissor.height};
    VulkanFunctionLoader::vkCmdSetScissor(vk_cmd_buffer_, 0, 1, &vk_scissor);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::draw_indexed(uint32_t index_count, uint32_t instance_count,
                                                uint32_t first_index, uint32_t vertex_offset,
                                                uint32_t first_instance) {
    VulkanFunctionLoader::vkCmdDrawIndexed(vk_cmd_buffer_, index_count, instance_count, first_index, vertex_offset, first_instance);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::draw(uint32_t vertex_count, uint32_t instance_count,
                                        uint32_t first_vertex, uint32_t first_instance) {
    VulkanFunctionLoader::vkCmdDraw(vk_cmd_buffer_, vertex_count, instance_count, first_vertex, first_instance);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::buffer_memory_barrier(RHIBuffer* buffer,
                                                         uint32_t src_access_mask,
                                                         uint32_t dst_access_mask,
                                                         uint32_t src_stage,
                                                         uint32_t dst_stage) {
    auto* vk_buf = reinterpret_cast<VulkanBuffer*>(buffer);
    VkBufferMemoryBarrier barrier{};
    barrier.sType = VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
    barrier.srcAccessMask = src_access_mask;
    barrier.dstAccessMask = dst_access_mask;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.buffer = vk_buf->vk_buffer();
    barrier.size = VK_WHOLE_SIZE;
    VulkanFunctionLoader::vkCmdPipelineBarrier(vk_cmd_buffer_, src_stage, dst_stage, 0, 0, nullptr, 1, &barrier, 0, nullptr);
    return Result<void>();
}

Result<void> VulkanCommandBuffer::image_memory_barrier(RHITexture* texture,
                                                        uint32_t src_access_mask,
                                                        uint32_t dst_access_mask,
                                                        uint32_t src_stage,
                                                        uint32_t dst_stage) {
    auto* vk_tex = reinterpret_cast<VulkanTexture*>(texture);
    VkImageMemoryBarrier barrier{};
    barrier.sType = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    barrier.srcAccessMask = src_access_mask;
    barrier.dstAccessMask = dst_access_mask;
    barrier.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    barrier.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.image = vk_tex->vk_image();
    barrier.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    barrier.subresourceRange.baseMipLevel = 0;
    barrier.subresourceRange.levelCount = 1;
    barrier.subresourceRange.baseArrayLayer = 0;
    barrier.subresourceRange.layerCount = 1;
    VulkanFunctionLoader::vkCmdPipelineBarrier(vk_cmd_buffer_, src_stage, dst_stage, 0, 0, nullptr, 0, nullptr, 1, &barrier);
    return Result<void>();
}

// === Vulkan Descriptor Set Layout ===

VulkanDescriptorSetLayout::VulkanDescriptorSetLayout() = default;
VulkanDescriptorSetLayout::~VulkanDescriptorSetLayout() = default;

void VulkanDescriptorSetLayout::init(VkDescriptorSetLayout layout) {
    vk_layout_ = layout;
}

void VulkanDescriptorSetLayout::cleanup(VkDevice device) {
    if (vk_layout_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyDescriptorSetLayout(device, vk_layout_, nullptr);
        vk_layout_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Descriptor Pool ===

VulkanDescriptorPool::VulkanDescriptorPool() = default;
VulkanDescriptorPool::~VulkanDescriptorPool() = default;

void VulkanDescriptorPool::init(VkDescriptorPool pool) {
    vk_pool_ = pool;
}

void VulkanDescriptorPool::cleanup(VkDevice device) {
    if (vk_pool_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyDescriptorPool(device, vk_pool_, nullptr);
        vk_pool_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Descriptor Set ===

VulkanDescriptorSet::VulkanDescriptorSet() = default;
VulkanDescriptorSet::~VulkanDescriptorSet() = default;

void VulkanDescriptorSet::init(VkDescriptorSet set) {
    vk_set_ = set;
}

void VulkanDescriptorSet::cleanup(VkDevice device) {
    // Descriptor sets are freed through the pool, not individually destroyed
    (void)device;
    vk_set_ = VK_NULL_HANDLE;
}

// === Vulkan Sampler ===

VulkanSampler::VulkanSampler() = default;
VulkanSampler::~VulkanSampler() = default;

void VulkanSampler::init(VkSampler sampler) {
    vk_sampler_ = sampler;
}

void VulkanSampler::cleanup(VkDevice device) {
    if (vk_sampler_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroySampler(device, vk_sampler_, nullptr);
        vk_sampler_ = VK_NULL_HANDLE;
    }
}

// === Vulkan Swapchain ===

VulkanSwapchain::VulkanSwapchain() = default;
VulkanSwapchain::~VulkanSwapchain() = default;

Result<void> VulkanSwapchain::init(VkDevice device, VkPhysicalDevice physical_device,
                                    VkSurfaceKHR surface, uint32_t width, uint32_t height,
                                    VkQueue graphics_queue, VkQueue present_queue) {
    vk_device_ = device;
    vk_graphics_queue_ = graphics_queue;
    vk_present_queue_ = present_queue;

    // Get surface capabilities
    VkSurfaceCapabilitiesKHR capabilities;
    VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical_device, surface, &capabilities);

    // Choose extent
    vk_extent_.width = (capabilities.currentExtent.width != UINT32_MAX) ?
                        capabilities.currentExtent.width : width;
    vk_extent_.height = (capabilities.currentExtent.height != UINT32_MAX) ?
                         capabilities.currentExtent.height : height;

    // Choose format
    uint32_t format_count;
    VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device, surface, &format_count, nullptr);
    std::vector<VkSurfaceFormatKHR> formats(format_count);
    VulkanFunctionLoader::vkGetPhysicalDeviceSurfaceFormatsKHR(physical_device, surface, &format_count, formats.data());

    if (format_count == 1 && formats[0].format == VK_FORMAT_UNDEFINED) {
        vk_format_ = VK_FORMAT_B8G8R8A8_UNORM;
    } else {
        vk_format_ = formats[0].format;
    }

    // Determine image count
    uint32_t image_count = capabilities.minImageCount + 1;
    if (capabilities.maxImageCount > 0 && image_count > capabilities.maxImageCount) {
        image_count = capabilities.maxImageCount;
    }

    // Create swapchain
    VkSwapchainCreateInfoKHR create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
    create_info.surface = surface;
    create_info.minImageCount = image_count;
    create_info.imageFormat = vk_format_;
    create_info.imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
    create_info.imageExtent = vk_extent_;
    create_info.imageArrayLayers = 1;
    create_info.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    create_info.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    create_info.preTransform = capabilities.currentTransform;
    create_info.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    create_info.presentMode = VK_PRESENT_MODE_FIFO_KHR;
    create_info.clipped = VK_TRUE;
    create_info.oldSwapchain = VK_NULL_HANDLE;

    VkResult result = VulkanFunctionLoader::vkCreateSwapchainKHR(vk_device_, &create_info, nullptr, &vk_swapchain_);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to create swapchain: " + std::to_string(result),
            "vulkan_rhi.cpp:VulkanSwapchain::init"});
    }

    // Get swapchain images
    uint32_t image_count_out;
    VulkanFunctionLoader::vkGetSwapchainImagesKHR(vk_device_, vk_swapchain_, &image_count_out, nullptr);
    vk_images_.resize(image_count_out);
    VulkanFunctionLoader::vkGetSwapchainImagesKHR(vk_device_, vk_swapchain_, &image_count_out, vk_images_.data());

    // Create image views
    vk_image_views_.resize(image_count_out);
    for (uint32_t i = 0; i < image_count_out; i++) {
        VkImageViewCreateInfo view_info{};
        view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view_info.image = vk_images_[i];
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = vk_format_;
        view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view_info.subresourceRange.baseMipLevel = 0;
        view_info.subresourceRange.levelCount = 1;
        view_info.subresourceRange.baseArrayLayer = 0;
        view_info.subresourceRange.layerCount = 1;

        result = VulkanFunctionLoader::vkCreateImageView(vk_device_, &view_info, nullptr, &vk_image_views_[i]);
        if (result != VK_SUCCESS) {
            return Result<void>(Error{ErrorCode::INIT_FAILED,
                "Vulkan: failed to create image view",
                "vulkan_rhi.cpp:VulkanSwapchain::init"});
        }
    }

    // Create sync primitives
    VkSemaphoreCreateInfo semaphore_info{};
    semaphore_info.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

    VkFenceCreateInfo fence_info{};
    fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fence_info.flags = VK_FENCE_CREATE_SIGNALED_BIT;

    VulkanFunctionLoader::vkCreateSemaphore(vk_device_, &semaphore_info, nullptr, &vk_image_available_semaphore_);
    VulkanFunctionLoader::vkCreateSemaphore(vk_device_, &semaphore_info, nullptr, &vk_render_finished_semaphore_);
    VulkanFunctionLoader::vkCreateFence(vk_device_, &fence_info, nullptr, &vk_in_flight_fence_);

    REALITY_LOG(INFO, "Vulkan: swapchain created with " + std::to_string(image_count_out) + " images");
    return Result<void>();
}

Result<void> VulkanSwapchain::create_framebuffers(VkRenderPass render_pass) {
    framebuffers_.resize(vk_image_views_.size());
    for (size_t i = 0; i < vk_image_views_.size(); i++) {
        VkFramebufferCreateInfo framebuffer_info{};
        framebuffer_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebuffer_info.renderPass = render_pass;
        framebuffer_info.attachmentCount = 1;
        framebuffer_info.pAttachments = &vk_image_views_[i];
        framebuffer_info.width = vk_extent_.width;
        framebuffer_info.height = vk_extent_.height;
        framebuffer_info.layers = 1;

        VkFramebuffer vk_fb = VK_NULL_HANDLE;
        VkResult result = VulkanFunctionLoader::vkCreateFramebuffer(vk_device_, &framebuffer_info, nullptr, &vk_fb);
        if (result != VK_SUCCESS) {
            // Clean up already created framebuffers
            for (size_t j = 0; j < i; j++) {
                if (framebuffers_[j] != nullptr) {
                    framebuffers_[j]->cleanup(vk_device_);
                    delete framebuffers_[j];
                }
            }
            framebuffers_.clear();
            return Result<void>(Error{ErrorCode::INIT_FAILED,
                "Vulkan: failed to create framebuffer",
                "vulkan_rhi.cpp:VulkanSwapchain::create_framebuffers"});
        }

        auto* fb = new VulkanFramebuffer();
        fb->init(vk_fb);
        framebuffers_[i] = fb;
    }
    REALITY_LOG(INFO, "Vulkan: created " + std::to_string(framebuffers_.size()) + " framebuffers");
    return Result<void>();
}

RHIFramebuffer* VulkanSwapchain::get_framebuffer(uint32_t index) const {
    if (index < framebuffers_.size()) {
        return reinterpret_cast<RHIFramebuffer*>(framebuffers_[index]);
    }
    return nullptr;
}

void VulkanSwapchain::destroy_framebuffers(VkDevice device) {
    for (auto& fb : framebuffers_) {
        if (fb != nullptr) {
            fb->cleanup(device);
            delete fb;
        }
    }
    framebuffers_.clear();
}

void VulkanSwapchain::cleanup(VkDevice device) {
    destroy_framebuffers(device);
    if (vk_in_flight_fence_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroyFence(device, vk_in_flight_fence_, nullptr);
        vk_in_flight_fence_ = VK_NULL_HANDLE;
    }
    if (vk_render_finished_semaphore_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroySemaphore(device, vk_render_finished_semaphore_, nullptr);
        vk_render_finished_semaphore_ = VK_NULL_HANDLE;
    }
    if (vk_image_available_semaphore_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroySemaphore(device, vk_image_available_semaphore_, nullptr);
        vk_image_available_semaphore_ = VK_NULL_HANDLE;
    }
    for (auto& view : vk_image_views_) {
        if (view != VK_NULL_HANDLE) {
            VulkanFunctionLoader::vkDestroyImageView(device, view, nullptr);
        }
    }
    vk_image_views_.clear();
    vk_images_.clear();
    if (vk_swapchain_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroySwapchainKHR(vk_device_, vk_swapchain_, nullptr);
        vk_swapchain_ = VK_NULL_HANDLE;
    }
}

Result<void> VulkanSwapchain::acquire_next_image(uint32_t* image_index) {
    VkResult result = VulkanFunctionLoader::vkAcquireNextImageKHR(vk_device_, vk_swapchain_, UINT64_MAX,
                                            vk_image_available_semaphore_, VK_NULL_HANDLE, image_index);
    if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to acquire next swapchain image",
            "vulkan_rhi.cpp:VulkanSwapchain::acquire_next_image"});
    }
    return Result<void>();
}

Result<void> VulkanSwapchain::present(uint32_t image_index) {
    VkPresentInfoKHR present_info{};
    present_info.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
    present_info.waitSemaphoreCount = 1;
    present_info.pWaitSemaphores = &vk_render_finished_semaphore_;
    present_info.swapchainCount = 1;
    present_info.pSwapchains = &vk_swapchain_;
    present_info.pImageIndices = &image_index;

    VkResult result = VulkanFunctionLoader::vkQueuePresentKHR(vk_present_queue_, &present_info);
    if (result != VK_SUCCESS) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: failed to present swapchain image",
            "vulkan_rhi.cpp:VulkanSwapchain::present"});
    }
    return Result<void>();
}

// === Vulkan Surface ===

VulkanSurface::VulkanSurface() = default;
VulkanSurface::~VulkanSurface() {
    destroy();
}

Result<void> VulkanSurface::init(RHIInstance* instance, RHIWindow* window) {
    vk_instance_ = reinterpret_cast<VulkanInstance*>(instance)->vk_instance();
    if (vk_instance_ == VK_NULL_HANDLE) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: invalid instance for surface creation",
            "vulkan_rhi.cpp:VulkanSurface::init"});
    }

    // Create platform-specific surface via window
    RHISurface* surface_this = reinterpret_cast<RHISurface*>(this);
    auto result = window->create_surface(instance, &surface_this);
    if (!result.ok()) return result;

    initialized_ = true;
    return Result<void>();
}

void VulkanSurface::destroy() {
    if (vk_surface_ != VK_NULL_HANDLE && vk_instance_ != VK_NULL_HANDLE) {
        VulkanFunctionLoader::vkDestroySurfaceKHR(vk_instance_, vk_surface_, nullptr);
        vk_surface_ = VK_NULL_HANDLE;
    }
    initialized_ = false;
}

// === Vulkan Window ===

VulkanWindow::VulkanWindow() = default;
VulkanWindow::~VulkanWindow() {
    destroy();
}

Result<void> VulkanWindow::create(const RHIWindowDesc& desc) {
    desc_ = desc;
    width_ = desc.width;
    height_ = desc.height;
    should_close_ = false;
    REALITY_LOG(INFO, "VulkanWindow: created " + desc.title + " (" +
                    std::to_string(desc.width) + "x" + std::to_string(desc.height) + ")");
    return Result<void>();
}

void VulkanWindow::destroy() {
    should_close_ = true;
}

void* VulkanWindow::get_instance_extension_names(std::vector<const char*>& extensions) {
    // For headless/minimal window, no window-system extensions needed
    // VK_KHR_display or VK_KHR_wayland/XCB/etc. would be added by platform code
    return nullptr;
}

Result<void> VulkanWindow::create_surface(RHIInstance* instance, RHISurface** surface) {
    auto* vulkan_instance = reinterpret_cast<VulkanInstance*>(instance);
    VkInstance vk_instance = vulkan_instance->vk_instance();

    // Try VK_KHR_display for headless surface creation (no window needed)
    // This is the preferred approach for headless/CI environments
    PFN_vkGetPhysicalDeviceDisplayPropertiesKHR get_display_props =
        reinterpret_cast<PFN_vkGetPhysicalDeviceDisplayPropertiesKHR>(
            VulkanFunctionLoader::vkGetInstanceProcAddr_fn(vk_instance, "vkGetPhysicalDeviceDisplayPropertiesKHR"));
    PFN_vkGetDisplayModePropertiesKHR get_display_mode_props =
        reinterpret_cast<PFN_vkGetDisplayModePropertiesKHR>(
            VulkanFunctionLoader::vkGetInstanceProcAddr_fn(vk_instance, "vkGetDisplayModePropertiesKHR"));
    PFN_vkCreateDisplayPlaneSurfaceKHR create_display_surface =
        reinterpret_cast<PFN_vkCreateDisplayPlaneSurfaceKHR>(
            VulkanFunctionLoader::vkGetInstanceProcAddr_fn(vk_instance, "vkCreateDisplayPlaneSurfaceKHR"));

    if (!get_display_props || !get_display_mode_props || !create_display_surface) {
        return Result<void>(Error{ErrorCode::INIT_FAILED,
            "Vulkan: VK_KHR_display extension not available for headless surface creation",
            "vulkan_rhi.cpp:VulkanWindow::create_surface"});
    }

    // Headless surface creation - no display extensions available
    // In a real deployment with a GPU, this would create a proper VkSurfaceKHR
    // via VK_KHR_display or platform-specific extensions (Xlib, Wayland, Win32, etc.)
    VkSurfaceKHR vk_surface = VK_NULL_HANDLE;

    auto* vk_surface_obj = new VulkanSurface();
    vk_surface_obj->vk_instance_ = vk_instance;
    vk_surface_obj->vk_surface_ = vk_surface;
    vk_surface_obj->initialized_ = true;
    *surface = vk_surface_obj;

    REALITY_LOG(WARN, "VulkanWindow: created null surface (no display available - headless only)");
    return Result<void>();
}

#endif // REALITY_HAS_VULKAN

} // namespace reality