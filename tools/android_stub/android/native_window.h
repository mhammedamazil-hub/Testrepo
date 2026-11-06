#pragma once
#include <cstdint>
struct AAssetManager;
struct ANativeActivity { AAssetManager* assetManager; };
struct ANativeWindow;
struct ANativeActivity;
enum { AWINDOW_FLAG_KEEP_SCREEN_ON = 0x00000080, AWINDOW_FLAG_FULLSCREEN = 0x00000400 };
int32_t ANativeActivity_setWindowFlags(ANativeActivity*, uint32_t, uint32_t);
void ANativeActivity_finish(ANativeActivity*);
