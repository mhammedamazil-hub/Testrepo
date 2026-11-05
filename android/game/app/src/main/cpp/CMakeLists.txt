cmake_minimum_required(VERSION 3.22.1)
project(villagame CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# The VPK loader and the shading/camera maths are shared with the villa viewer next door:
# one implementation, tested once, used by both apps.
set(VIEWER_CPP ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../viewer/app/src/main/cpp)
if(NOT EXISTS ${VIEWER_CPP}/vpk.cpp)
    message(FATAL_ERROR "vpk.cpp not found at ${VIEWER_CPP} - the villa viewer sources are "
                        "part of this repository and must be checked out alongside the game.")
endif()

add_library(villagame SHARED
        game.cpp
        ${VIEWER_CPP}/vpk.cpp)

target_include_directories(villagame PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${VIEWER_CPP})

target_compile_options(villagame PRIVATE -O3 -ffast-math -Wall)

find_library(GLES_LIB GLESv2)
find_library(LOG_LIB log)
find_library(ANDROID_LIB android)
target_link_libraries(villagame ${GLES_LIB} ${LOG_LIB} ${ANDROID_LIB})
