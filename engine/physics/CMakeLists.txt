add_library(reality_physics STATIC
    physics_world.cpp
    physics_body.cpp
)

target_include_directories(reality_physics PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_physics PUBLIC reality_ecs reality_core)

if(TARGET Jolt)
    target_link_libraries(reality_physics PUBLIC Jolt)
    target_compile_definitions(reality_physics PUBLIC REALITY_HAS_JOLT)
endif()
target_include_directories(reality_physics PUBLIC ${CMAKE_SOURCE_DIR} ${JOLT_PHYSICS_SOURCE_DIR})
