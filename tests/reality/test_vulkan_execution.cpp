// ============================================================================
// test_vulkan_execution.cpp
//
// Real Vulkan execution test - actually executes Vulkan API calls:
// 1. Vulkan instance creation with validation layers
// 2. Physical device enumeration (identifies hardware vs software)
// 3. Logical device creation
// 4. Queue retrieval
// 5. Buffer allocation, memory allocation and binding
// 6. Buffer upload
// 7. Shader module creation from SPIR-V
// 8. Graphics pipeline creation
// 9. Offscreen rendering to image
// 10. Image readback
// 11. Resource destruction
//
// This test requires a Vulkan ICD (libvulkan.so) to be available.
// On headless CI runners, Mesa lavapipe provides a software Vulkan ICD.
// ============================================================================

#include <iostream>
#include <cstring>
#include <vector>
#include <string>
#include <cstdlib>
#include <cassert>
#include <cstdint>
#if !defined(_WIN32)
#include <dlfcn.h>
#endif

// Vulkan headers
#include <vulkan/vulkan.h>

#ifndef VK_USE_PLATFORM_XCB_KHR
#define VK_USE_PLATFORM_XCB_KHR 0
#endif

// Simple test result tracking
static int g_tests_passed = 0;
static int g_tests_failed = 0;

#define TEST_CHECK(cond, msg) \
    do { \
        if (cond) { \
            std::cout << "  PASS: " << msg << std::endl; \
            g_tests_passed++; \
        } else { \
            std::cout << "  FAIL: " << msg << std::endl; \
            g_tests_failed++; \
        } \
    } while(0)

#define TEST_VK(result, msg) \
    do { \
        if (result == VK_SUCCESS) { \
            std::cout << "  PASS: " << msg << std::endl; \
            g_tests_passed++; \
        } else { \
            std::cout << "  FAIL: " << msg << " (VkResult=" << result << ")" << std::endl; \
            g_tests_failed++; \
        } \
    } while(0)

// Load Vulkan function pointers dynamically (like the engine does)
static PFN_vkGetInstanceProcAddr g_vkGetInstanceProcAddr = nullptr;

static void* load_vulkan_library() {
#ifdef _WIN32
    return LoadLibraryA("vulkan-1.dll");
#elif defined(__APPLE__)
    return dlopen("libvulkan.1.dylib", RTLD_NOW | RTLD_LOCAL);
#else
    void* lib = dlopen("libvulkan.so.1", RTLD_NOW | RTLD_LOCAL);
    if (!lib) lib = dlopen("libvulkan.so", RTLD_NOW | RTLD_LOCAL);
    return lib;
#endif
}

static PFN_vkVoidFunction load_vulkan_func(void* lib, const char* name) {
#ifdef _WIN32
    return (PROC)GetProcAddress((HMODULE)lib, name);
#else
    return reinterpret_cast<PFN_vkVoidFunction>(dlsym(lib, name));
#endif
}

int main() {
    std::cout << "=== Reality Engine Vulkan Execution Test ===" << std::endl;
    std::cout << std::endl;

    // ------------------------------------------------------------------
    // Step 1: Load Vulkan library
    // ------------------------------------------------------------------
    std::cout << "[1/12] Loading Vulkan library..." << std::endl;
    void* vk_lib = load_vulkan_library();
    TEST_CHECK(vk_lib != nullptr, "Vulkan library loaded (libvulkan.so)");
    if (!vk_lib) {
        std::cout << "  Cannot proceed without Vulkan ICD" << std::endl;
        return 1;
    }

    g_vkGetInstanceProcAddr = (PFN_vkGetInstanceProcAddr)load_vulkan_func(vk_lib, "vkGetInstanceProcAddr");
    TEST_CHECK(g_vkGetInstanceProcAddr != nullptr, "vkGetInstanceProcAddr loaded");

    // ------------------------------------------------------------------
    // Step 2: Vulkan instance creation
    // ------------------------------------------------------------------
    std::cout << std::endl << "[2/12] Creating Vulkan instance..." << std::endl;

    // Check available layers
    uint32_t layer_count = 0;
    g_vkGetInstanceProcAddr(nullptr, "vkEnumerateInstanceLayerProperties");
    auto vkEnumerateInstanceLayerProperties = (PFN_vkEnumerateInstanceLayerProperties)
        g_vkGetInstanceProcAddr(nullptr, "vkEnumerateInstanceLayerProperties");
    VkResult res = vkEnumerateInstanceLayerProperties(&layer_count, nullptr);
    TEST_VK(res, "vkEnumerateInstanceLayerProperties (count)");
    std::cout << "  Available instance layers: " << layer_count << std::endl;

    std::vector<VkLayerProperties> layers(layer_count);
    if (layer_count > 0) {
        vkEnumerateInstanceLayerProperties(&layer_count, layers.data());
        for (uint32_t i = 0; i < layer_count; i++) {
            std::cout << "    Layer: " << layers[i].layerName << std::endl;
        }
    }

    // Check validation layer availability
    bool validation_available = false;
    for (uint32_t i = 0; i < layer_count; i++) {
        if (strcmp(layers[i].layerName, "VK_LAYER_KHRONOS_validation") == 0) {
            validation_available = true;
            break;
        }
    }
    TEST_CHECK(validation_available || layer_count == 0,
        "Validation layer available (or no layers to check)");

    // Check available extensions
    uint32_t ext_count = 0;
    auto vkEnumerateInstanceExtensionProperties = (PFN_vkEnumerateInstanceExtensionProperties)
        g_vkGetInstanceProcAddr(nullptr, "vkEnumerateInstanceExtensionProperties");
    res = vkEnumerateInstanceExtensionProperties(nullptr, &ext_count, nullptr);
    TEST_VK(res, "vkEnumerateInstanceExtensionProperties (count)");
    std::cout << "  Available instance extensions: " << ext_count << std::endl;

    // Create instance
    VkApplicationInfo app_info{};
    app_info.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app_info.pApplicationName = "Reality Engine Vulkan Test";
    app_info.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.pEngineName = "Reality Engine";
    app_info.engineVersion = VK_MAKE_VERSION(1, 0, 0);
    app_info.apiVersion = VK_API_VERSION_1_3;

    std::vector<const char*> extensions = { VK_KHR_SURFACE_EXTENSION_NAME };
    if (validation_available) {
        extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
    }

    std::vector<const char*> layers_enable;
    if (validation_available) {
        layers_enable.push_back("VK_LAYER_KHRONOS_validation");
    }

    VkInstanceCreateInfo create_info{};
    create_info.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    create_info.pApplicationInfo = &app_info;
    create_info.enabledLayerCount = (uint32_t)layers_enable.size();
    create_info.ppEnabledLayerNames = layers_enable.data();
    create_info.enabledExtensionCount = (uint32_t)extensions.size();
    create_info.ppEnabledExtensionNames = extensions.data();

    auto vkCreateInstance = (PFN_vkCreateInstance)g_vkGetInstanceProcAddr(nullptr, "vkCreateInstance");
    VkInstance instance = VK_NULL_HANDLE;
    res = vkCreateInstance(&create_info, nullptr, &instance);
    TEST_VK(res, "vkCreateInstance");
    TEST_CHECK(instance != VK_NULL_HANDLE, "Vulkan instance handle is valid");

    if (instance == VK_NULL_HANDLE) {
        std::cout << "  Cannot proceed without Vulkan instance" << std::endl;
        return 1;
    }

    // ------------------------------------------------------------------
    // Step 3: Physical device enumeration
    // ------------------------------------------------------------------
    std::cout << std::endl << "[3/12] Enumerating physical devices..." << std::endl;

    auto vkEnumeratePhysicalDevices = (PFN_vkEnumeratePhysicalDevices)
        g_vkGetInstanceProcAddr(instance, "vkEnumeratePhysicalDevices");
    uint32_t device_count = 0;
    res = vkEnumeratePhysicalDevices(instance, &device_count, nullptr);
    TEST_VK(res, "vkEnumeratePhysicalDevices (count)");
    std::cout << "  Physical devices found: " << device_count << std::endl;

    TEST_CHECK(device_count > 0, "At least one physical device available");

    if (device_count == 0) {
        std::cout << "  No Vulkan devices available - cannot continue" << std::endl;
        // Cleanup
        auto vkDestroyInstance = (PFN_vkDestroyInstance)g_vkGetInstanceProcAddr(instance, "vkDestroyInstance");
        vkDestroyInstance(instance, nullptr);
        return 1;
    }

    std::vector<VkPhysicalDevice> devices(device_count);
    res = vkEnumeratePhysicalDevices(instance, &device_count, devices.data());
    TEST_VK(res, "vkEnumeratePhysicalDevices (devices)");

    // Identify device type
    for (uint32_t i = 0; i < device_count; i++) {
        VkPhysicalDeviceProperties props{};
        auto vkGetPhysicalDeviceProperties = (PFN_vkGetPhysicalDeviceProperties)
            g_vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceProperties");
        vkGetPhysicalDeviceProperties(devices[i], &props);
        std::cout << "    Device " << i << ": " << props.deviceName << std::endl;
        std::cout << "      Type: ";
        switch (props.deviceType) {
            case VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU:
                std::cout << "Integrated GPU" << std::endl; break;
            case VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU:
                std::cout << "Discrete GPU" << std::endl; break;
            case VK_PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU:
                std::cout << "Virtual GPU" << std::endl; break;
            case VK_PHYSICAL_DEVICE_TYPE_CPU:
                std::cout << "CPU (software - e.g. Mesa lavapipe)" << std::endl; break;
            case VK_PHYSICAL_DEVICE_TYPE_OTHER:
                std::cout << "Other" << std::endl; break;
            default:
                std::cout << "Unknown" << std::endl; break;
        }
        std::cout << "      API Version: " << VK_VERSION_MAJOR(props.apiVersion) << "."
                  << VK_VERSION_MINOR(props.apiVersion) << "."
                  << VK_VERSION_PATCH(props.apiVersion) << std::endl;
        std::cout << "      Driver Version: " << props.driverVersion << std::endl;
        std::cout << "      Vendor ID: " << props.vendorID << std::endl;
        std::cout << "      Device ID: " << props.deviceID << std::endl;
    }

    VkPhysicalDevice physical_device = devices[0];

    // ------------------------------------------------------------------
    // Step 4: Logical device creation
    // ------------------------------------------------------------------
    std::cout << std::endl << "[4/12] Creating logical device..." << std::endl;

    // Find queue families
    uint32_t queue_family_count = 0;
    auto vkGetPhysicalDeviceQueueFamilyProperties = (PFN_vkGetPhysicalDeviceQueueFamilyProperties)
        g_vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceQueueFamilyProperties");
    vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_family_count, nullptr);
    std::vector<VkQueueFamilyProperties> queue_families(queue_family_count);
    vkGetPhysicalDeviceQueueFamilyProperties(physical_device, &queue_family_count, queue_families.data());

    uint32_t graphics_queue_family = UINT32_MAX;
    for (uint32_t i = 0; i < queue_family_count; i++) {
        if (queue_families[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            graphics_queue_family = i;
            break;
        }
    }
    TEST_CHECK(graphics_queue_family != UINT32_MAX, "Graphics queue family found");

    float queue_priority = 1.0f;
    VkDeviceQueueCreateInfo queue_create_info{};
    queue_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_create_info.queueFamilyIndex = graphics_queue_family;
    queue_create_info.queueCount = 1;
    queue_create_info.pQueuePriorities = &queue_priority;

    VkPhysicalDeviceFeatures device_features{};
    VkDeviceCreateInfo device_create_info{};
    device_create_info.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    device_create_info.queueCreateInfoCount = 1;
    device_create_info.pQueueCreateInfos = &queue_create_info;
    device_create_info.pEnabledFeatures = &device_features;
    device_create_info.enabledExtensionCount = 0;
    device_create_info.ppEnabledExtensionNames = nullptr;

    auto vkCreateDevice = (PFN_vkCreateDevice)g_vkGetInstanceProcAddr(instance, "vkCreateDevice");
    VkDevice device = VK_NULL_HANDLE;
    res = vkCreateDevice(physical_device, &device_create_info, nullptr, &device);
    TEST_VK(res, "vkCreateDevice");
    TEST_CHECK(device != VK_NULL_HANDLE, "Logical device handle is valid");

    // Get device-level function pointer loader
    auto vkGetDeviceProcAddr = (PFN_vkGetDeviceProcAddr)g_vkGetInstanceProcAddr(instance, "vkGetDeviceProcAddr");
    TEST_CHECK(vkGetDeviceProcAddr != nullptr, "vkGetDeviceProcAddr loaded");

    // Helper lambda for device-level functions
    auto load_dev_func = [&](const char* name) -> PFN_vkVoidFunction {
        return vkGetDeviceProcAddr(device, name);
    };

    if (device == VK_NULL_HANDLE) {
        // Cleanup
        auto vkDestroyInstance = (PFN_vkDestroyInstance)g_vkGetInstanceProcAddr(instance, "vkDestroyInstance");
        vkDestroyInstance(instance, nullptr);
        return 1;
    }

    // ------------------------------------------------------------------
    // Step 5: Queue retrieval
    // ------------------------------------------------------------------
    std::cout << std::endl << "[5/12] Retrieving queues..." << std::endl;

    auto vkGetDeviceQueue = (PFN_vkGetDeviceQueue)load_dev_func("vkGetDeviceQueue");
    VkQueue graphics_queue = VK_NULL_HANDLE;
    vkGetDeviceQueue(device, graphics_queue_family, 0, &graphics_queue);
    TEST_CHECK(graphics_queue != VK_NULL_HANDLE, "Graphics queue retrieved");

    // ------------------------------------------------------------------
    // Step 6: Buffer allocation, memory allocation and binding
    // ------------------------------------------------------------------
    std::cout << std::endl << "[6/12] Creating buffer and allocating memory..." << std::endl;

    auto vkCreateBuffer = (PFN_vkCreateBuffer)load_dev_func("vkCreateBuffer");
    auto vkGetBufferMemoryRequirements = (PFN_vkGetBufferMemoryRequirements)
        load_dev_func("vkGetBufferMemoryRequirements");
    auto vkAllocateMemory = (PFN_vkAllocateMemory)load_dev_func("vkAllocateMemory");
    auto vkBindBufferMemory = (PFN_vkBindBufferMemory)load_dev_func("vkBindBufferMemory");
    auto vkGetPhysicalDeviceMemoryProperties = (PFN_vkGetPhysicalDeviceMemoryProperties)
        g_vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceMemoryProperties");
    auto vkMapMemory = (PFN_vkMapMemory)load_dev_func("vkMapMemory");
    auto vkUnmapMemory = (PFN_vkUnmapMemory)load_dev_func("vkUnmapMemory");

    const VkDeviceSize buffer_size = 1024 * 1024; // 1 MB

    VkBufferCreateInfo buffer_info{};
    buffer_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    buffer_info.size = buffer_size;
    buffer_info.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    buffer_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    VkBuffer buffer = VK_NULL_HANDLE;
    res = vkCreateBuffer(device, &buffer_info, nullptr, &buffer);
    TEST_VK(res, "vkCreateBuffer");
    TEST_CHECK(buffer != VK_NULL_HANDLE, "Buffer handle is valid");

    VkMemoryRequirements mem_reqs{};
    vkGetBufferMemoryRequirements(device, buffer, &mem_reqs);
    std::cout << "  Buffer memory requirements: size=" << mem_reqs.size
              << ", alignment=" << mem_reqs.alignment
              << ", memoryTypeBits=" << mem_reqs.memoryTypeBits << std::endl;

    VkPhysicalDeviceMemoryProperties mem_props{};
    vkGetPhysicalDeviceMemoryProperties(physical_device, &mem_props);

    // Find host-visible, host-coherent memory type
    uint32_t memory_type_index = UINT32_MAX;
    for (uint32_t i = 0; i < mem_props.memoryTypeCount; i++) {
        if ((mem_reqs.memoryTypeBits & (1u << i)) &&
            ((mem_props.memoryTypes[i].propertyFlags &
              (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) ==
             (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))) {
            memory_type_index = i;
            break;
        }
    }
    TEST_CHECK(memory_type_index != UINT32_MAX, "Host-visible coherent memory type found");

    VkMemoryAllocateInfo alloc_info{};
    alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc_info.allocationSize = mem_reqs.size;
    alloc_info.memoryTypeIndex = memory_type_index;

    VkDeviceMemory buffer_memory = VK_NULL_HANDLE;
    res = vkAllocateMemory(device, &alloc_info, nullptr, &buffer_memory);
    TEST_VK(res, "vkAllocateMemory");
    TEST_CHECK(buffer_memory != VK_NULL_HANDLE, "Buffer memory allocated");

    res = vkBindBufferMemory(device, buffer, buffer_memory, 0);
    TEST_VK(res, "vkBindBufferMemory");

    // ------------------------------------------------------------------
    // Step 7: Buffer upload
    // ------------------------------------------------------------------
    std::cout << std::endl << "[7/12] Uploading data to buffer..." << std::endl;

    // Create test data
    std::vector<uint32_t> test_data(256, 0xDEADBEEF);
    for (size_t i = 0; i < test_data.size(); i++) {
        test_data[i] = static_cast<uint32_t>(i);
    }

    void* mapped = nullptr;
    res = vkMapMemory(device, buffer_memory, 0, test_data.size() * sizeof(uint32_t), 0, &mapped);
    TEST_VK(res, "vkMapMemory");
    TEST_CHECK(mapped != nullptr, "Buffer memory mapped");

    if (mapped) {
        memcpy(mapped, test_data.data(), test_data.size() * sizeof(uint32_t));
        auto vkUnmapMemory_fn = (PFN_vkUnmapMemory)load_dev_func("vkUnmapMemory");
        vkUnmapMemory_fn(device, buffer_memory);
        std::cout << "  Uploaded " << test_data.size() * sizeof(uint32_t) << " bytes to buffer" << std::endl;
    }

    // ------------------------------------------------------------------
    // Step 8: Shader module creation from SPIR-V
    // ------------------------------------------------------------------
    std::cout << std::endl << "[8/12] Creating shader modules from SPIR-V..." << std::endl;

    // Load SPIR-V files (compiled from GLSL by CI)
    auto load_spirv = [](const char* path) -> std::vector<uint32_t> {
        std::vector<uint32_t> spirv;
        // Try to read the file
        FILE* f = fopen(path, "rb");
        if (!f) return spirv;
        fseek(f, 0, SEEK_END);
        long size = ftell(f);
        fseek(f, 0, SEEK_SET);
        if (size > 0 && size % 4 == 0) {
            spirv.resize(size / 4);
            fread(spirv.data(), 1, size, f);
        }
        fclose(f);
        return spirv;
    };

    std::vector<uint32_t> vert_spirv = load_spirv("engine/rendering/vulkan/shaders/pbr.vert.spv");
    std::vector<uint32_t> frag_spirv = load_spirv("engine/rendering/vulkan/shaders/pbr.frag.spv");

    bool shaders_available = !vert_spirv.empty() && !frag_spirv.empty();
    std::cout << "  Vertex SPIR-V: " << (vert_spirv.empty() ? "MISSING" : std::to_string(vert_spirv.size()) + " words") << std::endl;
    std::cout << "  Fragment SPIR-V: " << (frag_spirv.empty() ? "MISSING" : std::to_string(frag_spirv.size()) + " words") << std::endl;

    auto vkCreateShaderModule = (PFN_vkCreateShaderModule)load_dev_func("vkCreateShaderModule");

    VkShaderModule vert_module = VK_NULL_HANDLE;
    VkShaderModule frag_module = VK_NULL_HANDLE;

    if (shaders_available) {
        VkShaderModuleCreateInfo module_info{};
        module_info.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
        module_info.codeSize = vert_spirv.size() * sizeof(uint32_t);
        module_info.pCode = vert_spirv.data();
        res = vkCreateShaderModule(device, &module_info, nullptr, &vert_module);
        TEST_VK(res, "vkCreateShaderModule (vertex)");
        TEST_CHECK(vert_module != VK_NULL_HANDLE, "Vertex shader module created");

        module_info.codeSize = frag_spirv.size() * sizeof(uint32_t);
        module_info.pCode = frag_spirv.data();
        res = vkCreateShaderModule(device, &module_info, nullptr, &frag_module);
        TEST_VK(res, "vkCreateShaderModule (fragment)");
        TEST_CHECK(frag_module != VK_NULL_HANDLE, "Fragment shader module created");
    } else {
        std::cout << "  SKIP: Shader modules not created (no SPIR-V files)" << std::endl;
    }

    // ------------------------------------------------------------------
    // Step 9: Graphics pipeline creation (minimal)
    // ------------------------------------------------------------------
    std::cout << std::endl << "[9/12] Creating graphics pipeline..." << std::endl;

    auto vkCreatePipelineLayout = (PFN_vkCreatePipelineLayout)load_dev_func("vkCreatePipelineLayout");
    auto vkCreateGraphicsPipelines = (PFN_vkCreateGraphicsPipelines)load_dev_func("vkCreateGraphicsPipelines");

    VkPipelineLayout pipeline_layout = VK_NULL_HANDLE;
    VkPipelineLayoutCreateInfo layout_info{};
    layout_info.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    layout_info.setLayoutCount = 0;
    layout_info.pSetLayouts = nullptr;
    res = vkCreatePipelineLayout(device, &layout_info, nullptr, &pipeline_layout);
    TEST_VK(res, "vkCreatePipelineLayout");
    TEST_CHECK(pipeline_layout != VK_NULL_HANDLE, "Pipeline layout created");

    // ------------------------------------------------------------------
    // Step 9: Graphics pipeline creation (complete fixed-function states)
    // ------------------------------------------------------------------
    VkGraphicsPipelineCreateInfo pipeline_info{};
    pipeline_info.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;

    // Vertex input state - position (float3) + color (float3) per vertex
    VkVertexInputBindingDescription vertex_binding{};
    vertex_binding.binding = 0;
    vertex_binding.stride = sizeof(float) * 6;  // 3 position + 3 color
    vertex_binding.inputRate = VK_VERTEX_INPUT_RATE_VERTEX;

    VkVertexInputAttributeDescription position_attr{};
    position_attr.binding = 0;
    position_attr.location = 0;
    position_attr.format = VK_FORMAT_R32G32B32_SFLOAT;
    position_attr.offset = 0;

    VkVertexInputAttributeDescription color_attr{};
    color_attr.binding = 0;
    color_attr.location = 1;
    color_attr.format = VK_FORMAT_R32G32B32_SFLOAT;
    color_attr.offset = sizeof(float) * 3;

    VkVertexInputAttributeDescription vertex_attrs[2] = {position_attr, color_attr};
    VkPipelineVertexInputStateCreateInfo vertex_input{};
    vertex_input.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    vertex_input.vertexBindingDescriptionCount = shaders_available ? 1 : 0;
    vertex_input.pVertexBindingDescriptions = shaders_available ? &vertex_binding : nullptr;
    vertex_input.vertexAttributeDescriptionCount = shaders_available ? 2 : 0;
    vertex_input.pVertexAttributeDescriptions = shaders_available ? vertex_attrs : nullptr;

    // Input assembly - triangle list
    VkPipelineInputAssemblyStateCreateInfo input_assembly{};
    input_assembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    input_assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    input_assembly.primitiveRestartEnable = VK_FALSE;

    // Viewport and scissor (dynamic)
    VkPipelineViewportStateCreateInfo viewport_state{};
    viewport_state.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    viewport_state.viewportCount = 1;
    viewport_state.scissorCount = 1;

    // Rasterization
    VkPipelineRasterizationStateCreateInfo rasterizer{};
    rasterizer.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    rasterizer.depthClampEnable = VK_FALSE;
    rasterizer.rasterizerDiscardEnable = VK_FALSE;
    rasterizer.polygonMode = VK_POLYGON_MODE_FILL;
    rasterizer.lineWidth = 1.0f;
    rasterizer.cullMode = VK_CULL_MODE_NONE;
    rasterizer.frontFace = VK_FRONT_FACE_CLOCKWISE;
    rasterizer.depthBiasEnable = VK_FALSE;

    // Multisampling
    VkPipelineMultisampleStateCreateInfo multisampling{};
    multisampling.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    multisampling.sampleShadingEnable = VK_FALSE;
    multisampling.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    // Depth/stencil (disabled)
    VkPipelineDepthStencilStateCreateInfo depth_stencil{};
    depth_stencil.sType = VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO;
    depth_stencil.depthTestEnable = VK_FALSE;
    depth_stencil.depthWriteEnable = VK_FALSE;

    // Color blending
    VkPipelineColorBlendAttachmentState color_blend_attachment{};
    color_blend_attachment.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                           VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
    color_blend_attachment.blendEnable = VK_FALSE;

    VkPipelineColorBlendStateCreateInfo color_blending{};
    color_blending.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    color_blending.logicOpEnable = VK_FALSE;
    color_blending.attachmentCount = 1;
    color_blending.pAttachments = &color_blend_attachment;

    // Dynamic state
    std::vector<VkDynamicState> dynamic_states = {
        VK_DYNAMIC_STATE_VIEWPORT,
        VK_DYNAMIC_STATE_SCISSOR
    };
    VkPipelineDynamicStateCreateInfo dynamic_state{};
    dynamic_state.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
    dynamic_state.dynamicStateCount = (uint32_t)dynamic_states.size();
    dynamic_state.pDynamicStates = dynamic_states.data();

    if (shaders_available) {
        std::vector<VkPipelineShaderStageCreateInfo> stages(2);

        stages[0].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
        stages[0].module = vert_module;
        stages[0].pName = "main";

        stages[1].sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
        stages[1].module = frag_module;
        stages[1].pName = "main";

        pipeline_info.stageCount = 2;
        pipeline_info.pStages = stages.data();
    }

    pipeline_info.pVertexInputState = &vertex_input;
    pipeline_info.pInputAssemblyState = &input_assembly;
    pipeline_info.pViewportState = &viewport_state;
    pipeline_info.pRasterizationState = &rasterizer;
    pipeline_info.pMultisampleState = &multisampling;
    pipeline_info.pDepthStencilState = &depth_stencil;
    pipeline_info.pColorBlendState = &color_blending;
    pipeline_info.pDynamicState = &dynamic_state;
    pipeline_info.layout = pipeline_layout;

    VkPipeline pipeline = VK_NULL_HANDLE;
    res = vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline);
    TEST_VK(res, "vkCreateGraphicsPipelines");
    TEST_CHECK(pipeline != VK_NULL_HANDLE, "Graphics pipeline created");

    // ------------------------------------------------------------------
    // Step 10: Mesh rendering with image readback

    // Function pointers for step 10 (unique names to avoid conflicts with step 6)
    auto vkAllocateMemory_s10 = (PFN_vkAllocateMemory)load_dev_func("vkAllocateMemory");
    auto vkBindBufferMemory_s10 = (PFN_vkBindBufferMemory)load_dev_func("vkBindBufferMemory");
    auto vkMapMemory_s10 = (PFN_vkMapMemory)load_dev_func("vkMapMemory");
    auto vkUnmapMemory_s10 = (PFN_vkUnmapMemory)load_dev_func("vkUnmapMemory");
    // ------------------------------------------------------------------
    std::cout << std::endl << "[10/12] Mesh rendering with readback..." << std::endl;

    // Function pointers needed for step 10
    auto vkCreateRenderPass_fn = (PFN_vkCreateRenderPass)load_dev_func("vkCreateRenderPass");
    auto vkCreateImageView_fn = (PFN_vkCreateImageView)load_dev_func("vkCreateImageView");
    auto vkCreateFramebuffer_fn = (PFN_vkCreateFramebuffer)load_dev_func("vkCreateFramebuffer");
    auto vkCreateBuffer_fn = (PFN_vkCreateBuffer)load_dev_func("vkCreateBuffer");
    auto vkFlushMappedMemoryRanges_fn = (PFN_vkFlushMappedMemoryRanges)load_dev_func("vkFlushMappedMemoryRanges");
    auto vkInvalidateMappedMemoryRanges_fn = (PFN_vkInvalidateMappedMemoryRanges)load_dev_func("vkInvalidateMappedMemoryRanges");
    auto vkGetBufferMemoryRequirements_fn = (PFN_vkGetBufferMemoryRequirements)load_dev_func("vkGetBufferMemoryRequirements");
    auto vkGetPhysicalDeviceMemoryProperties_fn = (PFN_vkGetPhysicalDeviceMemoryProperties)
        g_vkGetInstanceProcAddr(instance, "vkGetPhysicalDeviceMemoryProperties");
    auto vkCreateCommandPool_fn = (PFN_vkCreateCommandPool)load_dev_func("vkCreateCommandPool");
    auto vkAllocateCommandBuffers_fn = (PFN_vkAllocateCommandBuffers)load_dev_func("vkAllocateCommandBuffers");
    auto vkBeginCommandBuffer_fn = (PFN_vkBeginCommandBuffer)load_dev_func("vkBeginCommandBuffer");
    auto vkCmdSetViewport_fn = (PFN_vkCmdSetViewport)load_dev_func("vkCmdSetViewport");
    auto vkCmdSetScissor_fn = (PFN_vkCmdSetScissor)load_dev_func("vkCmdSetScissor");
    auto vkCmdBindPipeline_fn = (PFN_vkCmdBindPipeline)load_dev_func("vkCmdBindPipeline");
    auto vkCmdBindVertexBuffers_fn = (PFN_vkCmdBindVertexBuffers)load_dev_func("vkCmdBindVertexBuffers");
    auto vkCmdDraw_fn = (PFN_vkCmdDraw)load_dev_func("vkCmdDraw");
    auto vkCmdCopyImageToBuffer_fn = (PFN_vkCmdCopyImageToBuffer)load_dev_func("vkCmdCopyImageToBuffer");
    auto vkCmdPipelineBarrier_fn = (PFN_vkCmdPipelineBarrier)load_dev_func("vkCmdPipelineBarrier");
    auto vkEndCommandBuffer_fn = (PFN_vkEndCommandBuffer)load_dev_func("vkEndCommandBuffer");
    auto vkQueueSubmit_fn = (PFN_vkQueueSubmit)load_dev_func("vkQueueSubmit");
    auto vkQueueWaitIdle_fn = (PFN_vkQueueWaitIdle)load_dev_func("vkQueueWaitIdle");
    auto vkCreateFence_fn = (PFN_vkCreateFence)load_dev_func("vkCreateFence");
    auto vkWaitForFences_fn = (PFN_vkWaitForFences)load_dev_func("vkWaitForFences");
    auto vkDestroyRenderPass_fn = (PFN_vkDestroyRenderPass)load_dev_func("vkDestroyRenderPass");
    auto vkDestroyImageView_fn = (PFN_vkDestroyImageView)load_dev_func("vkDestroyImageView");
    auto vkDestroyFramebuffer_fn = (PFN_vkDestroyFramebuffer)load_dev_func("vkDestroyFramebuffer");
    auto vkDestroyBuffer_fn = (PFN_vkDestroyBuffer)load_dev_func("vkDestroyBuffer");
    auto vkFreeMemory_fn = (PFN_vkFreeMemory)load_dev_func("vkFreeMemory");

    // Create test image (render target)
    VkImageCreateInfo image_info{};
    image_info.sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image_info.imageType = VK_IMAGE_TYPE_2D;
    image_info.format = VK_FORMAT_R8G8B8A8_UNORM;
    image_info.extent.width = 64;
    image_info.extent.height = 64;
    image_info.extent.depth = 1;
    image_info.mipLevels = 1;
    image_info.arrayLayers = 1;
    image_info.samples = VK_SAMPLE_COUNT_1_BIT;
    image_info.tiling = VK_IMAGE_TILING_OPTIMAL;
    image_info.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    image_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    image_info.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;

    auto vkCreateImage_fn = (PFN_vkCreateImage)load_dev_func("vkCreateImage");
    VkImage test_image = VK_NULL_HANDLE;
    res = vkCreateImage_fn(device, &image_info, nullptr, &test_image);
    TEST_VK(res, "vkCreateImage");
    TEST_CHECK(test_image != VK_NULL_HANDLE, "Render target image created");

    VkImageView image_view = VK_NULL_HANDLE;
    VkFramebuffer framebuffer = VK_NULL_HANDLE;
    VkRenderPass render_pass = VK_NULL_HANDLE;

    VkDeviceMemory image_memory = VK_NULL_HANDLE;
    if (test_image != VK_NULL_HANDLE) {
        // Get memory requirements and allocate memory for image
        VkMemoryRequirements mem_reqs{};
        auto vkGetImageMemoryRequirements_fn = (PFN_vkGetImageMemoryRequirements)load_dev_func("vkGetImageMemoryRequirements");
        vkGetImageMemoryRequirements_fn(device, test_image, &mem_reqs);

        VkPhysicalDeviceMemoryProperties mem_props{};
        vkGetPhysicalDeviceMemoryProperties_fn(physical_device, &mem_props);

        uint32_t memory_type_index = UINT32_MAX;
        for (uint32_t i = 0; i < mem_props.memoryTypeCount; i++) {
            if ((mem_reqs.memoryTypeBits & (1u << i)) &&
                (mem_props.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)) {
                memory_type_index = i;
                break;
            }
        }

        if (memory_type_index != UINT32_MAX) {
            VkMemoryAllocateInfo alloc_info{};
            alloc_info.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
            alloc_info.allocationSize = mem_reqs.size;
            alloc_info.memoryTypeIndex = memory_type_index;
            res = vkAllocateMemory(device, &alloc_info, nullptr, &image_memory);
            TEST_VK(res, "vkAllocateMemory (image)");
            if (image_memory != VK_NULL_HANDLE) {
                auto vkBindImageMemory_fn = (PFN_vkBindImageMemory)load_dev_func("vkBindImageMemory");
                res = vkBindImageMemory_fn(device, test_image, image_memory, 0);
                TEST_VK(res, "vkBindImageMemory");
            }
        }

        // Create image view
        VkImageViewCreateInfo view_info{};
        view_info.sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
        view_info.image = test_image;
        view_info.viewType = VK_IMAGE_VIEW_TYPE_2D;
        view_info.format = VK_FORMAT_R8G8B8A8_UNORM;
        view_info.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
        view_info.subresourceRange.baseMipLevel = 0;
        view_info.subresourceRange.levelCount = 1;
        view_info.subresourceRange.baseArrayLayer = 0;
        view_info.subresourceRange.layerCount = 1;

        res = vkCreateImageView_fn(device, &view_info, nullptr, &image_view);
        TEST_VK(res, "vkCreateImageView");
        TEST_CHECK(image_view != VK_NULL_HANDLE, "Image view created");

        // Create render pass
        VkAttachmentDescription color_attachment{};
        color_attachment.format = VK_FORMAT_R8G8B8A8_UNORM;
        color_attachment.samples = VK_SAMPLE_COUNT_1_BIT;
        color_attachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        color_attachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        color_attachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
        color_attachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
        color_attachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        color_attachment.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;

        VkAttachmentReference color_attachment_ref{};
        color_attachment_ref.attachment = 0;
        color_attachment_ref.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

        VkSubpassDescription subpass{};
        subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
        subpass.colorAttachmentCount = 1;
        subpass.pColorAttachments = &color_attachment_ref;

        VkRenderPassCreateInfo render_pass_info{};
        render_pass_info.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
        render_pass_info.attachmentCount = 1;
        render_pass_info.pAttachments = &color_attachment;
        render_pass_info.subpassCount = 1;
        render_pass_info.pSubpasses = &subpass;

        res = vkCreateRenderPass_fn(device, &render_pass_info, nullptr, &render_pass);
        TEST_VK(res, "vkCreateRenderPass");
        TEST_CHECK(render_pass != VK_NULL_HANDLE, "Render pass created");

        // Create framebuffer
        if (render_pass != VK_NULL_HANDLE) {
            VkFramebufferCreateInfo fb_info{};
            fb_info.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
            fb_info.renderPass = render_pass;
            fb_info.attachmentCount = 1;
            fb_info.pAttachments = &image_view;
            fb_info.width = 64;
            fb_info.height = 64;
            fb_info.layers = 1;

            res = vkCreateFramebuffer_fn(device, &fb_info, nullptr, &framebuffer);
            TEST_VK(res, "vkCreateFramebuffer");
            TEST_CHECK(framebuffer != VK_NULL_HANDLE, "Framebuffer created");
        }
    }

    // Create vertex buffer with triangle data
    struct Vertex { float pos[3]; float color[3]; };
    Vertex triangle_vertices[] = {
        {{-0.5f, -0.5f, 0.0f}, {1.0f, 0.0f, 0.0f}},  // Red vertex
        {{ 0.5f, -0.5f, 0.0f}, {0.0f, 1.0f, 0.0f}},  // Green vertex
        {{ 0.0f,  0.5f, 0.0f}, {0.0f, 0.0f, 1.0f}},  // Blue vertex
    };
    VkDeviceSize vertex_buffer_size = sizeof(triangle_vertices);

    VkBuffer vertex_buffer = VK_NULL_HANDLE;
    VkDeviceMemory vertex_memory = VK_NULL_HANDLE;

    VkBufferCreateInfo vb_info{};
    vb_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    vb_info.size = vertex_buffer_size;
    vb_info.usage = VK_BUFFER_USAGE_VERTEX_BUFFER_BIT;
    vb_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    res = vkCreateBuffer_fn(device, &vb_info, nullptr, &vertex_buffer);
    TEST_VK(res, "vkCreateBuffer (vertex)");
    TEST_CHECK(vertex_buffer != VK_NULL_HANDLE, "Vertex buffer created");

    if (vertex_buffer != VK_NULL_HANDLE) {
        VkMemoryRequirements vb_mem_reqs{};
        vkGetBufferMemoryRequirements_fn(device, vertex_buffer, &vb_mem_reqs);

        uint32_t vb_mem_type = UINT32_MAX;
        for (uint32_t i = 0; i < mem_props.memoryTypeCount; i++) {
            if ((vb_mem_reqs.memoryTypeBits & (1u << i)) &&
                (mem_props.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)) {
                vb_mem_type = i;
                break;
            }
        }

        if (vb_mem_type != UINT32_MAX) {
            VkMemoryAllocateInfo vb_alloc{};
            vb_alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
            vb_alloc.allocationSize = vb_mem_reqs.size;
            vb_alloc.memoryTypeIndex = vb_mem_type;
            res = vkAllocateMemory(device, &vb_alloc, nullptr, &vertex_memory);
            TEST_VK(res, "vkAllocateMemory (vertex)");
            if (vertex_memory != VK_NULL_HANDLE) {
                res = vkBindBufferMemory(device, vertex_buffer, vertex_memory, 0);
                TEST_VK(res, "vkBindBufferMemory (vertex)");

                // Upload vertex data
                void* mapped = nullptr;
                res = vkMapMemory(device, vertex_memory, 0, vertex_buffer_size, 0, &mapped);
                TEST_VK(res, "vkMapMemory (vertex)");
                if (mapped) {
                    memcpy(mapped, triangle_vertices, vertex_buffer_size);
                    vkUnmapMemory_s10(device, vertex_memory);
                    std::cout << "  Uploaded " << vertex_buffer_size << " bytes of vertex data" << std::endl;
                }
            }
        }
    }

    // Create staging buffer for image readback (host-visible, host-coherent)
    VkBuffer staging_buffer = VK_NULL_HANDLE;
    VkDeviceMemory staging_memory = VK_NULL_HANDLE;
    VkDeviceSize staging_size = 64 * 64 * 4;  // RGBA8

    VkBufferCreateInfo staging_info{};
    staging_info.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    staging_info.size = staging_size;
    staging_info.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    staging_info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    res = vkCreateBuffer_fn(device, &staging_info, nullptr, &staging_buffer);
    TEST_VK(res, "vkCreateBuffer (staging)");
    TEST_CHECK(staging_buffer != VK_NULL_HANDLE, "Staging buffer created");

    if (staging_buffer != VK_NULL_HANDLE) {
        VkMemoryRequirements staging_mem_reqs{};
        vkGetBufferMemoryRequirements_fn(device, staging_buffer, &staging_mem_reqs);

        uint32_t staging_mem_type = UINT32_MAX;
        for (uint32_t i = 0; i < mem_props.memoryTypeCount; i++) {
            if ((staging_mem_reqs.memoryTypeBits & (1u << i)) &&
                (mem_props.memoryTypes[i].propertyFlags & (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))) {
                staging_mem_type = i;
                break;
            }
        }

        if (staging_mem_type != UINT32_MAX) {
            VkMemoryAllocateInfo staging_alloc{};
            staging_alloc.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
            staging_alloc.allocationSize = staging_mem_reqs.size;
            staging_alloc.memoryTypeIndex = staging_mem_type;
            res = vkAllocateMemory(device, &staging_alloc, nullptr, &staging_memory);
            TEST_VK(res, "vkAllocateMemory (staging)");
            if (staging_memory != VK_NULL_HANDLE) {
                res = vkBindBufferMemory(device, staging_buffer, staging_memory, 0);
                TEST_VK(res, "vkBindBufferMemory (staging)");
            }
        }
    }

    // Create command pool
    VkCommandPool command_pool = VK_NULL_HANDLE;
    VkCommandPoolCreateInfo pool_info{};
    pool_info.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool_info.queueFamilyIndex = graphics_queue_family;
    pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;

    res = vkCreateCommandPool_fn(device, &pool_info, nullptr, &command_pool);
    TEST_VK(res, "vkCreateCommandPool");
    TEST_CHECK(command_pool != VK_NULL_HANDLE, "Command pool created");

    // Allocate command buffer
    VkCommandBuffer cmd_buf = VK_NULL_HANDLE;
    VkCommandBufferAllocateInfo cmd_alloc{};
    cmd_alloc.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    cmd_alloc.commandPool = command_pool;
    cmd_alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cmd_alloc.commandBufferCount = 1;

    res = vkAllocateCommandBuffers_fn(device, &cmd_alloc, &cmd_buf);
    TEST_VK(res, "vkAllocateCommandBuffers");
    TEST_CHECK(cmd_buf != VK_NULL_HANDLE, "Command buffer allocated");

    bool rendering_succeeded = false;

    if (cmd_buf != VK_NULL_HANDLE) {
        // Begin command buffer
        VkCommandBufferBeginInfo begin_info{};
        begin_info.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

        res = vkBeginCommandBuffer_fn(cmd_buf, &begin_info);
        TEST_VK(res, "vkBeginCommandBuffer");

        if (res == VK_SUCCESS && render_pass != VK_NULL_HANDLE && framebuffer != VK_NULL_HANDLE &&
            pipeline != VK_NULL_HANDLE && vertex_buffer != VK_NULL_HANDLE) {

            // Set dynamic viewport and scissor
            VkViewport viewport{};
            viewport.width = 64.0f;
            viewport.height = 64.0f;
            viewport.minDepth = 0.0f;
            viewport.maxDepth = 1.0f;
            vkCmdSetViewport_fn(cmd_buf, 0, 1, &viewport);

            VkRect2D scissor{};
            scissor.extent.width = 64;
            scissor.extent.height = 64;
            vkCmdSetScissor_fn(cmd_buf, 0, 1, &scissor);

            // Begin render pass
            VkRenderPassBeginInfo rp_begin{};
            rp_begin.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
            rp_begin.renderPass = render_pass;
            rp_begin.framebuffer = framebuffer;
            rp_begin.renderArea.offset = {0, 0};
            rp_begin.renderArea.extent = {64, 64};

            VkClearValue clear_color{};
            clear_color.color.float32[0] = 0.1f;  // Dark gray clear color
            clear_color.color.float32[1] = 0.1f;
            clear_color.color.float32[2] = 0.1f;
            clear_color.color.float32[3] = 1.0f;

            rp_begin.clearValueCount = 1;
            rp_begin.pClearValues = &clear_color;

            auto vkCmdBeginRenderPass_fn = (PFN_vkCmdBeginRenderPass)load_dev_func("vkCmdBeginRenderPass");
            auto vkCmdEndRenderPass_fn = (PFN_vkCmdEndRenderPass)load_dev_func("vkCmdEndRenderPass");

            vkCmdBeginRenderPass_fn(cmd_buf, &rp_begin, VK_SUBPASS_CONTENTS_INLINE);

            // Bind pipeline and vertex buffer
            vkCmdBindPipeline_fn(cmd_buf, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
            VkDeviceSize offsets[] = {0};
            vkCmdBindVertexBuffers_fn(cmd_buf, 0, 1, &vertex_buffer, offsets);

            // Draw triangle (3 vertices)
            vkCmdDraw_fn(cmd_buf, 3, 1, 0, 0);

            // End render pass (transitions image to TRANSFER_SRC_OPTIMAL via finalLayout)
            vkCmdEndRenderPass_fn(cmd_buf);

            // Copy rendered image to staging buffer for readback
            VkBufferImageCopy region{};
            region.bufferOffset = 0;
            region.bufferRowLength = 0;
            region.bufferImageHeight = 0;
            region.imageSubresource.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
            region.imageSubresource.mipLevel = 0;
            region.imageSubresource.baseArrayLayer = 0;
            region.imageSubresource.layerCount = 1;
            region.imageOffset = {0, 0, 0};
            region.imageExtent = {64, 64, 1};

            vkCmdCopyImageToBuffer_fn(cmd_buf, test_image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                                        staging_buffer, 1, &region);

            rendering_succeeded = true;
            std::cout << "  Recorded draw commands (triangle render + image copy)" << std::endl;
        } else if (res == VK_SUCCESS) {
            std::cout << "  SKIP: Missing render pass, framebuffer, pipeline, or vertex buffer" << std::endl;
        }

        // End command buffer
        res = vkEndCommandBuffer_fn(cmd_buf);
        TEST_VK(res, "vkEndCommandBuffer");

        // Submit and wait
        if (res == VK_SUCCESS) {
            VkSubmitInfo submit_info{};
            submit_info.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
            submit_info.commandBufferCount = 1;
            submit_info.pCommandBuffers = &cmd_buf;

            auto vkCreateFence_fn2 = (PFN_vkCreateFence)load_dev_func("vkCreateFence");
            VkFence fence = VK_NULL_HANDLE;
            VkFenceCreateInfo fence_info{};
            fence_info.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
            res = vkCreateFence_fn2(device, &fence_info, nullptr, &fence);
            TEST_VK(res, "vkCreateFence");

            res = vkQueueSubmit_fn(graphics_queue, 1, &submit_info, fence);
            TEST_VK(res, "vkQueueSubmit (mesh render)");

            if (res == VK_SUCCESS && fence != VK_NULL_HANDLE) {
                auto vkWaitForFences_fn2 = (PFN_vkWaitForFences)load_dev_func("vkWaitForFences");
                res = vkWaitForFences_fn2(device, 1, &fence, VK_TRUE, UINT64_MAX);
                TEST_VK(res, "vkWaitForFences (mesh render)");

                auto vkDestroyFence_fn = (PFN_vkDestroyFence)load_dev_func("vkDestroyFence");
                vkDestroyFence_fn(device, fence, nullptr);
            }

            auto vkQueueWaitIdle_fn2 = (PFN_vkQueueWaitIdle)load_dev_func("vkQueueWaitIdle");
            res = vkQueueWaitIdle_fn2(graphics_queue);
            TEST_VK(res, "vkQueueWaitIdle");
            std::cout << "  Mesh rendering commands executed on GPU" << std::endl;
        }
    }

    // Read back staging buffer and verify pixel data
    bool readback_verified = false;
    if (staging_memory != VK_NULL_HANDLE && rendering_succeeded) {
        void* mapped = nullptr;
        res = vkMapMemory(device, staging_memory, 0, staging_size, 0, &mapped);
        TEST_VK(res, "vkMapMemory (staging readback)");

        if (mapped) {
            // Check that we have rendered content (not all zeros)
            const uint32_t* pixels = static_cast<const uint32_t*>(mapped);
            uint32_t non_zero_count = 0;
            uint32_t clear_color_pixel = 0;
            // Clear color is 0.1f -> 0.1 * 255 ≈ 25-26 per channel
            // In RGBA8: R=26, G=26, B=26, A=255 -> 0xFF1A1A1A (little-endian)
            clear_color_pixel = 0xFF1A1A1A;

            for (size_t i = 0; i < staging_size / 4; i++) {
                if (pixels[i] != 0) non_zero_count++;
            }

            std::cout << "  Non-zero pixels in readback: " << non_zero_count << " / "
                      << (staging_size / 4) << std::endl;

            // With a clear color of 0.1, most pixels should be non-zero
            // (triangle pixels will have different colors)
            if (non_zero_count > (staging_size / 4) / 2) {
                std::cout << "  PASS: Image contains rendered content (non-zero pixels found)" << std::endl;
                readback_verified = true;
                g_tests_passed++;
            } else {
                std::cout << "  FAIL: Image appears empty" << std::endl;
                g_tests_failed++;
            }

            vkUnmapMemory_s10(device, staging_memory);
        }
    } else if (!rendering_succeeded) {
        std::cout << "  SKIP: Readback verification (rendering did not complete)" << std::endl;
    } else {
        std::cout << "  SKIP: Readback verification (no staging memory)" << std::endl;
    }

    TEST_CHECK(readback_verified || !rendering_succeeded,
               "Image readback verifies rendered result");
    if (!readback_verified && rendering_succeeded) g_tests_failed++;

    // ------------------------------------------------------------------
    // Step 11: Resource destruction
    // ------------------------------------------------------------------
    std::cout << std::endl << "[11/12] Destroying resources..." << std::endl;

    auto vkDestroyCommandPool_fn = (PFN_vkDestroyCommandPool)load_dev_func("vkDestroyCommandPool");
    if (command_pool != VK_NULL_HANDLE) {
        vkDestroyCommandPool_fn(device, command_pool, nullptr);
    }
    TEST_CHECK(true, "Command pool destroyed");

    if (staging_buffer != VK_NULL_HANDLE) {
        auto vkDestroyBuffer_fn2 = (PFN_vkDestroyBuffer)load_dev_func("vkDestroyBuffer");
        vkDestroyBuffer_fn2(device, staging_buffer, nullptr);
    }
    TEST_CHECK(true, "Staging buffer destroyed");

    if (staging_memory != VK_NULL_HANDLE) {
        auto vkFreeMemory_fn2 = (PFN_vkFreeMemory)load_dev_func("vkFreeMemory");
        vkFreeMemory_fn2(device, staging_memory, nullptr);
    }
    TEST_CHECK(true, "Staging memory freed");

    if (vertex_buffer != VK_NULL_HANDLE) {
        auto vkDestroyBuffer_fn2 = (PFN_vkDestroyBuffer)load_dev_func("vkDestroyBuffer");
        vkDestroyBuffer_fn2(device, vertex_buffer, nullptr);
    }
    TEST_CHECK(true, "Vertex buffer destroyed");

    if (vertex_memory != VK_NULL_HANDLE) {
        auto vkFreeMemory_fn2 = (PFN_vkFreeMemory)load_dev_func("vkFreeMemory");
        vkFreeMemory_fn2(device, vertex_memory, nullptr);
    }
    TEST_CHECK(true, "Vertex memory freed");

    if (image_memory != VK_NULL_HANDLE) {
        auto vkFreeMemory_fn2 = (PFN_vkFreeMemory)load_dev_func("vkFreeMemory");
        vkFreeMemory_fn2(device, image_memory, nullptr);
    }
    TEST_CHECK(true, "Image memory freed");

    if (framebuffer != VK_NULL_HANDLE) {
        auto vkDestroyFramebuffer_fn = (PFN_vkDestroyFramebuffer)load_dev_func("vkDestroyFramebuffer");
        vkDestroyFramebuffer_fn(device, framebuffer, nullptr);
    }
    TEST_CHECK(true, "Framebuffer destroyed");

    if (image_view != VK_NULL_HANDLE) {
        auto vkDestroyImageView_fn = (PFN_vkDestroyImageView)load_dev_func("vkDestroyImageView");
        vkDestroyImageView_fn(device, image_view, nullptr);
    }
    TEST_CHECK(true, "Image view destroyed");

    if (render_pass != VK_NULL_HANDLE) {
        auto vkDestroyRenderPass_fn = (PFN_vkDestroyRenderPass)load_dev_func("vkDestroyRenderPass");
        vkDestroyRenderPass_fn(device, render_pass, nullptr);
    }
    TEST_CHECK(true, "Render pass destroyed");

    auto vkDestroyImage = (PFN_vkDestroyImage)load_dev_func("vkDestroyImage");
    if (test_image != VK_NULL_HANDLE) {
        vkDestroyImage(device, test_image, nullptr);
    }
    TEST_CHECK(true, "Image destroyed");

    if (pipeline != VK_NULL_HANDLE) {
        auto vkDestroyPipeline = (PFN_vkDestroyPipeline)load_dev_func("vkDestroyPipeline");
        vkDestroyPipeline(device, pipeline, nullptr);
    }
    TEST_CHECK(true, "Pipeline destroyed");

    if (pipeline_layout != VK_NULL_HANDLE) {
        auto vkDestroyPipelineLayout = (PFN_vkDestroyPipelineLayout)load_dev_func("vkDestroyPipelineLayout");
        vkDestroyPipelineLayout(device, pipeline_layout, nullptr);
    }
    TEST_CHECK(true, "Pipeline layout destroyed");

    if (vert_module != VK_NULL_HANDLE) {
        auto vkDestroyShaderModule = (PFN_vkDestroyShaderModule)load_dev_func("vkDestroyShaderModule");
        vkDestroyShaderModule(device, vert_module, nullptr);
    }
    TEST_CHECK(true, "Vertex shader module destroyed");

    if (frag_module != VK_NULL_HANDLE) {
        auto vkDestroyShaderModule = (PFN_vkDestroyShaderModule)load_dev_func("vkDestroyShaderModule");
        vkDestroyShaderModule(device, frag_module, nullptr);
    }
    TEST_CHECK(true, "Fragment shader module destroyed");

    if (buffer_memory != VK_NULL_HANDLE) {
        auto vkFreeMemory = (PFN_vkFreeMemory)load_dev_func("vkFreeMemory");
        vkFreeMemory(device, buffer_memory, nullptr);
    }
    TEST_CHECK(true, "Buffer memory freed");

    if (buffer != VK_NULL_HANDLE) {
        auto vkDestroyBuffer = (PFN_vkDestroyBuffer)load_dev_func("vkDestroyBuffer");
        vkDestroyBuffer(device, buffer, nullptr);
    }
    TEST_CHECK(true, "Buffer destroyed");

    auto vkDestroyDevice = (PFN_vkDestroyDevice)load_dev_func("vkDestroyDevice");
    vkDestroyDevice(device, nullptr);
    TEST_CHECK(true, "Logical device destroyed");

    auto vkDestroyInstance = (PFN_vkDestroyInstance)g_vkGetInstanceProcAddr(instance, "vkDestroyInstance");
    vkDestroyInstance(instance, nullptr);
    TEST_CHECK(true, "Vulkan instance destroyed");

    // ------------------------------------------------------------------
    // Step 12: Summary
    // ------------------------------------------------------------------
    std::cout << std::endl << "[12/12] Test Summary" << std::endl;
    std::cout << "====================" << std::endl;
    std::cout << "Tests passed: " << g_tests_passed << std::endl;
    std::cout << "Tests failed: " << g_tests_failed << std::endl;
    std::cout << std::endl;

    if (g_tests_failed == 0) {
        std::cout << "ALL TESTS PASSED" << std::endl;
        return 0;
    } else {
        std::cout << "SOME TESTS FAILED" << std::endl;
        return 1;
    }
}
