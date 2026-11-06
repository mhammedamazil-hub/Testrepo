// Host stub for android_native_app_glue, enough to type-check main_android.cpp.
#pragma once
#include <android/asset_manager.h>
#include <android/input.h>
#include <android/looper.h>

struct ANativeActivity;
struct ANativeWindow;

struct android_app {
    void* userData;
    ANativeActivity* activity;
    ANativeWindow* window;
    void (*onAppCmd)(android_app*, int32_t);
    int32_t (*onInputEvent)(android_app*, AInputEvent*);
    int destroyRequested;
};

enum {
    APP_CMD_INIT_WINDOW = 10,
    APP_CMD_TERM_WINDOW = 11,
    APP_CMD_WINDOW_RESIZED = 12,
    APP_CMD_CONFIG_CHANGED = 13,
    APP_CMD_GAINED_FOCUS = 14,
    APP_CMD_LOST_FOCUS = 15,
    APP_CMD_DESTROY = 16,
};
void android_main(android_app* app);
