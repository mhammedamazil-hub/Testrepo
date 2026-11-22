add_library(reality_world STATIC
    world.cpp
)

target_include_directories(reality_world PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_world PUBLIC reality_ecs reality_core)
target_include_directories(reality_world PUBLIC ${CMAKE_SOURCE_DIR})
