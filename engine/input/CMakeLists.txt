add_library(reality_input STATIC
    input.cpp
)

target_include_directories(reality_input PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_input PUBLIC reality_core reality_platform)
target_include_directories(reality_input PUBLIC ${CMAKE_SOURCE_DIR})
