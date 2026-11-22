add_library(reality_rendering STATIC
    renderer.cpp
    headless_renderer.cpp
)

if(REALITY_HAS_VULKAN)
    target_sources(reality_rendering PRIVATE
        vulkan/vulkan_rhi.cpp
        vulkan/vulkan_renderer.cpp
    )
    target_include_directories(reality_rendering PRIVATE
        ${VULKAN_HEADERS_DIR}/include
        ${VULKAN_LOADER_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/vulkan
    )
endif()

target_include_directories(reality_rendering PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_rendering PUBLIC reality_core)
target_include_directories(reality_rendering PUBLIC ${CMAKE_SOURCE_DIR})
