// The look of the game, in one place.
//
// `shade.h` holds the *viewer's* lighting (a bright, flat, "product shot" curve). The game
// needs the opposite: the reference renders in `villa_v2/hero/` are Cycles frames through an
// AgX-like curve, so here the sun is stronger, the ambient is lower and the tone map is an
// ACES fit. Every constant below appears verbatim in the GLSL in game.cpp, so the desktop
// harness (tools/game_sim.cpp) predicts the tablet instead of merely flattering it.
#pragma once
#include <cmath>

struct GameSun {
    float dir[3];        // towards the sun, normalised
    float sun_col[3];    // sun colour * strength
    float sky_col[3];    // zenith ambient
    float ground_col[3]; // bounce from the paving and lawn
    float fog_col[3];
    float exposure;
    float fog_start;     // metres
    float fog_density;
};

// Late afternoon, 22 degrees up, raking from the west-south-west: the same rig the hero
// stills were lit with (sun azimuth 205 deg in Blender terms).
static inline GameSun game_sun() {
    GameSun s{};
    const float el = 30.0f * 3.14159265f / 180.0f;   // mid-afternoon: a garden you can walk in, not a dusk photo
    const float az = 236.0f * 3.14159265f / 180.0f;
    s.dir[0] = sinf(az) * cosf(el);
    s.dir[1] = sinf(el);
    s.dir[2] = -cosf(az) * cosf(el);
    s.sun_col[0] = 3.00f;  s.sun_col[1] = 2.55f;  s.sun_col[2] = 1.88f;
    s.sky_col[0] = 0.50f;  s.sky_col[1] = 0.62f;  s.sky_col[2] = 0.80f;
    s.ground_col[0] = 0.24f; s.ground_col[1] = 0.22f; s.ground_col[2] = 0.18f;
    s.fog_col[0] = 0.115f; s.fog_col[1] = 0.128f; s.fog_col[2] = 0.145f;  // == the sky horizon, so distance melts into sky
    s.exposure = 2.30f;
    s.fog_start = 20.0f;
    s.fog_density = 0.011f;
    return s;
}

// ACES-ish filmic curve (Narkowicz fit). Keeps highlights from clipping to white, which is
// what made the first version of this shot look like pale grey cardboard.
static inline float game_tonemap(float x) {
    const float a = 2.51f, b = 0.03f, c = 2.43f, d = 0.59f, e = 0.14f;
    float t = (x * (a * x + b)) / (x * (c * x + d) + e);
    if (t < 0.0f) t = 0.0f;
    if (t > 1.0f) t = 1.0f;
    return powf(t, 1.0f / 2.2f);
}

/// `albedo` is the sampled texture (sRGB), `base` the material factor, `n` the interpolated
/// world normal, `ao` a 0..1 ambient occlusion term (1 = fully open sky).
/// `fres` is the grazing-angle weight (0 = face on, 1 = edge on): a lawn seen at 80 degrees
/// picks up a lot of sky, and without it every distant surface goes flat and muddy.
static inline void game_shade(const float albedo[3], const float base[3], const float n[3],
                             const GameSun& s, float ao, float out[3], float fres = 0.0f) {
    float nl = n[0] * n[0] + n[1] * n[1] + n[2] * n[2];
    float inv = nl > 1e-8f ? 1.0f / sqrtf(nl) : 0.0f;
    const float nx = n[0] * inv, ny = n[1] * inv, nz = n[2] * inv;
    float d = nx * s.dir[0] + ny * s.dir[1] + nz * s.dir[2];
    // a soft terminator, because a hard N.L edge looks like a 1996 renderer indoors
    d = d > 0.0f ? d : 0.0f;
    d = d * d * (3.0f - 2.0f * d) * 0.35f + d * 0.65f;
    const float hemi = 0.5f + 0.5f * ny;
    for (int i = 0; i < 3; ++i) {
        // sRGB -> linear, cheaply (albedo squared), then light, then back out through gamma
        float alb = albedo[i] * base[i];
        float lin = alb * alb;
        float amb = (s.ground_col[i] + (s.sky_col[i] - s.ground_col[i]) * hemi) * ao;
        float c = lin * (amb + s.sun_col[i] * d * (0.35f + 0.65f * ao));
        // sky sheen at grazing angles
        c += s.sky_col[i] * fres * 0.055f;
        out[i] = game_tonemap(c * s.exposure);
    }
}

/// HDR variant: same maths, but stops before the tone curve so the post pass can bloom the
/// scene in linear light. `sun_vis` is the baked sun visibility and `ao` the baked ambient
/// visibility, both 0..1 from tools/villa_pack.py. Without them GLES2 has no shadows at all,
/// which is why v1 looked flat: the trees cast nothing and every wall was lit the same.
static inline void game_shade_hdr(const float albedo[3], const float base[3], const float n[3],
                                  const GameSun& s, float ao, float sun_vis, float out[3],
                                  float fres = 0.0f) {
    float nl = n[0] * n[0] + n[1] * n[1] + n[2] * n[2];
    float inv = nl > 1e-8f ? 1.0f / sqrtf(nl) : 0.0f;
    const float nx = n[0] * inv, ny = n[1] * inv, nz = n[2] * inv;
    float d = nx * s.dir[0] + ny * s.dir[1] + nz * s.dir[2];
    d = d > 0.0f ? d : 0.0f;
    d = d * d * (3.0f - 2.0f * d) * 0.35f + d * 0.65f;
    const float hemi = 0.5f + 0.5f * ny;
    for (int i = 0; i < 3; ++i) {
        float alb = albedo[i] * base[i];
        float lin = alb * alb;
        float amb = (s.ground_col[i] + (s.sky_col[i] - s.ground_col[i]) * hemi) * ao;
        float c = lin * (amb + s.sun_col[i] * d * sun_vis);
        // the sheen is what a sky actually adds at grazing angles
        c += s.sky_col[i] * fres * 0.055f * ao;
        out[i] = c * s.exposure;
    }
}

/// Exposure + ACES + sRGB, the display end of the pipeline.
static inline float game_display(float x) { return game_tonemap(x); }

/// Distance haze, matched to fog_col/fog_start/fog_density.
static inline float game_fog(const GameSun& s, float dist) {
    float x = (dist - s.fog_start) * s.fog_density;
    if (x <= 0.0f) return 0.0f;
    return 1.0f - expf(-x);
}
