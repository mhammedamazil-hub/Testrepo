add_library(reality_rendering STATIC
    renderer.cpp
    headless_renderer.cpp
)

target_include_directories(reality_rendering PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_rendering PUBLIC reality_core)
target_include_directories(reality_rendering PUBLIC ${CMAKE_SOURCE_DIR})
