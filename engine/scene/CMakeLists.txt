add_library(reality_scene STATIC
    scene.cpp
)

target_include_directories(reality_scene PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_scene PUBLIC reality_ecs reality_core reality_assets)
target_include_directories(reality_scene PUBLIC ${CMAKE_SOURCE_DIR})
