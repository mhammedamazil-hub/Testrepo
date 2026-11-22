add_library(reality_animation STATIC
    animation.cpp
)

target_include_directories(reality_animation PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_animation PUBLIC reality_ecs reality_core)
target_include_directories(reality_animation PUBLIC ${CMAKE_SOURCE_DIR})
