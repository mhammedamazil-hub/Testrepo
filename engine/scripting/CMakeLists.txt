add_library(reality_scripting STATIC
    scripting.cpp
)

target_include_directories(reality_scripting PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_scripting PUBLIC reality_core)
target_include_directories(reality_scripting PUBLIC ${CMAKE_SOURCE_DIR})
