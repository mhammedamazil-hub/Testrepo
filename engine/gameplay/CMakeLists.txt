add_library(reality_gameplay STATIC
    gameplay.cpp
)

target_include_directories(reality_gameplay PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_gameplay PUBLIC reality_ecs reality_core reality_physics)
target_include_directories(reality_gameplay PUBLIC ${CMAKE_SOURCE_DIR})
