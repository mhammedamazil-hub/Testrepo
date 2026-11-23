add_library(reality_assets STATIC
    asset_manager.cpp
    gltf_loader.cpp
)

target_include_directories(reality_assets PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(reality_assets PUBLIC reality_core)
target_include_directories(reality_assets PUBLIC ${CMAKE_SOURCE_DIR})
