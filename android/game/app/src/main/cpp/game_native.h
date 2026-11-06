// The game engine's public surface, for the native app shell.
//
// These were JNI methods back when an `Activity` owned the window. The APK is native-only now
// (NativeActivity + android_native_app_glue), so the same functions are called directly from
// main_android.cpp. `game.cpp` implements them; nothing here touches Java.
#pragma once

#include <string>

struct AAssetManager;

// Reads model.vpk + level.bin from the assets, builds the level, compiles every program and
// runs the GL self-test. Must be called with a current EGL context.
bool game_init(AAssetManager* mgr, std::string* err);

// Surface size in pixels. Safe to call on every resize and rotation.
void game_resize(int w, int h);

// One frame. `jx`/`jy` are the thumb stick (-1..1, +y is forward), `dyaw`/`dpitch` the look
// delta accumulated since the last call, in radians.
void game_frame(float dt, float jx, float jy, float dyaw, float dpitch);

// Reads for the HUD.
int game_orbs();
int game_total();
float game_time();
int game_state();          // 0 = playing, 1 = won
float game_bearing();      // radians to the nearest orb, 0 = ahead
void game_reset();

// Human-readable state: the renderer's self-diagnosis when it has one, otherwise the status.
const char* game_status();

// The EGL context is going away (or the app is): drop every GL object reference.
void game_shutdown();
