cmake_minimum_required(VERSION 3.22.1)

# C is not optional: android_native_app_glue is a C file, and a project that enables only CXX
# cannot even pick a linker language for it. That is what broke the v7 build:
#   "CMake Error: CMake can not determine linker language for target: native_app_glue"
project(villagame C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_STANDARD 11)

# The VPK loader and the shading/camera maths are shared with the villa viewer next door:
# one implementation, tested once, used by both apps.
set(VIEWER_CPP ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../viewer/app/src/main/cpp)
if(NOT EXISTS ${VIEWER_CPP}/vpk.cpp)
    message(FATAL_ERROR "vpk.cpp not found at ${VIEWER_CPP} - the villa viewer sources are "
                        "part of this repository and must be checked out alongside the game.")
endif()

set(APP_GLUE_DIR ${ANDROID_NDK}/sources/android/native_app_glue)
if(NOT EXISTS ${APP_GLUE_DIR}/android_native_app_glue.c)
    message(FATAL_ERROR "android_native_app_glue.c not found at ${APP_GLUE_DIR}")
endif()

# The glue is compiled straight into the .so instead of into its own static library. Built as
# a static library it needs -u ANativeActivity_onCreate to survive the link; compiled as an
# ordinary object of the shared library, ANativeActivity_onCreate is defined in the image and
# that flag, and the extra target, both go away.
add_library(villagame SHARED
        ${APP_GLUE_DIR}/android_native_app_glue.c
        main_android.cpp          # the whole Android front end: EGL, input, frame loop
        hud.cpp                   # the HUD, drawn in GL from a baked font atlas
        game.cpp                  # the renderer and the game entry points
        ${VIEWER_CPP}/vpk.cpp)

target_include_directories(villagame PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${APP_GLUE_DIR}
        ${VIEWER_CPP})

target_compile_options(villagame PRIVATE -O3 -ffast-math -Wall)

target_link_libraries(villagame
        android
        log
        EGL
        GLESv2)
