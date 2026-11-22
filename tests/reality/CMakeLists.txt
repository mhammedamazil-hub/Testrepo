# Reality Engine Phase 1 Tests
add_executable(test_ecs
    test_ecs.cpp
)
target_link_libraries(test_ecs PRIVATE reality_ecs reality_core)
target_include_directories(test_ecs PRIVATE
    ${CMAKE_SOURCE_DIR}/../../engine/core
    ${CMAKE_SOURCE_DIR}/../../engine/ecs
)
add_test(NAME test_ecs COMMAND test_ecs)

add_executable(test_transform
    test_transform.cpp
)
target_link_libraries(test_transform PRIVATE reality_ecs reality_core)
target_include_directories(test_transform PRIVATE
    ${CMAKE_SOURCE_DIR}/../../engine/core
    ${CMAKE_SOURCE_DIR}/../../engine/ecs
)
add_test(NAME test_transform COMMAND test_transform)

add_executable(test_scene
    test_scene.cpp
)
target_link_libraries(test_scene PRIVATE reality_scene reality_ecs reality_core reality_assets)
target_include_directories(test_scene PRIVATE
    ${CMAKE_SOURCE_DIR}/../../engine/core
    ${CMAKE_SOURCE_DIR}/../../engine/ecs
    ${CMAKE_SOURCE_DIR}/../../engine/scene
    ${CMAKE_SOURCE_DIR}/../../engine/assets
)
add_test(NAME test_scene COMMAND test_scene)

add_executable(test_entity_id
    test_entity_id.cpp
)
target_link_libraries(test_entity_id PRIVATE reality_ecs reality_core)
target_include_directories(test_entity_id PRIVATE
    ${CMAKE_SOURCE_DIR}/../../engine/core
    ${CMAKE_SOURCE_DIR}/../../engine/ecs
)
add_test(NAME test_entity_id COMMAND test_entity_id)


add_executable(test_jolt_physics
    test_jolt_physics.cpp
)
target_link_libraries(test_jolt_physics PRIVATE
    reality_physics
    reality_world
    reality_ecs
    reality_core
    reality_rendering
    reality_platform
    reality_diagnostics
)
target_include_directories(test_jolt_physics PRIVATE
    ${CMAKE_SOURCE_DIR}/../../engine/core
    ${CMAKE_SOURCE_DIR}/../../engine/ecs
    ${CMAKE_SOURCE_DIR}/../../engine/world
    ${CMAKE_SOURCE_DIR}/../../engine/physics
    ${CMAKE_SOURCE_DIR}/../../engine/rendering
    ${CMAKE_SOURCE_DIR}/../../engine/platform
    ${CMAKE_SOURCE_DIR}/../../engine/diagnostics
)
add_test(NAME test_jolt_physics COMMAND test_jolt_physics)

# Vulkan execution test - requires Vulkan ICD
if(REALITY_HAS_VULKAN)
    add_executable(test_vulkan_execution
        test_vulkan_execution.cpp
    )
    target_link_libraries(test_vulkan_execution PRIVATE
        reality_rendering
        reality_core
    )
    target_include_directories(test_vulkan_execution PRIVATE
        ${CMAKE_SOURCE_DIR}/../../engine/core
        ${CMAKE_SOURCE_DIR}/../../engine/rendering
        ${CMAKE_SOURCE_DIR}/../../engine/rendering/vulkan
    )
    add_test(NAME test_vulkan_execution COMMAND test_vulkan_execution)
    set_tests_properties(test_vulkan_execution PROPERTIES
        ENVIRONMENT "VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json")
endif()
