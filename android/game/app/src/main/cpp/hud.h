// =====================================================================================
//  hud.h - the HUD, drawn with GLES2 instead of Android's Canvas.
//
//  Replacing `HudView.java` costs one thing: text has to come from a texture. tools/hud_font.py
//  bakes a fixed-cell atlas of printable ASCII (white glyphs, alpha = coverage) so there are
//  no per-glyph metrics on this side - a glyph is `ascii - 32`, the cell is known, and the
//  fixed cell means even a proportional font lines up on a grid.
//
//  Everything here draws into a single dynamic vertex buffer and flushes once per kind of
//  state change, so a full HUD (panel, five text runs, crosshair, chevron, stick) is about a
//  dozen draw calls at 1080p - nothing next to 88 model draws.
//
//  Coordinates are *pixels, y down* (screen space), which is what the touch code speaks. The
//  vertex shader does the flip, so nothing above this layer has to think about it.
// =====================================================================================
#pragma once

#include <string>

struct AAssetManager;

// Creates the HUD program and loads the font atlas. Call it after the EGL context exists;
// `mgr` is the APK's asset manager (android_native_app_glue gives you one).
bool hud_init(AAssetManager* mgr);

// Called once per frame before anything is drawn; `w`/`h` are the surface size in pixels.
void hud_begin(int w, int h);
// Uploads whatever is queued, restores GL state and leaves the HUD on screen.
void hud_end();
// Called when the EGL context is destroyed: all GL objects must be recreated on return.
void hud_on_gl_lost();
void hud_shutdown();

// ---- primitives, all in pixels with y pointing down
void hud_rect(float x, float y, float w, float h, float r, float g, float b, float a);
void hud_panel(float x, float y, float w, float h);          // translucent dark rounded box
void hud_disc(float cx, float cy, float radius, float r, float g, float b, float a);
void hud_ring(float cx, float cy, float radius, float thickness, float r, float g, float b,
              float a);
void hud_dim(float alpha);                                    // full-screen scrim

// ---- text. `size` is the pixel height of a capital, so 16 is a normal HUD line at 800 px tall
void hud_text(const char* text, float x, float y, float size, float r, float g, float b, float a);
void hud_text_right(const char* text, float right_x, float y, float size, float r, float g,
                    float b, float a);
void hud_text_centered(const char* text, float cx, float y, float size, float r, float g,
                       float b, float a);
// Width of a run of text in pixels, for laying out a box behind it.
float hud_text_width(const char* text, float size);

// ---- game furniture
void hud_crosshair(float cx, float cy, float radius, float dp);
// `bearing` is radians, 0 = straight ahead, positive = to the right (game_core convention).
void hud_chevron(float cx, float cy, float size, float bearing, float dp);
// The renderer's self-diagnosis (gpu, precision, program links, probes), bottom-left.
void hud_diag(const char* text);
