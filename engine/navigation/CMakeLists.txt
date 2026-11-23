add_library(reality_navigation STATIC
    navigation.cpp
)

target_include_directories(reality_navigation PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_navigation PUBLIC reality_core)
target_include_directories(reality_navigation PUBLIC ${CMAKE_SOURCE_DIR})
