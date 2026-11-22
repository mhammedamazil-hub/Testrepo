add_library(reality_rendering STATIC
    renderer.cpp
    headless_renderer.cpp
    vulkan/vulkan_renderer.cpp
    vulkan/vulkan_rhi.cpp
)

target_include_directories(reality_rendering PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/vulkan
    ${CMAKE_CURRENT_SOURCE_DIR}/rhi
)

# Vulkan headers and loader
set(VULKAN_HEADERS_DIR "${CMAKE_SOURCE_DIR}/../../third_party/Vulkan-Headers" CACHE PATH "Path to Vulkan-Headers")
set(VULKAN_LOADER_DIR "${CMAKE_SOURCE_DIR}/../../third_party/Vulkan-Loader" CACHE PATH "Path to Vulkan-Loader")

if(EXISTS "${VULKAN_HEADERS_DIR}/include/vulkan/vulkan.h")
    target_include_directories(reality_rendering PUBLIC "${VULKAN_HEADERS_DIR}/include")
    target_compile_definitions(reality_rendering PUBLIC REALITY_HAS_VULKAN)
    message(STATUS "Vulkan headers found at ${VULKAN_HEADERS_DIR}")
else()
    message(WARNING "Vulkan headers not found at ${VULKAN_HEADERS_DIR} - Vulkan renderer will be stubbed")
endif()

if(EXISTS "${VULKAN_LOADER_DIR}/loader")
    message(STATUS "Vulkan loader source found at ${VULKAN_LOADER_DIR} (not built - headers only)")
else()
    message(STATUS "Vulkan loader source not found at ${VULKAN_LOADER_DIR}")
endif()

target_link_libraries(reality_rendering PUBLIC reality_core)
target_include_directories(reality_rendering PUBLIC ${CMAKE_SOURCE_DIR})

# Note: Vulkan Loader is not built as a library here since there is no
# Vulkan ICD available on this headless machine. The loader provides the
# runtime Vulkan dispatch layer, which is only needed when actually running
# on a GPU. For headless compilation, headers are sufficient.
# On systems with Vulkan, link against -lvulkan or build Vulkan-Loader separately.