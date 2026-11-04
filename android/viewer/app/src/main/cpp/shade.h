// Shading constants and camera maths shared by the Android GLES2 renderer and the desktop
// software-rasteriser test tool. Keeping ONE definition of the look means the desktop test
// actually predicts what the tablet will show.
#pragma once
#include <cmath>
#include <cstring>

#include "vpk.h"

struct Vsun {
    float dir[3];    // towards the sun (normalised)
    float colour[3]; // sun tint * intensity
    float amb_sky[3];
    float amb_ground[3];
};

// Late-afternoon raking sun + sky/ground bounce, matched to the Blender lighting rig.
static inline Vsun vpk_default_sun() {
    Vsun s{};
    const float el = 20.0f * 3.14159265f / 180.0f;
    const float az = 232.0f * 3.14159265f / 180.0f;
    s.dir[0] = sinf(az) * cosf(el);
    s.dir[1] = sinf(el);
    s.dir[2] = -cosf(az) * cosf(el);
    s.colour[0] = 1.00f; s.colour[1] = 0.88f; s.colour[2] = 0.72f;
    s.amb_sky[0] = 0.42f; s.amb_sky[1] = 0.50f; s.amb_sky[2] = 0.62f;
    s.amb_ground[0] = 0.24f; s.amb_ground[1] = 0.21f; s.amb_ground[2] = 0.16f;
    return s;
}

// ---- shading (exactly the maths in the fragment shader)
static inline void vpk_shade(const float albedo[3], const float base[3], const float n[3],
                             const Vsun& s, float e_sun, float e_amb, float e_bounce,
                             float out[3]) {
    float alb[3];
    for (int i = 0; i < 3; ++i) alb[i] = albedo[i] * base[i];
    float nl = n[0] * n[0] + n[1] * n[1] + n[2] * n[2];
    float inv = nl > 1e-8f ? 1.0f / sqrtf(nl) : 0.0f;
    float nx = n[0] * inv, ny = n[1] * inv, nz = n[2] * inv;
    float d = nx * s.dir[0] + ny * s.dir[1] + nz * s.dir[2];
    if (d < 0.0f) d = 0.0f;
    float band = 0.5f + 0.5f * ny;
    for (int i = 0; i < 3; ++i) {
        float amb = s.amb_ground[i] + (s.amb_sky[i] - s.amb_ground[i]) * band;
        // albedo squared = cheap sRGB->linear, sqrt at the end puts it back
        float c = alb[i] * alb[i] * (amb * e_amb + s.colour[i] * d * e_sun);
        c += alb[i] * e_bounce * 0.10f;   // fake ground bounce on the shade side
        if (c < 0.0f) c = 0.0f;
        // tone map (Reinhard-ish, then the 2.2 gamma)
        float t = c / (c + 0.85f);
        out[i] = sqrtf(t * 1.30f);
        if (out[i] > 1.0f) out[i] = 1.0f;
    }
}

// ---- 4x4 column-major matrices, as GL wants them
struct Mat4 { float m[16]; };

static inline Mat4 mat4_mul(const Mat4& a, const Mat4& b) {
    Mat4 r{};
    for (int c = 0; c < 4; ++c)
        for (int rw = 0; rw < 4; ++rw) {
            float s = 0.0f;
            for (int k = 0; k < 4; ++k) s += a.m[k * 4 + rw] * b.m[c * 4 + k];
            r.m[c * 4 + rw] = s;
        }
    return r;
}

static inline Mat4 mat4_perspective(float fovy, float aspect, float zn, float zf) {
    Mat4 r{};
    float f = 1.0f / tanf(0.5f * fovy);
    r.m[0] = f / aspect;
    r.m[5] = f;
    r.m[10] = (zf + zn) / (zn - zf);
    r.m[11] = -1.0f;
    r.m[14] = (2.0f * zf * zn) / (zn - zf);
    return r;
}

static inline Mat4 mat4_lookat(const float eye[3], const float ctr[3], const float up[3]) {
    float f[3] = {ctr[0] - eye[0], ctr[1] - eye[1], ctr[2] - eye[2]};
    float fl = sqrtf(f[0] * f[0] + f[1] * f[1] + f[2] * f[2]);
    for (int i = 0; i < 3; ++i) f[i] /= fl;
    float s[3] = {f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2],
                  f[0] * up[1] - f[1] * up[0]};
    float sl = sqrtf(s[0] * s[0] + s[1] * s[1] + s[2] * s[2]);
    for (int i = 0; i < 3; ++i) s[i] /= sl;
    float u[3] = {s[1] * f[2] - s[2] * f[1], s[2] * f[0] - s[0] * f[2],
                  s[0] * f[1] - s[1] * f[0]};
    Mat4 r{};
    r.m[0] = s[0]; r.m[4] = s[1]; r.m[8] = s[2];
    r.m[1] = u[0]; r.m[5] = u[1]; r.m[9] = u[2];
    r.m[2] = -f[0]; r.m[6] = -f[1]; r.m[10] = -f[2];
    r.m[12] = -(s[0] * eye[0] + s[1] * eye[1] + s[2] * eye[2]);
    r.m[13] = -(u[0] * eye[0] + u[1] * eye[1] + u[2] * eye[2]);
    r.m[14] = (f[0] * eye[0] + f[1] * eye[1] + f[2] * eye[2]);
    r.m[15] = 1.0f;
    return r;
}

// Orbit camera: yaw 0 looks from -Z towards +Z. Default is the "hero garden" angle.
struct OrbitCam {
    float target[3] = {0, 0, 0};
    float dist = 40.0f;
    float yaw = 2.60f;      // radians
    float pitch = 0.20f;    // radians above the horizon
    void eye(float out[3]) const {
        const float cp = cosf(pitch);
        out[0] = target[0] + dist * cp * sinf(yaw);
        out[1] = target[1] + dist * sinf(pitch);
        out[2] = target[2] + dist * cp * cosf(yaw);
    }
    void view_proj(float aspect, Mat4* out_vp) const {
        float e[3];
        eye(e);
        const float up[3] = {0.0f, 1.0f, 0.0f};
        Mat4 v = mat4_lookat(e, target, up);
        Mat4 p = mat4_perspective(38.0f * 3.14159265f / 180.0f, aspect, 0.4f, 1400.0f);
        *out_vp = mat4_mul(p, v);
    }
};
