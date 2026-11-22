add_library(reality_diagnostics STATIC
    diagnostics.cpp
)

target_include_directories(reality_diagnostics PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_diagnostics PUBLIC reality_core reality_ecs reality_physics)
target_include_directories(reality_diagnostics PUBLIC ${CMAKE_SOURCE_DIR})
