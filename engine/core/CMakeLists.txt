add_library(reality_core STATIC
    engine.cpp
    application.cpp
    game_loop.cpp
    logging.cpp
    config.cpp
    error.cpp
)

target_include_directories(reality_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_definitions(reality_core PUBLIC
    REALITY_CORE_EXPORT
)
target_include_directories(reality_core PUBLIC ${CMAKE_SOURCE_DIR})
