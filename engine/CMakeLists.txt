cmake_minimum_required(VERSION 3.16)
project(RealityEngine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

if(NOT CMAKE_INSTALL_PREFIX)
    set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/install)
endif()

set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -O2 -DNDEBUG")
set(CMAKE_EXE_LINKER_FLAGS_RELEASE "${CMAKE_EXE_LINKER_FLAGS_RELEASE} -s")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -lstdc++fs")

set(JOLT_PHYSICS_SOURCE_DIR "${CMAKE_SOURCE_DIR}/../jolt-physics" CACHE PATH "Path to Jolt Physics source directory")
set(JOLT_PHYSICS_BUILD_DIR "${CMAKE_SOURCE_DIR}/../jolt-physics/Build" CACHE PATH "Path to Jolt Physics build directory")
if(EXISTS "${JOLT_PHYSICS_BUILD_DIR}/CMakeLists.txt")
    add_subdirectory(${JOLT_PHYSICS_BUILD_DIR} JoltPhysics)
else()
    message(WARNING "Jolt Physics CMake not found at ${JOLT_PHYSICS_BUILD_DIR}. Physics module will be stubbed.")
endif()

add_subdirectory(core)
add_subdirectory(ecs)
add_subdirectory(world)
add_subdirectory(scene)
add_subdirectory(assets)
add_subdirectory(physics)
add_subdirectory(rendering)
add_subdirectory(platform)
add_subdirectory(input)
add_subdirectory(animation)
add_subdirectory(audio)
add_subdirectory(navigation)
add_subdirectory(scripting)
add_subdirectory(gameplay)
add_subdirectory(diagnostics)

add_executable(reality_runtime
    ../runtime/main.cpp
)

target_link_libraries(reality_runtime PRIVATE
    reality_core
    reality_ecs
    reality_world
    reality_scene
    reality_assets
    reality_physics
    reality_rendering
    reality_platform
    reality_input
    reality_animation
    reality_audio
    reality_navigation
    reality_scripting
    reality_gameplay
    reality_diagnostics
)

if(TARGET Jolt)
    target_link_libraries(reality_runtime PRIVATE Jolt)
endif()

target_include_directories(reality_runtime PRIVATE
    ${JOLT_PHYSICS_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}
    ${CMAKE_SOURCE_DIR}/core
    ${CMAKE_SOURCE_DIR}/ecs
    ${CMAKE_SOURCE_DIR}/world
    ${CMAKE_SOURCE_DIR}/scene
    ${CMAKE_SOURCE_DIR}/assets
    ${CMAKE_SOURCE_DIR}/physics
    ${CMAKE_SOURCE_DIR}/rendering
    ${CMAKE_SOURCE_DIR}/platform
    ${CMAKE_SOURCE_DIR}/input
    ${CMAKE_SOURCE_DIR}/animation
    ${CMAKE_SOURCE_DIR}/audio
    ${CMAKE_SOURCE_DIR}/navigation
    ${CMAKE_SOURCE_DIR}/scripting
    ${CMAKE_SOURCE_DIR}/gameplay
    ${CMAKE_SOURCE_DIR}/diagnostics
)

enable_testing()
add_subdirectory(${CMAKE_SOURCE_DIR}/../tests/reality tests)
