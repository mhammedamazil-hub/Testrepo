add_library(reality_audio STATIC
    audio.cpp
)

target_include_directories(reality_audio PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_audio PUBLIC reality_core)
target_include_directories(reality_audio PUBLIC ${CMAKE_SOURCE_DIR})
