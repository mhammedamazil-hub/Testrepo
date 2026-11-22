add_library(reality_ecs STATIC
    ecs.cpp
)

target_include_directories(reality_ecs PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_ecs PUBLIC reality_core)
target_include_directories(reality_ecs PUBLIC ${CMAKE_SOURCE_DIR})
