// Desktop verification harness for the game.
//
//   g++ -O2 -std=c++17 tools/game_sim.cpp \
//       android/viewer/app/src/main/cpp/vpk.cpp \
//       -Iandroid/viewer/app/src/main/cpp \
//       -Iandroid/game/app/src/main/cpp -o /tmp/gamesim
//
//   /tmp/gamesim play  android/game/app/src/main/assets  /tmp/shots 20
//   /tmp/gamesim shot  android/game/app/src/main/assets  /tmp/eye.ppm  [x z yaw_deg]
//
// `play` is the important one: it drives the *real* game_core.h movement code around the
// *real* level with a BFS autopilot, collects every objective, and writes eye-level frames
// with the *real* vpk.cpp loader and shading maths. If the walkthrough completes, the level
// is traversable and the renderer is showing the geometry the collision was baked from; if
// it stalls, the level has a gap too narrow for a 0.68 m body and this fails.
//
// It is a test tool, not the deliverable. It renders in software at 512x288.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <string>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#include "stb_image.h"

#include "game_core.h"
#include "game_shade.h"
#include "shade.h"
#include "vpk.h"

static const int W = 1920, H = 1080;   // the target: 1080p, like the phone
static const float kFovY = 62.0f * 3.14159265f / 180.0f;
static float g_time = 0.0f;            // drives wind, water and the orb pulse
static float g_wind = 1.0f;            // 0 = still air, 1 = a light garden breeze (m/s-ish)


// ---- surface detail -------------------------------------------------------------
// The 70 m lawn is one quad with a 256 px texture, so it renders as a flat green sheet.
// The device shader adds the same two-octave value noise to near-horizontal surfaces from
// world XZ; this is that function, and the GLSL in game.cpp is a line-for-line copy.
static inline float g_hash(float x, float y) {
    x = fmodf(x * 123.34f, 1.0f);
    y = fmodf(y * 456.21f, 1.0f);
    if (x < 0) x += 1.0f;
    if (y < 0) y += 1.0f;
    float d = x * (y + 34.56f) + y * (x + 34.56f);
    float r = fmodf(x * y + d, 1.0f);
    return r < 0 ? r + 1.0f : r;
}

static inline float g_noise(float x, float y) {
    float fx = floorf(x), fy = floorf(y);
    float tx = x - fx, ty = y - fy;
    tx = tx * tx * (3.0f - 2.0f * tx);
    ty = ty * ty * (3.0f - 2.0f * ty);
    float a = g_hash(fx, fy), b = g_hash(fx + 1.0f, fy);
    float c = g_hash(fx, fy + 1.0f), d = g_hash(fx + 1.0f, fy + 1.0f);
    float ab = a + (b - a) * tx;
    float cd = c + (d - c) * tx;
    return ab + (cd - ab) * ty;
}

// 0.78 .. 1.18 multiplier, only on up-facing surfaces, fading out with distance so the
// detail does not shimmer on the horizon
static inline float g_detail(const float n[3], const float wp[3], float dist) {
    float ny = fabsf(n[1]);
    if (ny < 0.75f) return 1.0f;
    float fade = 1.0f - fminf(1.0f, fmaxf(0.0f, (dist - 8.0f) * 0.045f));
    if (fade <= 0.001f) return 1.0f;
    float patch = g_noise(wp[0] * 0.21f, wp[2] * 0.21f);        // ~5 m patches
    float grain = g_noise(wp[0] * 2.3f + 3.0f, wp[2] * 2.3f);
    float fine = g_noise(wp[0] * 11.0f + 5.1f, wp[2] * 11.0f - 3.7f);
    float m = 0.80f + 0.22f * patch + 0.20f * grain + 0.10f * fine;
    // mown stripes, only where the surface is actually lawn (green dominant in world XZ)
    float stripe = 0.5f + 0.5f * sinf((wp[0] * 0.62f + wp[2] * 0.78f) * 1.35f);
    m *= 0.965f + 0.07f * stripe;
    return 1.0f + (m - 1.0f) * fade * (ny - 0.75f) * 4.0f;
}

// The same idea for walls and everything else vertical: plaster and stone are never a single
// flat value. Without this a sunlit white facade fills the screen as one blank sheet.
static inline float g_wall_detail(const float wp[3], float dist, bool foliage) {
    if (foliage) return 1.0f;
    float wf = 1.0f - fminf(1.0f, fmaxf(0.0f, (dist - 5.0f) * 0.075f));
    if (wf <= 0.002f) return 1.0f;
    float g1 = g_noise(wp[0] * 5.7f + wp[2] * 1.9f, wp[1] * 5.7f);
    float g2 = g_noise(wp[2] * 17.0f + 4.3f, wp[1] * 17.0f);
    return 1.0f + ((g1 - 0.5f) * 0.10f + (g2 - 0.5f) * 0.05f) * wf;
}

// N.V with a guard, in one place instead of three
static inline float imag_fix(float nl, float dot_, float vl) {
    if (nl < 1e-6f || vl < 1e-6f) return 1.0f;
    return dot_ / (nl * vl);
}

struct Tex {
    int w = 0, h = 0;
    std::vector<unsigned char> px;
};
static std::vector<Tex> g_tex;

static void load_textures(VModel& m) {
    g_tex.resize(m.textures.size());
    for (size_t i = 0; i < m.textures.size(); ++i) {
        int w, h, n;
        unsigned char* d = stbi_load_from_memory(m.texture_bytes((uint16_t)i),
                                                 (int)m.texture_length((uint16_t)i), &w, &h, &n, 4);
        if (!d) continue;
        g_tex[i].w = w;
        g_tex[i].h = h;
        g_tex[i].px.assign(d, d + (size_t)w * h * 4);
        stbi_image_free(d);
    }
}

static void sample(const Tex& t, float u, float v, float out[4]) {
    if (t.w == 0) {
        out[0] = out[1] = out[2] = out[3] = 1.0f;
        return;
    }
    u = u - floorf(u);
    v = v - floorf(v);
    int x = (int)(u * (float)t.w) % t.w;
    int y = (int)(v * (float)t.h) % t.h;
    const unsigned char* p = &t.px[((size_t)y * t.w + x) * 4];
    for (int i = 0; i < 4; ++i) out[i] = p[i] / 255.0f;
}

// ---------------------------------------------------------------- sky (mirrors the shader)
static void sky_colour(const float d[3], float out[3]) {
    const float y = d[1];
    const float t = y > 0.0f ? 1.0f - expf(-3.1f * y) : 0.0f;   // zenith weight
    // authored in linear light so that, through exposure + the ACES fit, this lands on a
    // late-afternoon sky rather than on white paper
    const float zen[3] = {0.105f, 0.175f, 0.335f};
    const float hor[3] = {0.330f, 0.360f, 0.390f};
    float c[3];
    for (int i = 0; i < 3; ++i) c[i] = hor[i] + (zen[i] - hor[i]) * t;
    // sun disc + glow in the same direction the model is lit from
    const GameSun s = game_sun();
    float cs = d[0] * s.dir[0] + d[1] * s.dir[1] + d[2] * s.dir[2];
    if (cs > 0.0f) {
        const float glow = powf(cs, 24.0f) * 0.55f + powf(cs, 4.0f) * 0.10f;
        const float disc = cs > 0.9985f ? 1.0f : powf(cs, 900.0f);
        for (int i = 0; i < 3; ++i) c[i] += s.sun_col[i] * 0.30f * glow + 30.0f * disc;
    }
    // thin altocumulus: noise projected onto a plane 260 m up, so the pattern converges
    // towards the horizon like real cloud rows instead of sticking to the viewport
    if (y > 0.03f) {
        float px = d[0] / (y + 0.10f) * 7.0f;
        float pz = d[2] / (y + 0.10f) * 7.0f;
        float f = 0.62f * g_noise(px, pz) + 0.26f * g_noise(px * 2.1f + 11.0f, pz * 2.1f) +
                  0.12f * g_noise(px * 4.3f, pz * 4.3f - 7.0f);
        float cov = (f - 0.56f) * 4.0f;
        cov = cov < 0.0f ? 0.0f : (cov > 1.0f ? 1.0f : cov);
        cov = cov * cov * (3.0f - 2.0f * cov);
        cov *= fminf(1.0f, y * 4.0f);          // thin out at the horizon
        float lit = 0.55f + 0.45f * fminf(1.0f, cs > 0.0f ? cs * 1.6f : 0.0f);
        const float cloud[3] = {0.105f, 0.115f, 0.132f};
        for (int i = 0; i < 3; ++i) c[i] = c[i] * (1.0f - cov * 0.85f) + cloud[i] * lit * cov * 0.85f;
    }
    // below the horizon: distant haze, never sky, because the garden ends at 87 m
    if (y < 0.0f) {
        float k = fminf(1.0f, -y * 6.0f);
        for (int i = 0; i < 3; ++i) c[i] = c[i] * (1.0f - k) + 0.10f * k;
    }
    for (int i = 0; i < 3; ++i) out[i] = fminf(1.0f, c[i]);
}

struct View {
    float eye[3], fwd[3], right[3], up[3];
    Mat4 vp;
};

static void make_view(const Game& g, View* v) {
    g.eye_pos(v->eye);
    g.look_dir(v->fwd);
    const float up[3] = {0.0f, 1.0f, 0.0f};
    float r[3] = {v->fwd[1] * up[2] - v->fwd[2] * up[1], v->fwd[2] * up[0] - v->fwd[0] * up[2],
                  v->fwd[0] * up[1] - v->fwd[1] * up[0]};
    float rl = sqrtf(r[0] * r[0] + r[1] * r[1] + r[2] * r[2]);
    if (rl < 1e-5f) {   // looking straight up/down: any right vector will do
        r[0] = 1; r[1] = 0; r[2] = 0; rl = 1;
    }
    for (int i = 0; i < 3; ++i) v->right[i] = r[i] / rl;
    v->up[0] = v->right[1] * v->fwd[2] - v->right[2] * v->fwd[1];
    v->up[1] = v->right[2] * v->fwd[0] - v->right[0] * v->fwd[2];
    v->up[2] = v->right[0] * v->fwd[1] - v->right[1] * v->fwd[0];
    float ctr[3] = {v->eye[0] + v->fwd[0], v->eye[1] + v->fwd[1], v->eye[2] + v->fwd[2]};
    Mat4 view = mat4_lookat(v->eye, ctr, up);
    Mat4 proj = mat4_perspective(kFovY, (float)W / H, 0.15f, 900.0f);
    v->vp = mat4_mul(proj, view);
}

struct Frame {
    std::vector<float> zbuf, col;   // col is linear HDR until post_process() runs
};

static void post_process(Frame* f, const View& v, bool want_rays);

struct Vtx {
    float p[3];    // world
    float c[4];    // clip
    float uv[2];
    float n[3];
    float ao;      // baked ambient visibility   (vertex byte 6)
    float sun;     // baked sun visibility       (vertex byte 7)
};

// Clip one triangle against the near plane (c[3] >= NEAR) and emit 0..3 triangles.
// Without this, any triangle that straddles the camera - a 70 m ground plane, every wall
// you stand next to - is dropped, which is exactly what made the lawn invisible here while
// the GPU (which clips for free) drew it fine.
static int clip_near(const Vtx in[3], Vtx out[6]) {
    const float NEAR = 0.06f;
    Vtx poly[4];
    int n = 0;
    for (int i = 0; i < 3; ++i) {
        const Vtx& a = in[i];
        const Vtx& b = in[(i + 1) % 3];
        const bool ina = a.c[3] >= NEAR;
        const bool inb = b.c[3] >= NEAR;
        if (ina) poly[n++] = a;
        if (ina != inb) {
            float t = (NEAR - a.c[3]) / (b.c[3] - a.c[3]);
            Vtx m;
            for (int k = 0; k < 4; ++k) m.c[k] = a.c[k] + (b.c[k] - a.c[k]) * t;
            for (int k = 0; k < 3; ++k) m.p[k] = a.p[k] + (b.p[k] - a.p[k]) * t;
            for (int k = 0; k < 2; ++k) m.uv[k] = a.uv[k] + (b.uv[k] - a.uv[k]) * t;
            for (int k = 0; k < 3; ++k) m.n[k] = a.n[k] + (b.n[k] - a.n[k]) * t;
            m.ao = a.ao + (b.ao - a.ao) * t;
            m.sun = a.sun + (b.sun - a.sun) * t;
            poly[n++] = m;
        }
    }
    int nt = 0;
    for (int i = 2; i < n; ++i) {
        out[nt++] = poly[0];
        out[nt++] = poly[i - 1];
        out[nt++] = poly[i];
    }
    return nt;
}


// A flat, shaded quad with near-clipping and perspective-correct world interpolation. Used
// for the ground skirt: the level's lawn is 87 m across and simply stops, which reads as the
// edge of the world. One huge quad a little below it, fogged into the sky, fixes that
// without any new art.
static void raster_flat(Frame* f, const View& v, const GameSun& gs, const float tri[3][3],
                        const float albedo[3]) {
    Vtx in[3];
    for (int k = 0; k < 3; ++k) {
        for (int i = 0; i < 3; ++i) in[k].p[i] = tri[k][i];
        for (int i = 0; i < 4; ++i)
            in[k].c[i] = in[k].p[0] * v.vp.m[i] + in[k].p[1] * v.vp.m[4 + i] +
                         in[k].p[2] * v.vp.m[8 + i] + v.vp.m[12 + i];
        in[k].uv[0] = in[k].uv[1] = 0.0f;
        in[k].n[0] = 0.0f;
        in[k].n[1] = 1.0f;
        in[k].n[2] = 0.0f;
    }
    Vtx cl[6];
    const int nc = clip_near(in, cl);
    const float tan_half = tanf(0.5f * kFovY);
    for (int cw = 0; cw + 2 < nc; cw += 3) {
        const Vtx* T = cl + cw;
        float iw[3], sx[3], sy2[3], sz[3];
        for (int k = 0; k < 3; ++k) {
            iw[k] = 1.0f / T[k].c[3];
            sx[k] = (T[k].c[0] * iw[k] * 0.5f + 0.5f) * W;
            sy2[k] = (1.0f - (T[k].c[1] * iw[k] * 0.5f + 0.5f)) * H;
            sz[k] = T[k].c[2] * iw[k];
        }
        const float area = (sx[1] - sx[0]) * (sy2[2] - sy2[0]) - (sx[2] - sx[0]) * (sy2[1] - sy2[0]);
        if (fabsf(area) < 1e-6f) continue;
        const float inv_area = 1.0f / area;
        const int x0 = (int)fmaxf(0, fminf(sx[0], fminf(sx[1], sx[2])));
        const int x1 = (int)fminf(W - 1, fmaxf(sx[0], fmaxf(sx[1], sx[2])));
        const int y0 = (int)fmaxf(0, fminf(sy2[0], fminf(sy2[1], sy2[2])));
        const int y1 = (int)fminf(H - 1, fmaxf(sy2[0], fmaxf(sy2[1], sy2[2])));
        for (int py = y0; py <= y1; ++py) {
            for (int px = x0; px <= x1; ++px) {
                const float fxp = px + 0.5f, fyp = py + 0.5f;
                float w0 = ((sx[1] - fxp) * (sy2[2] - fyp) - (sx[2] - fxp) * (sy2[1] - fyp)) * inv_area;
                float w1 = ((sx[2] - fxp) * (sy2[0] - fyp) - (sx[0] - fxp) * (sy2[2] - fyp)) * inv_area;
                float w2 = 1.0f - w0 - w1;
                if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                const float z = w0 * sz[0] + w1 * sz[1] + w2 * sz[2];
                const size_t idx = (size_t)py * W + px;
                if (z >= f->zbuf[idx]) continue;
                const float pw = w0 * iw[0] + w1 * iw[1] + w2 * iw[2];
                float wp[3] = {0, 0, 0};
                for (int k = 0; k < 3; ++k) {
                    const float wq = (k == 0 ? w0 : k == 1 ? w1 : w2) * iw[k] / pw;
                    for (int i = 0; i < 3; ++i) wp[i] += T[k].p[i] * wq;
                }
                const float dist = sqrtf((wp[0] - v.eye[0]) * (wp[0] - v.eye[0]) +
                                         (wp[1] - v.eye[1]) * (wp[1] - v.eye[1]) +
                                         (wp[2] - v.eye[2]) * (wp[2] - v.eye[2]));
                const float patch = g_noise(wp[0] * 0.05f, wp[2] * 0.05f);
                float alb[3] = {albedo[0] * (0.85f + 0.3f * patch),
                                albedo[1] * (0.85f + 0.3f * patch),
                                albedo[2] * (0.85f + 0.3f * patch)};
                (void)tan_half;
                const float Vx = v.eye[0] - wp[0], Vy = v.eye[1] - wp[1],
                            Vz = v.eye[2] - wp[2];
                const float vl = sqrtf(Vx * Vx + Vy * Vy + Vz * Vz);
                float ndv = vl > 1e-5f ? fabsf(wp[1] * 0.0f + (Vy) / vl) : 1.0f;
                const float fres = powf(1.0f - ndv, 3.0f);
                float rgb[3];
                game_shade_hdr(alb, alb, in[0].n, gs, 1.0f, 1.0f, rgb, fres);
                const float fog = game_fog(gs, dist);
                for (int i = 0; i < 3; ++i)
                    rgb[i] = rgb[i] * (1.0f - fog) + gs.fog_col[i] * gs.exposure * fog;
                f->zbuf[idx] = z;
                for (int i = 0; i < 3; ++i) f->col[idx * 3 + i] = fminf(40.0f, rgb[i]);
            }
        }
    }
}

static void draw_skirt(Frame* f, const View& v, const GameSun& gs, float y) {
    const float e = 420.0f;
    const float ex = v.eye[0], ez = v.eye[2];
    const float c[4][3] = {{ex - e, y, ez - e}, {ex + e, y, ez - e},
                           {ex - e, y, ez + e}, {ex + e, y, ez + e}};
    const int order[6] = {0, 1, 2, 2, 1, 3};
    // the lawn's own albedo, a little darker so it reads as meadow beyond the garden
    const float albedo[3] = {0.105f, 0.165f, 0.062f};
    for (int t = 0; t < 6; t += 3) {
        float tri[3][3];
        for (int k = 0; k < 3; ++k)
            for (int i = 0; i < 3; ++i) tri[k][i] = c[order[t + k]][i];
        raster_flat(f, v, gs, tri, albedo);
    }
}

static void render(const VModel& model, const Game& g, Frame* f) {
    View v;
    make_view(g, &v);
    f->zbuf.assign((size_t)W * H, 1e30f);
    f->col.assign((size_t)W * H * 3, 0.0f);
    const float tan_half = tanf(0.5f * kFovY);
    const GameSun gs = game_sun();
    // ---- sky, per pixel from the view ray, in linear light so it goes through the same
    // curve as the geometry (authoring it in display space made it read as black)
    for (int y = 0; y < H; ++y) {
        float sy = (1.0f - 2.0f * ((y + 0.5f) / H)) * tan_half;
        for (int x = 0; x < W; ++x) {
            float sx = (2.0f * ((x + 0.5f) / W) - 1.0f) * tan_half * (float)W / H;
            float d[3];
            for (int i = 0; i < 3; ++i) d[i] = v.fwd[i] + v.right[i] * sx + v.up[i] * sy;
            float l = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
            for (int i = 0; i < 3; ++i) d[i] /= l;
            float c[3];
            sky_colour(d, c);
            for (int i = 0; i < 3; ++i)
                f->col[((size_t)y * W + x) * 3 + i] = c[i] * gs.exposure;
        }
    }

    if (!getenv("MATID")) draw_skirt(f, v, gs, -0.55f);

    const bool matid = getenv("MATID") != nullptr;
    for (uint32_t di = 0; di < model.h.n_draws; ++di) {
        const VDraw& d = model.draws[di];
        const bool glass = (d.flags & 4u) != 0;
        const uint8_t* vb = model.draw_vertices(d);
        const uint16_t* ib = model.draw_indices(d);
        const Tex* tex = d.tex == VPK_NO_TEXTURE ? nullptr : &g_tex[d.tex];
        for (uint32_t t = 0; t + 2 < d.index_count; t += 3) {
            Vtx tri[3];
            for (int k = 0; k < 3; ++k) {
                const uint8_t* vv = vb + (size_t)ib[t + k] * VPK_VERTEX_STRIDE;
                const uint16_t* pq = (const uint16_t*)vv;
                const int8_t* nq = (const int8_t*)(vv + 8);
                const float* uvq = (const float*)(vv + 12);
                Vtx& o = tri[k];
                for (int i = 0; i < 3; ++i)
                    o.p[i] = d.pos_min[i] + (pq[i] / 65535.0f) * d.pos_scale[i];
                // ---- wind. Only alpha-tested foliage moves; a wall that breathes would be
                // worse than still air. The phase varies with world position so the garden
                // ripples in gusts instead of marching in lockstep.
                if ((d.flags & 1u) && g_wind > 0.0f) {
                    const float ph = o.p[0] * 0.31f + o.p[2] * 0.23f;
                    const float h = o.p[1] < 0.0f ? 0.0f : o.p[1];
                    const float amp = g_wind * (0.012f + 0.020f * h) *
                                      (0.7f + 0.3f * sinf(g_time * 0.37f + ph * 0.2f));
                    const float sw = sinf(g_time * 2.1f + ph) + 0.45f * sinf(g_time * 3.7f + ph * 1.7f);
                    o.p[0] += sw * amp;
                    o.p[2] += (0.6f * sinf(g_time * 1.7f + ph * 1.3f)) * amp;
                }
                for (int i = 0; i < 4; ++i)
                    o.c[i] = o.p[0] * v.vp.m[i] + o.p[1] * v.vp.m[4 + i] +
                             o.p[2] * v.vp.m[8 + i] + v.vp.m[12 + i];
                o.uv[0] = uvq[0];
                o.uv[1] = uvq[1];
                for (int i = 0; i < 3; ++i) o.n[i] = nq[i] / 127.0f;
                o.ao = vv[6] / 255.0f;
                o.sun = vv[7] / 255.0f;
            }
            Vtx cl[6];
            const int nc = clip_near(tri, cl);
            for (int cw = 0; cw + 2 < nc; cw += 3) {
                const Vtx* T = cl + cw;
                float iw[3], sx[3], sy2[3], sz[3];
                for (int k = 0; k < 3; ++k) {
                    iw[k] = 1.0f / T[k].c[3];
                    sx[k] = (T[k].c[0] * iw[k] * 0.5f + 0.5f) * W;
                    sy2[k] = (1.0f - (T[k].c[1] * iw[k] * 0.5f + 0.5f)) * H;
                    sz[k] = T[k].c[2] * iw[k];
                }
                float area = (sx[1] - sx[0]) * (sy2[2] - sy2[0]) - (sx[2] - sx[0]) * (sy2[1] - sy2[0]);
                if (fabsf(area) < 1e-6f) continue;
                if (!(d.flags & 2u) && area < 0.0f) continue;
                int x0 = (int)fmaxf(0, fminf(sx[0], fminf(sx[1], sx[2])));
                int x1 = (int)fminf(W - 1, fmaxf(sx[0], fmaxf(sx[1], sx[2])));
                int y0 = (int)fmaxf(0, fminf(sy2[0], fminf(sy2[1], sy2[2])));
                int y1 = (int)fminf(H - 1, fmaxf(sy2[0], fmaxf(sy2[1], sy2[2])));
                if (x1 < x0 || y1 < y0) continue;
                const float inv_area = 1.0f / area;
                for (int py = y0; py <= y1; ++py) {
                    for (int px = x0; px <= x1; ++px) {
                        float fxp = px + 0.5f, fyp = py + 0.5f;
                        float w0 = ((sx[1] - fxp) * (sy2[2] - fyp) - (sx[2] - fxp) * (sy2[1] - fyp)) * inv_area;
                        float w1 = ((sx[2] - fxp) * (sy2[0] - fyp) - (sx[0] - fxp) * (sy2[2] - fyp)) * inv_area;
                        float w2 = 1.0f - w0 - w1;
                        if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                        float z = w0 * sz[0] + w1 * sz[1] + w2 * sz[2];
                        size_t idx = (size_t)py * W + px;
                        if (!glass && z >= f->zbuf[idx]) continue;
                        float pw = w0 * iw[0] + w1 * iw[1] + w2 * iw[2];
                        float uv[2] = {0, 0}, n[3] = {0, 0, 0}, wp[3] = {0, 0, 0};
                        float aow = 1.0f, sunw = 1.0f;   // baked occlusion, interpolated
                        for (int k = 0; k < 3; ++k) {
                            float wq = (k == 0 ? w0 : k == 1 ? w1 : w2) * iw[k] / pw;
                            uv[0] += T[k].uv[0] * wq;
                            uv[1] += T[k].uv[1] * wq;
                            aow += T[k].ao * wq - wq;
                            sunw += T[k].sun * wq - wq;
                            for (int i = 0; i < 3; ++i) {
                                n[i] += T[k].n[i] * wq;
                                wp[i] += T[k].p[i] * wq;
                            }
                        }
                        // (aow/sunw start at 1 and accumulate value-minus-one, so an
                        // un-baked vertex - AO byte 255 - comes out at exactly 1)
                        float texel[4] = {1, 1, 1, 1};
                        if (tex) sample(*tex, uv[0], uv[1], texel);
                        if (d.alpha_cutoff > 0.0f && texel[3] < d.alpha_cutoff) continue;
                        float* c = &f->col[idx * 3];
                        if (d.flags & 8u) {                 // ---- water
                            // A pool is 8 triangles, so every bit of it has to be shading.
                            // Three things make water read as water: normals that move,
                            // a mirror of the sky, and a sun glint that is much brighter
                            // than the water around it.
                            const float dist = sqrtf((wp[0] - v.eye[0]) * (wp[0] - v.eye[0]) +
                                                     (wp[2] - v.eye[2]) * (wp[2] - v.eye[2]));
                            const float ao_w = 0.35f + 0.65f * aow;
                            const float sun_w = sunw;
                            float nx = 0.0f, nz = 0.0f;
                            {
                                const float t = g_time;
                                const float s1 = sinf(wp[0] * 3.1f + t * 1.9f) *
                                                 cosf(wp[2] * 2.7f - t * 1.3f);
                                const float s2 = sinf((wp[0] + wp[2]) * 7.3f - t * 2.6f);
                                const float s3 = cosf(wp[2] * 11.7f + wp[0] * 5.1f + t * 3.4f);
                                const float fade = 1.0f / (1.0f + dist * 0.35f);
                                nx = (s1 * 0.5f + s2 * 0.22f + s3 * 0.10f) * fade;
                                nz = (s2 * 0.4f - s3 * 0.16f) * fade;
                            }
                            float wn[3] = {nx * 0.9f, 1.0f, nz * 0.9f};
                            const float wl = sqrtf(wn[0] * wn[0] + wn[1] * wn[1] + wn[2] * wn[2]);
                            for (int i = 0; i < 3; ++i) wn[i] /= wl;
                            // reflection of the sky off a tilted surface
                            float Vd[3] = {v.eye[0] - wp[0], v.eye[1] - wp[1],
                                           v.eye[2] - wp[2]};
                            const float vl = sqrtf(Vd[0] * Vd[0] + Vd[1] * Vd[1] + Vd[2] * Vd[2]);
                            for (int i = 0; i < 3; ++i) Vd[i] /= vl;
                            const float ndv = -(Vd[0] * wn[0] + Vd[1] * wn[1] + Vd[2] * wn[2]);
                            float rd[3];
                            for (int i = 0; i < 3; ++i) rd[i] = Vd[i] + 2.0f * ndv * wn[i];
                            float sky_r[3];
                            sky_colour(rd, sky_r);
                            const float fren = 0.03f + 0.97f * powf(1.0f - fmaxf(ndv, 0.0f), 5.0f);
                            // sun glint: a tight specular lobe, widened by the ripples
                            float h[3] = {gs.dir[0] - Vd[0], gs.dir[1] - Vd[1], gs.dir[2] - Vd[2]};
                            const float hl = sqrtf(h[0] * h[0] + h[1] * h[1] + h[2] * h[2]);
                            for (int i = 0; i < 3; ++i) h[i] /= hl;
                            float ndh = fmaxf(0.0f, h[0] * wn[0] + h[1] * wn[1] + h[2] * wn[2]);
                            const float spec = powf(ndh, 900.0f) * 26.0f + powf(ndh, 90.0f) * 0.8f;
                            // body colour: shallow pool tile showing through
                            const float deep[3] = {0.035f, 0.105f, 0.115f};
                            for (int i = 0; i < 3; ++i) {
                                float col_ = deep[i] * (0.55f + 0.45f * ao_w) +
                                             sky_r[i] * (0.16f + 0.58f * fren) +
                                             gs.sun_col[i] * spec * sun_w;
                                c[i] = fminf(12.0f, col_ * gs.exposure);
                            }
                            float wfog = game_fog(gs, dist);
                            for (int i = 0; i < 3; ++i)
                                c[i] = c[i] * (1.0f - wfog) +
                                       gs.fog_col[i] * gs.exposure * wfog;
                            f->zbuf[idx] = z;
                            continue;
                        }
                        if (glass) {
                            // Glazing on GLES2 cannot be transparent, so it is drawn as what
                            // a window actually shows from outside: a dim room behind a cool
                            // sheet of sky reflection. Adding a bright tint (the first
                            // attempt) turned every window into a white lightbox.
                            float Vd[3] = {v.eye[0] - wp[0], v.eye[1] - wp[1], v.eye[2] - wp[2]};
                            const float vl = sqrtf(Vd[0] * Vd[0] + Vd[1] * Vd[1] + Vd[2] * Vd[2]);
                            for (int i = 0; i < 3; ++i) Vd[i] /= vl;
                            const float ndv = fmaxf(0.0f, -(Vd[0] * n[0] + Vd[1] * n[1] + Vd[2] * n[2]));
                            float rd[3];
                            for (int i = 0; i < 3; ++i) rd[i] = Vd[i] + 2.0f * ndv * n[i];
                            float sky_g[3];
                            sky_colour(rd, sky_g);
                            const float fren = 0.28f + 0.60f * powf(1.0f - ndv, 4.0f);
                            const float room[3] = {0.020f, 0.024f, 0.028f};
                            for (int i = 0; i < 3; ++i)
                                c[i] = (room[i] + sky_g[i] * fren * 0.55f +
                                        gs.sky_col[i] * 0.10f) * gs.exposure;
                            f->zbuf[idx] = z;
                            continue;
                        }
                        float dist = sqrtf((wp[0] - v.eye[0]) * (wp[0] - v.eye[0]) +
                                           (wp[1] - v.eye[1]) * (wp[1] - v.eye[1]) +
                                           (wp[2] - v.eye[2]) * (wp[2] - v.eye[2]));
                        const float Vx = v.eye[0] - wp[0], Vy = v.eye[1] - wp[1],
                                    Vz = v.eye[2] - wp[2];
                        const float vl = sqrtf(Vx * Vx + Vy * Vy + Vz * Vz);
                        const float nl_ = sqrtf(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
                        float ndv = imag_fix(nl_, Vx * n[0] + Vy * n[1] + Vz * n[2], vl);
                        if (ndv < 0.0f) ndv = 0.0f;
                        const float fres = powf(1.0f - ndv, 3.0f);
                        // a shadowed surface keeps its sky dome - the baked sun term is a
                        // visibility, so floor it or shade goes pitch black
                        const float ao_ = 0.26f + 0.74f * aow * aow;   // ^2: darker contact
                        const float sun_ = 0.10f + 0.90f * sunw;
                        (void)0;
                        float det = g_detail(n, wp, dist) *
                                    g_wall_detail(wp, dist, (d.flags & 1u) != 0);
                        float alb[3] = {texel[0] * det, texel[1] * det, texel[2] * det};
                        // The lawn texture is authored nearly black-green (0.03..0.10) for a
                        // Cycles render with a strong sun; under this pipeline that is a dark
                        // sheet. Lift the value, then pull the green towards olive so it
                        // matches the stills instead of glowing emerald.
                        {
                            float g0 = alb[1];
                            if (g0 > alb[0] * 1.25f && g0 > alb[2] * 1.25f) {
                                for (int i = 0; i < 3; ++i) alb[i] = powf(alb[i], 0.55f);
                                alb[0] *= 1.10f;
                                alb[1] *= 0.90f;
                                alb[2] *= 1.02f;
                            }
                        }
                        for (int i = 0; i < 3; ++i) alb[i] = fminf(alb[i], 0.75f);
                        if (d.flags & 1u) {   // foliage cards
                            float lum = 0.30f * alb[0] + 0.59f * alb[1] + 0.11f * alb[2];
                            for (int i = 0; i < 3; ++i) alb[i] = (lum * 0.55f + alb[i] * 0.45f) * 0.82f;
                        }
                        float rgb[3];
                        // smooth the baked values a little: a shadow edge that snaps from
                        // vertex to vertex across a 2.5 m quad is worse than a soft one
                        if (d.flags & 1u) {
                            // a leaf is a thin sheet, not a diffuse block: cut the direct
                            // sun term so the cards stop reading as gold plastic
                            game_shade_hdr(alb, d.base_color, n, gs, ao_ * 1.1f,
                                           sun_ * 0.55f, rgb, fres * 0.4f);
                        } else {
                            game_shade_hdr(alb, d.base_color, n, gs, ao_, sun_, rgb, fres);
                        }
                        if (matid) {
                            rgb[0] = ((di * 7) % 11) / 11.0f;
                            rgb[1] = ((di * 5) % 13) / 13.0f;
                            rgb[2] = ((di * 3) % 17) / 17.0f;
                        }
                        if (d.emissive[0] + d.emissive[1] + d.emissive[2] > 0.01f)
                            for (int i = 0; i < 3; ++i)
                                rgb[i] += d.emissive[i] * 6.0f;   // bulbs bloom properly
                        float fog = game_fog(gs, dist);
                        for (int i = 0; i < 3; ++i)
                            rgb[i] = rgb[i] * (1.0f - fog) +
                                     gs.fog_col[i] * gs.exposure * fog;
                        f->zbuf[idx] = z;
                        for (int i = 0; i < 3; ++i) c[i] = rgb[i] > 40.0f ? 40.0f : rgb[i];
                    }
                }
            }
        }
    }
    // objectives: additive billboards, so the autopilot's frames show what it walks to
    for (size_t i = 0; i < g.lv.objs.size(); ++i) {
        if (g.taken[i]) continue;
        const LevelObj& o = g.lv.objs[i];
        float cw[4];
        for (int k = 0; k < 4; ++k)
            cw[k] = o.x * v.vp.m[k] + o.y * v.vp.m[4 + k] + o.z * v.vp.m[8 + k] + v.vp.m[12 + k];
        if (cw[3] < 0.1f) continue;
        float cx = (cw[0] / cw[3] * 0.5f + 0.5f) * W;
        float cy = (1.0f - (cw[1] / cw[3] * 0.5f + 0.5f)) * H;
        float rad = 0.45f * H / (cw[3] * tan_half);
        if (rad < 1.0f) rad = 1.0f;
        for (int py = (int)fmaxf(0, cy - rad); py <= (int)fminf(H - 1, cy + rad); ++py) {
            for (int px = (int)fmaxf(0, cx - rad); px <= (int)fminf(W - 1, cx + rad); ++px) {
                float dx = (px + 0.5f - cx) / rad, dy = (py + 0.5f - cy) / rad;
                float r2 = dx * dx + dy * dy;
                if (r2 > 1.0f) continue;
                float a = (1.0f - r2) * (1.0f - r2) * 0.9f;
                float* c = &f->col[((size_t)py * W + px) * 3];
                c[0] = fminf(40.0f, c[0] + 2.4f * a);   // HDR: the orb is a light source
                c[1] = fminf(40.0f, c[1] + 1.9f * a);
                c[2] = fminf(40.0f, c[2] + 0.75f * a);
            }
        }
    }
}


// ------------------------------------------------------------------ post processing
// Order matters and it is the same order the device uses:
//   scene (HDR) -> bloom -> crepuscular rays -> ACES -> sRGB -> dither
// Bloom is a plain 5-tier pyramid with bilinear upsampling; on GLES2 that is six small
// framebuffers at 1/2, 1/4, 1/8, 1/16 of the target, which is cheap even at 1080p.

struct Img {
    int w = 0, h = 0;
    std::vector<float> px;   // rgb, linear
    void resize(int nw, int nh) {
        w = nw;
        h = nh;
        px.assign((size_t)w * h * 3, 0.0f);
    }
    float* at(int x, int y) { return &px[((size_t)y * w + x) * 3]; }
};

// separable box blur, repeated: close enough to a gaussian at these radii, and O(n)
static void blur(Img& img, int radius) {
    if (radius < 1) return;
    std::vector<float> tmp(img.px.size());
    const float inv = 1.0f / (2 * radius + 1);
    for (int y = 0; y < img.h; ++y) {
        for (int x = 0; x < img.w; ++x) {
            float acc[3] = {0, 0, 0};
            for (int k = -radius; k <= radius; ++k) {
                int xx = x + k;
                if (xx < 0) xx = 0;
                if (xx >= img.w) xx = img.w - 1;
                const float* s = img.at(xx, y);
                for (int i = 0; i < 3; ++i) acc[i] += s[i];
            }
            float* d = &tmp[((size_t)y * img.w + x) * 3];
            for (int i = 0; i < 3; ++i) d[i] = acc[i] * inv;
        }
    }
    for (int y = 0; y < img.h; ++y)
        for (int x = 0; x < img.w; ++x) {
            float acc[3] = {0, 0, 0};
            for (int k = -radius; k <= radius; ++k) {
                int yy = y + k;
                if (yy < 0) yy = 0;
                if (yy >= img.h) yy = img.h - 1;
                const float* s = &tmp[((size_t)yy * img.w + x) * 3];
                for (int i = 0; i < 3; ++i) acc[i] += s[i];
            }
            float* d = img.at(x, y);
            for (int i = 0; i < 3; ++i) d[i] = acc[i] * inv;
        }
}

// half-res box downsample (2x2 average)
static void downsample(const Img& src, Img* dst) {
    dst->resize((src.w + 1) / 2, (src.h + 1) / 2);
    for (int y = 0; y < dst->h; ++y)
        for (int x = 0; x < dst->w; ++x) {
            float acc[3] = {0, 0, 0};
            int n = 0;
            for (int dy = 0; dy < 2; ++dy)
                for (int dx = 0; dx < 2; ++dx) {
                    int sx = x * 2 + dx, sy = y * 2 + dy;
                    if (sx >= src.w || sy >= src.h) continue;
                    const float* s = &src.px[((size_t)sy * src.w + sx) * 3];
                    for (int i = 0; i < 3; ++i) acc[i] += s[i];
                    ++n;
                }
            float* d = dst->at(x, y);
            for (int i = 0; i < 3; ++i) d[i] = n ? acc[i] / n : 0.0f;
        }
}

// bilinear upsample and add
static void upsample_add(Img* dst, const Img& src, float weight) {
    for (int y = 0; y < dst->h; ++y) {
        float fy = (y + 0.5f) * src.h / dst->h - 0.5f;
        int y0 = (int)floorf(fy);
        float ty = fy - y0;
        int y1 = y0 + 1;
        y0 = y0 < 0 ? 0 : (y0 >= src.h ? src.h - 1 : y0);
        y1 = y1 < 0 ? 0 : (y1 >= src.h ? src.h - 1 : y1);
        for (int x = 0; x < dst->w; ++x) {
            float fx = (x + 0.5f) * src.w / dst->w - 0.5f;
            int x0 = (int)floorf(fx);
            float tx = fx - x0;
            int x1 = x0 + 1;
            x0 = x0 < 0 ? 0 : (x0 >= src.w ? src.w - 1 : x0);
            x1 = x1 < 0 ? 0 : (x1 >= src.w ? src.w - 1 : x1);
            const float* a = &src.px[((size_t)y0 * src.w + x0) * 3];
            const float* b = &src.px[((size_t)y0 * src.w + x1) * 3];
            const float* c = &src.px[((size_t)y1 * src.w + x0) * 3];
            const float* d = &src.px[((size_t)y1 * src.w + x1) * 3];
            float* o = dst->at(x, y);
            for (int i = 0; i < 3; ++i) {
                float top = a[i] + (b[i] - a[i]) * tx;
                float bot = c[i] + (d[i] - c[i]) * tx;
                o[i] += (top + (bot - top) * ty) * weight;
            }
        }
    }
}

// Sun position in screen space, for the rays. Returns false when the sun is behind you.
static bool sun_screen(const View& v, float* sx, float* sy) {
    const GameSun gs = game_sun();
    // a point 500 m towards the sun
    float p[3] = {v.eye[0] + gs.dir[0] * 500.0f, v.eye[1] + gs.dir[1] * 500.0f,
                  v.eye[2] + gs.dir[2] * 500.0f};
    float c[4];
    for (int i = 0; i < 4; ++i)
        c[i] = p[0] * v.vp.m[i] + p[1] * v.vp.m[4 + i] + p[2] * v.vp.m[8 + i] + v.vp.m[12 + i];
    if (c[3] <= 0.0f) return false;
    *sx = (c[0] / c[3] * 0.5f + 0.5f) * W;
    *sy = (1.0f - (c[1] / c[3] * 0.5f + 0.5f)) * H;
    return true;
}

// Crepuscular rays: march from each pixel towards the sun's screen position through a
// quarter-res brightness buffer. Only sky and foliage contribute, so a tree's silhouette
// cuts the shafts - which is the whole point of god rays.
static void god_rays(const Img& bright, const View& v, float strength, float* out) {
    float sx, sy;
    if (!sun_screen(v, &sx, &sy) || strength <= 0.0f) return;
    const int rw = bright.w, rh = bright.h;
    const float scale = (float)rw / (float)W;
    const float scx = sx * scale, scy = sy * scale;
    const int STEPS = 40;
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            float dx = (scx - x * scale);
            float dy = (scy - y * scale);
            float len = sqrtf(dx * dx + dy * dy) + 1e-3f;
            // step along the line to the sun, at most ~a quarter of the screen per sample
            float stepx = dx / len * 2.4f;
            float stepy = dy / len * 2.4f;
            float px = x * scale, py = y * scale;
            float acc[3] = {0, 0, 0};
            float decay = 1.0f;
            float wsum = 0.0f;
            for (int k = 0; k < STEPS; ++k) {
                px += stepx;
                py += stepy;
                if (px < 0 || py < 0 || px >= rw - 1 || py >= rh - 1) break;
                int ix = (int)px, iy = (int)py;
                const float* b = &bright.px[((size_t)iy * rw + ix) * 3];
                for (int i = 0; i < 3; ++i) acc[i] += b[i] * decay;
                wsum += decay;
                decay *= 0.955f;
            }
            if (wsum <= 0.0f) continue;
            // a soft distance falloff so the shafts fade before they smear over the frame
            float fall = expf(-len / (rw * 0.85f)) * strength;
            float* o = &out[((size_t)y * W + x) * 3];
            for (int i = 0; i < 3; ++i) o[i] = acc[i] / wsum * fall;
        }
    }
}

// Final composite: scene + bloom + rays, through ACES and sRGB, with a dither that stops
// the sky from banding (8-bit output over a 3-stop gradient bands horribly without it).
static void post_process(Frame* f, const View& v, bool want_rays) {
    Img scene, bright;
    scene.resize(W, H);
    for (size_t i = 0; i < (size_t)W * H * 3; ++i) scene.px[i] = f->col[i];

    // ---- bloom: threshold -> pyramid -> upsample back
    bright.resize(W / 4, H / 4);
    for (int y = 0; y < bright.h; ++y)
        for (int x = 0; x < bright.w; ++x) {
            float acc[3] = {0, 0, 0};
            for (int dy = 0; dy < 4; ++dy)
                for (int dx = 0; dx < 4; ++dx) {
                    int sx2 = x * 4 + dx, sy2 = y * 4 + dy;
                    if (sx2 >= W || sy2 >= H) continue;
                    const float* s = &scene.px[((size_t)sy2 * W + sx2) * 3];
                    for (int i = 0; i < 3; ++i) acc[i] += s[i];
                }
            float* d = bright.at(x, y);
            for (int i = 0; i < 3; ++i) {
                float c = acc[i] / 16.0f;
                // threshold with a soft knee at ~1.1
                float lum = c;
                d[i] = lum > 1.05f ? (lum - 1.05f) : 0.0f;
            }
        }

    if (want_rays) {
        // the rays read the same bright pass, blurred hard so the shafts are smooth
        Img ray_src = bright;
        blur(ray_src, 3);
        std::vector<float> rays((size_t)W * H * 3, 0.0f);
        god_rays(ray_src, v, 0.55f, rays.data());
        for (size_t i = 0; i < (size_t)W * H * 3; ++i) scene.px[i] += rays[i] * 0.45f;
    }

    Img p0 = bright;
    Img p1, p2, p3;
    downsample(p0, &p1);
    downsample(p1, &p2);
    downsample(p2, &p3);
    blur(p0, 2);
    blur(p1, 2);
    blur(p2, 2);
    blur(p3, 2);
    Img glow;
    glow.resize(p3.w, p3.h);
    for (size_t i = 0; i < (size_t)glow.w * glow.h * 3; ++i) glow.px[i] = p3.px[i] * 0.34f;
    upsample_add(&glow, p2, 0.75f);
    upsample_add(&glow, p1, 0.55f);
    upsample_add(&glow, p0, 0.35f);

    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            const size_t i = ((size_t)y * W + x) * 3;
            float c[3];
            // bilinear from the glow pyramid
            float fx = (x + 0.5f) * glow.w / W - 0.5f;
            float fy = (y + 0.5f) * glow.h / H - 0.5f;
            int x0 = (int)floorf(fx), y0 = (int)floorf(fy);
            float tx = fx - x0, ty = fy - y0;
            int x1 = x0 + 1, y1 = y0 + 1;
            x0 = x0 < 0 ? 0 : (x0 >= glow.w ? glow.w - 1 : x0);
            x1 = x1 < 0 ? 0 : (x1 >= glow.w ? glow.w - 1 : x1);
            y0 = y0 < 0 ? 0 : (y0 >= glow.h ? glow.h - 1 : y0);
            y1 = y1 < 0 ? 0 : (y1 >= glow.h ? glow.h - 1 : y1);
            const float* a0 = &glow.px[((size_t)y0 * glow.w + x0) * 3];
            const float* a1 = &glow.px[((size_t)y0 * glow.w + x1) * 3];
            const float* b0 = &glow.px[((size_t)y1 * glow.w + x0) * 3];
            const float* b1 = &glow.px[((size_t)y1 * glow.w + x1) * 3];
            for (int i2 = 0; i2 < 3; ++i2) {
                float top = a0[i2] + (a1[i2] - a0[i2]) * tx;
                float bot = b0[i2] + (b1[i2] - b0[i2]) * tx;
                c[i2] = scene.px[i + i2] + (top + (bot - top) * ty) * 0.34f;
            }
            // ACES + sRGB + ordered dither
            float d0 = ((x & 3) * 4 + (y & 3)) / 16.0f - 0.5f;
            for (int i2 = 0; i2 < 3; ++i2) {
                float v2 = game_tonemap(c[i2] > 0.0f ? c[i2] : 0.0f);
                v2 = fminf(1.0f, v2 + d0 * (1.0f / 255.0f));
                f->col[i + i2] = v2;
            }
        }
    }
    post_process(f, v, getenv("NOPOST") == nullptr);
}
static void write_ppm(const Frame& f, const char* path) {
    FILE* fp = std::fopen(path, "wb");
    if (!fp) {
        std::perror(path);
        return;
    }
    std::fprintf(fp, "P6\n%d %d\n255\n", W, H);
    std::vector<unsigned char> row((size_t)W * 3);
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x)
            for (int i = 0; i < 3; ++i) {
                float c = f.col[((size_t)y * W + x) * 3 + i];
                row[x * 3 + i] = (unsigned char)(fminf(1.0f, fmaxf(0.0f, c)) * 255.0f + 0.5f);
            }
        std::fwrite(row.data(), 1, row.size(), fp);
    }
    std::fclose(fp);
}

// ------------------------------------------------------------------------ BFS autopilot
struct Route {
    std::vector<int> cells;   // packed r*cols+c
};

// Can a body walk straight from a to b? The autopilot steers at the farthest path point it
// can actually see, the way a player does; steering waypoint-by-waypoint made the test walk
// into the inside corner of a hedge and stall, which is a fault of the *test*, not the level.
// Cells a body actually fits in. The path planner must only route through these: the level's
// walkable mask is a cell mask, and a cell that merely touches the boundary is somewhere a
// 0.52 m body cannot stand. Planning on the raw mask made the test walker aim at spots it
// could never occupy and then grind along the edge.
static std::vector<uint8_t> g_safe;

static void build_safe(const Level& lv) {
    g_safe.assign((size_t)lv.cols * lv.rows, 0);
    for (uint32_t r = 0; r < lv.rows; ++r)
        for (uint32_t c = 0; c < lv.cols; ++c) {
            if (!lv.walk[(size_t)r * lv.cols + c]) continue;
            const float x = lv.x0 + (c + 0.5f) * lv.cell;
            const float z = lv.z0 + (r + 0.5f) * lv.cell;
            g_safe[(size_t)r * lv.cols + c] = lv.body_fits(x, z, Game::kBodyRadius) ? 1 : 0;
        }
}

static bool line_ok(const Level& lv, float ax, float az, float bx, float bz) {
    const float dx = bx - ax, dz = bz - az;
    const float len = sqrtf(dx * dx + dz * dz);
    const int steps = (int)(len / 0.10f) + 1;
    for (int i = 0; i <= steps; ++i) {
        const float t = (float)i / (float)steps;
        const float px = ax + dx * t, pz = az + dz * t;
        int r, c;
        lv.to_cell(px, pz, &r, &c);
        if (!g_safe[(size_t)r * lv.cols + c]) return false;
    }
    return true;
}

static bool bfs(const Level& lv, int r0, int c0, int r1, int c1, Route* out) {
    const int n = (int)(lv.cols * lv.rows);
    std::vector<int> prev((size_t)n, -2);
    std::deque<int> q;
    const int start = r0 * (int)lv.cols + c0, goal = r1 * (int)lv.cols + c1;
    if (start < 0 || start >= n || goal < 0 || goal >= n) return false;
    if (!g_safe[start] || !g_safe[goal]) return false;
    prev[start] = -1;
    q.push_back(start);
    const int dr8[8] = {1, -1, 0, 0, 1, 1, -1, -1};
    const int dc8[8] = {0, 0, 1, -1, 1, -1, 1, -1};
    while (!q.empty()) {
        int cur = q.front();
        q.pop_front();
        if (cur == goal) break;
        int r = cur / (int)lv.cols, c = cur % (int)lv.cols;
        for (int k = 0; k < 8; ++k) {
            int rr = r + dr8[k], cc = c + dc8[k];
            if (rr < 0 || cc < 0 || rr >= (int)lv.rows || cc >= (int)lv.cols) continue;
            int ni = rr * (int)lv.cols + cc;
            if (prev[ni] != -2 || !g_safe[ni]) continue;
            // no corner cutting: a diagonal needs both orthogonal neighbours free
            if (k >= 4 && (!g_safe[r * (int)lv.cols + cc] || !g_safe[rr * (int)lv.cols + c]))
                continue;
            prev[ni] = cur;
            q.push_back(ni);
        }
    }
    if (prev[goal] == -2) return false;
    std::vector<int> rev;
    for (int c = goal; c != -1; c = prev[c]) rev.push_back(c);
    out->cells.assign(rev.rbegin(), rev.rend());
    return true;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s play|shot <assets_dir> <out_prefix|out.ppm> [shots]\n",
                     argv[0]);
        return 2;
    }
    const std::string mode = argv[1];
    const std::string assets = argv[2];
    const std::string out = argv[3];
    const int want_shots = argc > 4 ? atoi(argv[4]) : 0;

    VModel model;
    std::string err;
    if (!model.load_file((assets + "/model.vpk").c_str(), &err)) {
        std::fprintf(stderr, "model: %s\n", err.c_str());
        return 1;
    }
    load_textures(model);
    Game g;
    if (!g.init((assets + "/level.bin").c_str(), &err)) {
        std::fprintf(stderr, "level: %s\n", err.c_str());
        return 1;
    }
    std::printf("level %ux%u cells @ %.2f m, spawn %.2f %.2f %.2f, %d objectives\n",
                g.lv.cols, g.lv.rows, g.lv.cell, g.lv.spawn[0], g.lv.spawn[1], g.lv.spawn[2],
                g.total);

    build_safe(g.lv);
    {
        int n = 0;
        for (uint8_t v : g_safe) n += v ? 1 : 0;
        std::printf("body-safe cells: %d of %d walkable (%.1f%%)\n", n, (int)g.lv.walk.size(),
                    100.0 * n / (double)g.lv.walk.size());
    }

    // ---- static facts that must hold before anything is walked
    if (!g.lv.body_fits(g.lv.spawn[0], g.lv.spawn[2], Game::kBodyRadius)) {
        std::printf("FAIL: spawn does not fit a body\n");
        return 1;
    }
    for (size_t i = 0; i < g.lv.objs.size(); ++i) {
        const LevelObj& o = g.lv.objs[i];
        int r, c;
        g.lv.to_cell(o.x, o.z, &r, &c);
        if (!g_safe[(size_t)r * g.lv.cols + c]) {
            std::printf("FAIL: objective %zu is on a cell no body fits in\n", i);
            return 1;
        }
        if (!g.lv.body_fits(o.x, o.z, Game::kBodyRadius)) {
            std::printf("FAIL: objective %zu is inside geometry\n", i);
            return 1;
        }
        if (!g.lv.walk_at(o.x, o.z)) {
            std::printf("FAIL: objective %zu is not walkable\n", i);
            return 1;
        }
    }
    std::printf("objectives all stand on walkable ground\n");

    if (mode == "shot") {
        float angle = g.p.yaw;
        if (argc > 5) {
            g.p.feet[0] = (float)atof(argv[4]);
            g.p.feet[2] = (float)atof(argv[5]);
            g.p.feet[1] = g.lv.ground_at(g.p.feet[0], g.p.feet[2]);
            angle = (float)atof(argv[6]) * 3.14159265f / 180.0f;
            g.p.yaw = angle;
        }
        Frame f;
        render(model, g, &f);
        write_ppm(f, out.c_str());
        std::printf("wrote %s\n", out.c_str());
        return 0;
    }

    // ---- play: drive the real movement code to every objective, in order
    const float dt = 1.0f / 60.0f;
    int shots = 0;
    int frames = 0;
    float stuck_time = 0.0f;
    float walked = 0.0f;
    float back_time = 0.0f;
    float last_d[3] = {g.p.feet[0], g.p.feet[2], 0};
    int order[64];
    for (int i = 0; i < g.total && i < 64; ++i) order[i] = i;
    // visit nearest-first so the route does not zig-zag across the garden
    for (int i = 0; i < g.total; ++i)
        for (int j = i + 1; j < g.total; ++j) {
            float da = (g.lv.objs[order[i]].x - g.p.feet[0]) * (g.lv.objs[order[i]].x - g.p.feet[0]) +
                       (g.lv.objs[order[i]].z - g.p.feet[2]) * (g.lv.objs[order[i]].z - g.p.feet[2]);
            float db = (g.lv.objs[order[j]].x - g.p.feet[0]) * (g.lv.objs[order[j]].x - g.p.feet[0]) +
                       (g.lv.objs[order[j]].z - g.p.feet[2]) * (g.lv.objs[order[j]].z - g.p.feet[2]);
            if (db < da) {
                int t = order[i];
                order[i] = order[j];
                order[j] = t;
            }
        }

    std::printf("route:");
    for (int i = 0; i < g.total; ++i)
        std::printf(" (%.0f,%.0f)", g.lv.objs[order[i]].x, g.lv.objs[order[i]].z);
    std::printf("\n");

    for (int k = 0; k < g.total; ++k) {
        const LevelObj& target = g.lv.objs[order[k]];
        int r0, c0, r1, c1;
        g.lv.to_cell(g.p.feet[0], g.p.feet[2], &r0, &c0);
        g.lv.to_cell(target.x, target.z, &r1, &c1);
        Route route;
        if (!bfs(g.lv, r0, c0, r1, c1, &route)) {
            std::printf("FAIL: no route from cell %d,%d to objective %d at cell %d,%d\n", r0, c0,
                        k, r1, c1);
            return 1;
        }
        size_t wp = 0;
        stuck_time = 0;
        float best_togo = 1e30f;
        // start from the nearest path point, not necessarily index 0
        {
            float best = 1e30f;
            for (size_t i = 0; i < route.cells.size(); ++i) {
                const int cell = route.cells[i];
                const float wx = g.lv.x0 + (cell % (int)g.lv.cols + 0.5f) * g.lv.cell;
                const float wz = g.lv.z0 + (cell / (int)g.lv.cols + 0.5f) * g.lv.cell;
                const float d = (wx - g.p.feet[0]) * (wx - g.p.feet[0]) +
                                (wz - g.p.feet[2]) * (wz - g.p.feet[2]);
                if (d < best) {
                    best = d;
                    wp = i;
                }
            }
        }
        int guard = 60 * 240;   // a human would need ~40 s per leg at most
        while (g.taken[order[k]] == 0 && guard-- > 0) {
            if (wp < route.cells.size()) {
                // look ahead as far as the body can see in a straight line
                size_t best = wp;
                for (size_t j = wp + 1; j < route.cells.size() && j <= wp + 40; ++j) {
                    const int cell = route.cells[j];
                    const float wx = g.lv.x0 + (cell % (int)g.lv.cols + 0.5f) * g.lv.cell;
                    const float wz = g.lv.z0 + (cell / (int)g.lv.cols + 0.5f) * g.lv.cell;
                    if (line_ok(g.lv, g.p.feet[0], g.p.feet[2], wx, wz)) {
                        best = j;
                    } else {
                        break;
                    }
                }
                wp = best;
                const int cell = route.cells[wp];
                const float wx = g.lv.x0 + (cell % (int)g.lv.cols + 0.5f) * g.lv.cell;
                const float wz = g.lv.z0 + (cell / (int)g.lv.cols + 0.5f) * g.lv.cell;
                const float dx = wx - g.p.feet[0], dz = wz - g.p.feet[2];
                g.p.yaw = atan2f(dx, dz);          // the test steers instantly
                g.update(dt, 1.0f, 0.0f, 0.0f, 0.0f);
            } else {
                g.update(dt, 1.0f, 0.0f, 0.0f, 0.0f);
            }
            ++frames;
            // progress watchdog: catches a route that a point can walk but a body cannot
            float d = (g.p.feet[0] - last_d[0]) * (g.p.feet[0] - last_d[0]) +
                      (g.p.feet[2] - last_d[1]) * (g.p.feet[2] - last_d[1]);
            last_d[0] = g.p.feet[0];
            last_d[1] = g.p.feet[2];
            walked += sqrtf(d);
            // progress = getting closer to the objective. Jittering in place against a wall
            // counts as stuck even though the body technically moves.
            {
                float togo = (target.x - g.p.feet[0]) * (target.x - g.p.feet[0]) +
                             (target.z - g.p.feet[2]) * (target.z - g.p.feet[2]);
                if (togo < best_togo - 0.25f) {
                    best_togo = togo;
                    stuck_time = 0.0f;
                    back_time = 0.0f;
                } else {
                    stuck_time += dt;
                }
            }
            // a real player backs out of a corner; refusing to do so would fail levels a
            // human can walk
            if (stuck_time > 0.30f) {
                g.update(dt, -0.8f, 0.0f, 0.0f, 0.0f);
                back_time += dt;
                if (back_time > 0.45f) {
                    stuck_time = 0.0f;
                    back_time = 0.0f;
                }
            }
            if (stuck_time > 1.6f) {
                std::printf("FAIL: stuck at %.2f %.2f heading to objective %d (cell %d,%d)"
                            " ground %.2f walk %d\n",
                            g.p.feet[0], g.p.feet[2], k, r1, c1, g.p.feet[1],
                            (int)g.lv.walk_at(g.p.feet[0], g.p.feet[2]));
                // dump the neighbourhood: which cells are walkable, and what the body test
                // says about them, so the failure can be read instead of guessed at
                int rr, cc;
                g.lv.to_cell(g.p.feet[0], g.p.feet[2], &rr, &cc);
                for (int dr = -3; dr <= 3; ++dr) {
                    std::printf("    ");
                    for (int dc = -3; dc <= 3; ++dc) {
                        const int r = rr + dr, c = cc + dc;
                        if (r < 0 || c < 0 || r >= (int)g.lv.rows || c >= (int)g.lv.cols) {
                            std::printf(" #");
                            continue;
                        }
                        const float wx = g.lv.x0 + (c + 0.5f) * g.lv.cell;
                        const float wz = g.lv.z0 + (r + 0.5f) * g.lv.cell;
                        const bool w = g.lv.walk[(size_t)r * g.lv.cols + c] != 0;
                        const bool b = g.lv.body_fits(wx, wz, Game::kBodyRadius);
                        std::printf(" %c", w ? (b ? '.' : 'w') : '#');
                    }
                    std::printf("\n");
                }
                std::printf("    body_fits here: %d, ground %.2f, step limit %.2f\n",
                            (int)g.lv.body_fits(g.p.feet[0], g.p.feet[2], Game::kBodyRadius),
                            g.lv.ground_at(g.p.feet[0], g.p.feet[2]), Game::kStepUp);
                return 1;
            }
            if (!g.lv.walk_at(g.p.feet[0], g.p.feet[2])) {
                std::printf("FAIL: body left walkable ground at %.2f %.2f\n", g.p.feet[0],
                            g.p.feet[2]);
                return 1;
            }
            if (want_shots > 0 && frames % (60 * 6) == 0 && shots < want_shots) {
                Frame f;
                render(model, g, &f);
                char p[256];
                std::snprintf(p, sizeof p, "%s_%02d.ppm", out.c_str(), shots);
                write_ppm(f, p);
                std::printf("  shot %s (t=%.1fs, %.0f %.0f)\n", p, g.time, g.p.feet[0],
                            g.p.feet[2]);
                ++shots;
            }
        }
        if (g.taken[order[k]] == 0) {
            std::printf("FAIL: ran out of time reaching objective %d\n", k);
            return 1;
        }
        std::printf("  reached objective %d at t=%.1fs  pos %.2f %.2f %.2f\n", k, g.time,
                    g.p.feet[0], g.p.feet[1], g.p.feet[2]);
    }

    std::printf("PASS: collected %d/%d objectives in %.1f s of game time (%d frames, %.0f m "
                "walked)\n",
                g.orbs, g.total, g.time, frames, walked);
    std::printf("state=%d orbs=%d time=%.2f\n", g.state, g.orbs, g.time);
    return (g.state == 1 && g.orbs == g.total) ? 0 : 1;
}
