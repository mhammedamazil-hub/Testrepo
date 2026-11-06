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

# android_native_app_glue ships with the NDK as source, not as a library.
add_library(native_app_glue STATIC
        ${ANDROID_NDK}/sources/android/native_app_glue/android_native_app_glue.c)
target_include_directories(native_app_glue PUBLIC
        ${ANDROID_NDK}/sources/android/native_app_glue)

add_library(villagame SHARED
        main_android.cpp          # the whole Android front end: EGL, input, frame loop
        hud.cpp                   # the HUD, drawn in GL from a baked font atlas
        game.cpp                  # the renderer and the game entry points
        ${VIEWER_CPP}/vpk.cpp)

target_include_directories(villagame PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${VIEWER_CPP})

target_compile_options(villagame PRIVATE -O3 -ffast-math -Wall)

target_link_libraries(villagame
        native_app_glue
        android
        log
        EGL
        GLESv2)
