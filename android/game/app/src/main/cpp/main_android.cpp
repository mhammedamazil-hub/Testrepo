// =====================================================================================
//  main_android.cpp - the whole Android front end, in C++.
//
//  v1..v6 used a Java Activity + GLSurfaceView + Canvas HUD. Nothing about that was needed:
//  Android ships `android_native_app_glue`, which hands you a window, an input queue and an
//  asset manager from a plain C `android_main()`. This file replaces all ~600 lines of Java:
//
//      Java (before)                     C++ (now)
//      MainActivity          ->  android_main() + lifecycle events
//      GameSurface / EGL     ->  egl_init() and the frame loop
//      MotionEvent stick/look ->  handle_input()
//      HudView (Canvas)      ->  hud.cpp, drawn with GL
//      Audio (AudioTrack)    ->  dropped, see README "honest limits"
//
//  The renderer is untouched: game_native.h is the old JNI entry points, moved out of
//  `extern "C"` so this file can call them directly. Same shaders, same post chain, same
//  self-diagnosis - which now also prints on screen when EGL or the window fails, because
//  there is no Java layer left to hide it.
// =====================================================================================

#include <android/log.h>
#include <android/native_activity.h>
#include <android/native_window.h>
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <android_native_app_glue.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#include "game_native.h"
#include "hud.h"

// radians of yaw per pixel of drag: a full sweep of a 1080 px-wide thumb is about 4 rad
static const float kLookSensitivity = 0.0042f;

#define LOG_TAG "VillaGame"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace {

struct FrameTime {
    double last = 0.0;
    double fps_acc = 0.0;
    int fps_frames = 0;
    float fps = 0.0f;

    static double now() {
        timespec ts{};
        clock_gettime(CLOCK_MONOTONIC, &ts);
        return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
    }

    float tick() {
        const double t = now();
        if (last <= 0.0) last = t;
        float dt = (float)(t - last);
        last = t;
        if (dt > 0.25f) dt = 0.25f;          // a stalled frame must not teleport anything
        fps_acc += dt;
        ++fps_frames;
        if (fps_acc >= 0.5) {
            fps = (float)(fps_frames / fps_acc);
            fps_acc = 0.0;
            fps_frames = 0;
        }
        return dt;
    }
};

// The thumb stick, floating under the first finger that lands on the left 45 % of the screen.
struct Stick {
    bool active = false;
    int id = -1;
    float base_x = 0, base_y = 0, knob_x = 0, knob_y = 0, radius = 1;
    float x = 0, y = 0;                      // -1..1, y up
};

struct AppState {
    android_app* app = nullptr;
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    int width = 1, height = 1;
    bool gl_ready = false;
    bool engine_ready = false;
    bool engine_tried = false;
    std::string boot_error;
    float boot_anim = 0.0f;

    FrameTime clock;
    Stick stick;
    int look_id = -1;
    float look_x = 0, look_y = 0;
    float pending_yaw = 0, pending_pitch = 0;

    float step_timer = 0.0f;
    int last_orbs = 0;

    double anim_start = 0.0;                 // drives the boot progress bar
};

AppState g;

// ------------------------------------------------------------------ GLES2 context
bool egl_init() {
    g.display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (g.display == EGL_NO_DISPLAY) {
        g.boot_error = "eglGetDisplay failed";
        return false;
    }
    EGLint major = 0, minor = 0;
    if (!eglInitialize(g.display, &major, &minor)) {
        g.boot_error = "eglInitialize failed";
        return false;
    }
    // GLES2, 16-bit depth: the floor the renderer is written against, and enough bandwidth
    // for old tablets. No depth requirement on the config beyond 16.
    const EGLint cfg_attribs[] = {EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
                                  EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
                                  EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
                                  EGL_ALPHA_SIZE, 0, EGL_DEPTH_SIZE, 16,
                                  EGL_NONE};
    EGLConfig config = nullptr;
    EGLint n = 0;
    if (!eglChooseConfig(g.display, cfg_attribs, &config, 1, &n) || n < 1) {
        g.boot_error = "no EGL config for GLES2";
        return false;
    }
    const EGLint ctx_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    g.context = eglCreateContext(g.display, config, EGL_NO_CONTEXT, ctx_attribs);
    if (g.context == EGL_NO_CONTEXT) {
        g.boot_error = "eglCreateContext failed";
        return false;
    }
    ANativeWindow* win = g.app->window;
    if (!win) {
        g.boot_error = "no native window";
        return false;
    }
    g.surface = eglCreateWindowSurface(g.display, config, win, nullptr);
    if (g.surface == EGL_NO_SURFACE) {
        g.boot_error = "eglCreateWindowSurface failed";
        return false;
    }
    if (!eglMakeCurrent(g.display, g.surface, g.surface, g.context)) {
        g.boot_error = "eglMakeCurrent failed";
        return false;
    }
    EGLint w = 0, h = 0;
    eglQuerySurface(g.display, g.surface, EGL_WIDTH, &w);
    eglQuerySurface(g.display, g.surface, EGL_HEIGHT, &h);
    g.width = w > 0 ? w : 1;
    g.height = h > 0 ? h : 1;
    LOGI("EGL %d.%d, surface %dx%d", major, minor, g.width, g.height);
    return true;
}

void egl_shutdown() {
    if (g.display != EGL_NO_DISPLAY) {
        eglMakeCurrent(g.display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
        if (g.surface != EGL_NO_SURFACE) eglDestroySurface(g.display, g.surface);
        if (g.context != EGL_NO_CONTEXT) eglDestroyContext(g.display, g.context);
        eglTerminate(g.display);
    }
    g.display = EGL_NO_DISPLAY;
    g.surface = EGL_NO_SURFACE;
    g.context = EGL_NO_CONTEXT;
    g.gl_ready = false;
}

// ------------------------------------------------------------------ input
void stick_release() {
    g.stick.active = false;
    g.stick.id = -1;
    g.stick.x = 0;
    g.stick.y = 0;
}

void handle_input() {
    android_input_buffer* buf = android_app_swap_input_buffers(g.app);
    if (!buf) return;
    for (uint64_t i = 0; i < buf->motionEventsCount; ++i) {
        const AInputEvent* e = buf->motionEvents[i];
        const int32_t action = AMotionEvent_getAction(e) & AMOTION_EVENT_ACTION_MASK;
        switch (action) {
            case AMOTION_EVENT_ACTION_DOWN:
            case AMOTION_EVENT_ACTION_POINTER_DOWN: {
                const int idx = (AMotionEvent_getAction(e) & AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >>
                                AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT;
                const int id = AMotionEvent_getPointerId(e, (size_t)idx);
                const float x = AMotionEvent_getX(e, (size_t)idx);
                const float y = AMotionEvent_getY(e, (size_t)idx);
                if (x < (float)g.width * 0.45f && !g.stick.active) {
                    g.stick.id = id;
                    g.stick.active = true;
                    g.stick.base_x = x;
                    g.stick.base_y = y;
                    g.stick.knob_x = x;
                    g.stick.knob_y = y;
                    g.stick.radius = (float)(g.width < g.height ? g.width : g.height) * 0.13f;
                    if (g.stick.radius < 60.0f) g.stick.radius = 60.0f;
                } else {
                    g.look_id = id;
                    g.look_x = x;
                    g.look_y = y;
                }
                // tapping the win screen starts a new run
                if (game_state() == 1) game_reset();
                break;
            }
            case AMOTION_EVENT_ACTION_MOVE: {
                const size_t count = AMotionEvent_getPointerCount(e);
                for (size_t i2 = 0; i2 < count; ++i2) {
                    const int id = AMotionEvent_getPointerId(e, i2);
                    const float x = AMotionEvent_getX(e, i2);
                    const float y = AMotionEvent_getY(e, i2);
                    if (id == g.stick.id) {
                        float dx = x - g.stick.base_x;
                        float dy = y - g.stick.base_y;
                        const float r = g.stick.radius;
                        float len = sqrtf(dx * dx + dy * dy);
                        if (len > r) {                  // let the base follow a long drag
                            g.stick.base_x += dx * (1.0f - r / len);
                            g.stick.base_y += dy * (1.0f - r / len);
                            dx = x - g.stick.base_x;
                            dy = y - g.stick.base_y;
                        }
                        g.stick.knob_x = g.stick.base_x + dx;
                        g.stick.knob_y = g.stick.base_y + dy;
                        g.stick.x = dx / r;
                        g.stick.y = -dy / r;            // screen y is down, forward is up
                    } else if (id == g.look_id) {
                        const float dx = x - g.look_x;
                        const float dy = y - g.look_y;
                        g.look_x = x;
                        g.look_y = y;
                        g.pending_yaw += dx * kLookSensitivity;    // drag right, turn right
                        g.pending_pitch -= dy * kLookSensitivity;  // drag up, look up
                    }
                }
                break;
            }
            case AMOTION_EVENT_ACTION_UP:
            case AMOTION_EVENT_ACTION_POINTER_UP:
            case AMOTION_EVENT_ACTION_CANCEL: {
                const int idx = (AMotionEvent_getAction(e) & AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >>
                                AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT;
                const int id = AMotionEvent_getPointerId(e, (size_t)idx);
                if (id == g.stick.id) stick_release();
                else if (id == g.look_id) g.look_id = -1;
                break;
            }
            default:
                break;
        }
    }
    android_app_clear_motion_events(buf);

    for (uint64_t i = 0; i < buf->keyEventsCount; ++i) {
        const AInputEvent* e = buf->keyEvents[i];
        const int32_t action = AKeyEvent_getAction(e);
        const int32_t code = AKeyEvent_getKeyCode(e);
        if (action == AKEY_EVENT_ACTION_DOWN && code == AKEYCODE_BACK) {
            ANativeActivity_finish(g.app->activity);
        }
    }
    android_app_clear_key_events(buf);
}

// ------------------------------------------------------------------ boot screen
// Frame 1 happens before the model is parsed, so there has to be something to look at while
// the 30 MB pack and the 117 kB level are read. Half a second of "VILLA GARDEN / loading..."
// beats a black rectangle - and, if EGL never comes up, this is what carries the error.
void draw_boot_screen() {
    hud_begin(g.width, g.height);
    const float cx = (float)g.width * 0.5f;
    hud_text_centered("VILLA GARDEN", cx, (float)g.height * 0.42f, 3.0f, 1.0f, 0.84f, 0.36f, 1.0f);
    if (!g.boot_error.empty()) {
        hud_text_centered(g.boot_error.c_str(), cx, (float)g.height * 0.52f, 1.6f,
                          1.0f, 0.45f, 0.42f, 1.0f);
        hud_text_centered("this build is native-only; see android/game/README.md", cx,
                          (float)g.height * 0.60f, 1.3f, 0.85f, 0.88f, 0.92f, 1.0f);
    } else {
        // a thin progress bar that fills over the first second of loading
        const double t = FrameTime::now() - g.anim_start;
        float p = (float)t / 0.9f;
        if (p > 1.0f) p = 1.0f;
        if (p < 0.0f) p = 0.0f;
        const float w = (float)g.width * 0.30f * p;
        hud_rect(cx - (float)g.width * 0.15f, (float)g.height * 0.52f, w, 3.0f, 1.0f, 0.84f,
                 0.36f, 0.9f);
    }
    hud_end();
}

// ------------------------------------------------------------------ frame
void draw_frame() {
    const float dt = g.clock.tick();

    if (!g.engine_ready) {
        if (!g.engine_tried) {
            g.engine_tried = true;
            std::string err;
            if (!game_init(g.app->activity->assetManager, &err)) {
                g.boot_error = err.empty() ? "engine init failed" : err;
                LOGE("engine init: %s", g.boot_error.c_str());
            } else {
                g.engine_ready = true;
                game_resize(g.width, g.height);
            }
            hud_init(g.app->activity->assetManager);
        }
        draw_boot_screen();
        eglSwapBuffers(g.display, g.surface);
        return;
    }

    // one footstep per ~0.55 s while the stick is pushed
    const float mag = sqrtf(g.stick.x * g.stick.x + g.stick.y * g.stick.y);
    if (mag > 0.35f && game_state() == 0) {
        g.step_timer -= dt * (0.6f + 0.7f * mag);
        if (g.step_timer <= 0.0f) g.step_timer = 0.55f;
    } else {
        g.step_timer = 0.0f;
    }

    const float yaw_delta = g.pending_yaw;
    const float pitch_delta = g.pending_pitch;
    g.pending_yaw = 0.0f;
    g.pending_pitch = 0.0f;

    game_frame(dt, g.stick.active ? g.stick.x : 0.0f, g.stick.active ? g.stick.y : 0.0f,
               yaw_delta, pitch_delta);

    // ---- HUD, drawn into the same framebuffer, over the finished frame
    hud_begin(g.width, g.height);
    const float dp = (float)g.height / 800.0f;          // 1 dp at 800 px tall
    const float pad = 18.0f * dp;
    hud_panel(pad * 0.5f, pad * 0.5f, 168.0f * dp, 66.0f * dp);
    char buf[96];
    std::snprintf(buf, sizeof buf, "VILLA GARDEN");
    hud_text(buf, pad, pad + 14.0f * dp, 1.6f * dp, 0.93f, 0.95f, 0.97f, 1.0f);
    std::snprintf(buf, sizeof buf, "%d / %d", game_orbs(), game_total());
    hud_text(buf, pad, pad + 44.0f * dp, 2.4f * dp, 1.0f, 1.0f, 1.0f, 1.0f);

    const int secs = (int)game_time();
    std::snprintf(buf, sizeof buf, "%d:%02d", secs / 60, secs % 60);
    hud_text_right(buf, (float)g.width - pad, pad + 34.0f * dp, 2.2f * dp, 0.96f, 0.97f, 0.98f, 1.0f);

    std::snprintf(buf, sizeof buf, "%d fps", (int)(g.clock.fps + 0.5f));
    hud_text_right(buf, (float)g.width - pad, (float)g.height - pad * 0.6f, 1.3f * dp, 0.55f,
                   0.58f, 0.62f, 1.0f);

    hud_crosshair((float)g.width * 0.5f, (float)g.height * 0.5f, 2.0f, dp);

    // compass chevron: rotates to point at the nearest orb
    const float bearing = game_bearing();
    hud_chevron((float)g.width * 0.5f, pad + 40.0f * dp, 22.0f * dp, bearing, dp);

    // thumb stick, when a finger is down
    if (g.stick.active) {
        hud_ring(g.stick.base_x, g.stick.base_y, g.stick.radius, 2.0f * dp, 1.0f, 1.0f, 1.0f,
                 0.28f);
        hud_disc(g.stick.knob_x, g.stick.knob_y, g.stick.radius * 0.34f, 1.0f, 1.0f, 1.0f, 0.55f);
    }

    if (game_state() == 1) {
        hud_dim(0.55f);
        hud_text_centered("GARDEN WALKED", (float)g.width * 0.5f, (float)g.height * 0.42f,
                          3.2f * dp, 1.0f, 0.85f, 0.38f, 1.0f);
        std::snprintf(buf, sizeof buf, "all %d collected in %d:%02d", game_total(), secs / 60,
                      secs % 60);
        hud_text_centered(buf, (float)g.width * 0.5f, (float)g.height * 0.50f, 1.8f * dp, 1.0f,
                          1.0f, 1.0f, 1.0f);
        hud_text_centered("tap anywhere to walk it again", (float)g.width * 0.5f,
                          (float)g.height * 0.56f, 1.5f * dp, 0.72f, 0.75f, 0.78f, 1.0f);
    }

    // the renderer's self-diagnosis, always on screen (see game.cpp)
    hud_diag(game_status());
    hud_end();

    if (!eglSwapBuffers(g.display, g.surface)) {
        LOGE("eglSwapBuffers failed: 0x%04x", eglGetError());
    }
}

// ------------------------------------------------------------------ glue callbacks
void on_app_cmd(android_app* app, int32_t cmd) {
    switch (cmd) {
        case APP_CMD_INIT_WINDOW:
            if (app->window && !g.gl_ready) {
                if (egl_init()) {
                    g.gl_ready = true;
                    hud_init(g.app->activity->assetManager);
                    if (g.engine_ready) game_resize(g.width, g.height);
                } else {
                    LOGE("EGL init: %s", g.boot_error.c_str());
                }
            }
            break;
        case APP_CMD_TERM_WINDOW:
            // Losing the window destroys the EGL context, and with it every texture, buffer,
            // framebuffer and program the renderer owns. The engine has to be told, or its
            // "ready" flag would have it drawing with dead GL names on the next window - a
            // black screen after switching apps. Re-initialising re-reads the assets, which
            // costs a fraction of a second and is the only correct thing to do while the
            // loader still mixes CPU and GPU state.
            game_shutdown();
            hud_on_gl_lost();
            g.engine_ready = false;
            g.engine_tried = false;
            g.stick.active = false;
            g.stick.id = -1;
            g.look_id = -1;
            break;
        case APP_CMD_WINDOW_RESIZED:
        case APP_CMD_CONFIG_CHANGED: {
            if (g.gl_ready && g.surface != EGL_NO_SURFACE) {
                EGLint w = 0, h = 0;
                eglQuerySurface(g.display, g.surface, EGL_WIDTH, &w);
                eglQuerySurface(g.display, g.surface, EGL_HEIGHT, &h);
                if (w > 0 && h > 0 && (w != g.width || h != g.height)) {
                    g.width = w;
                    g.height = h;
                    if (g.engine_ready) game_resize(g.width, g.height);
                }
            }
            break;
        }
        case APP_CMD_GAINED_FOCUS:
            g.clock.last = 0.0;      // do not integrate the pause as one giant frame
            break;
        case APP_CMD_LOST_FOCUS:
            stick_release();
            g.look_id = -1;
            break;
        case APP_CMD_DESTROY:
            game_shutdown();
            hud_shutdown();
            egl_shutdown();
            break;
        default:
            break;
    }
}

}  // namespace

void android_main(android_app* app) {
    app->onAppCmd = on_app_cmd;
    app->userData = &g;
    g.app = app;
    g.anim_start = FrameTime::now();

    // keep the screen on and hide the status bar, without Java
    ANativeActivity_setWindowFlags(app->activity,
                                   AWINDOW_FLAG_KEEP_SCREEN_ON | AWINDOW_FLAG_FULLSCREEN, 0);

    for (;;) {
        int events = 0;
        android_poll_source* source = nullptr;
        // block only when there is nothing to draw: once GL is up this is a render loop
        const int timeout = (g.gl_ready && g.engine_ready) ? 0 : -1;
        while (ALooper_pollOnce(timeout, nullptr, &events, (void**)&source) >= 0) {
            if (source) source->process(app, source);
            if (app->destroyRequested != 0) {
                game_shutdown();
                hud_shutdown();
                egl_shutdown();
                return;
            }
            if (g.gl_ready) break;      // events handled; go draw
        }
        if (app->destroyRequested != 0) {
            game_shutdown();
            hud_shutdown();
            egl_shutdown();
            return;
        }
        if (g.gl_ready) {
            handle_input();
            draw_frame();
        }
    }
}
