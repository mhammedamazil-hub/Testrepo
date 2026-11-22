add_library(reality_platform STATIC
    platform.cpp
)

target_include_directories(reality_platform PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_platform PUBLIC reality_core)
target_include_directories(reality_platform PUBLIC ${CMAKE_SOURCE_DIR})
