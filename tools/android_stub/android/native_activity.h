// Host stub for android/native_activity.h (only what the game touches).
#pragma once
#include <cstdint>
struct AAssetManager;
struct ANativeWindow;
struct ANativeActivity {
    AAssetManager* assetManager;
    ANativeWindow* window;
};
int32_t ANativeActivity_setWindowFlags(ANativeActivity*, uint32_t, uint32_t);
void ANativeActivity_finish(ANativeActivity*);
