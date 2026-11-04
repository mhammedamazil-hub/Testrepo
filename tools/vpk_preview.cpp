// Desktop verification tool for the VPK pack + the shading maths.
//
//   g++ -O2 -std=c++17 tools/vpk_preview.cpp \
//       android/viewer/app/src/main/cpp/vpk.cpp -Iandroid/viewer/app/src/main/cpp -o /tmp/vpkpreview
//   /tmp/vpkpreview model.vpk out.ppm [yaw_deg] [pitch_deg] [dist]
//
// It uses the SAME vpk.cpp loader and the SAME shading/camera maths as the Android app,
// then rasterises in software (z-buffer, perspective-correct uv). Use it to prove the pack
// is right before trusting an APK: if this image looks like the villa, the vertex order,
// quantisation, indices, textures, alpha cutouts and lighting are all correct.
//
// This is a test tool, not the deliverable.
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#include "stb_image.h"

#include "shade.h"
#include "vpk.h"

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
                                                 (int)m.texture_length((uint16_t)i), &w, &h,
                                                 &n, 4);
        if (!d) {
            std::fprintf(stderr, "texture %zu failed: %s\n", i, stbi_failure_reason());
            continue;
        }
        g_tex[i].w = w; g_tex[i].h = h;
        g_tex[i].px.assign(d, d + (size_t)w * h * 4);
        stbi_image_free(d);
    }
}

static void sample(const Tex& t, float u, float v, float out[4]) {
    if (t.w == 0) { out[0] = out[1] = out[2] = out[3] = 1.0f; return; }
    u = u - floorf(u);
    v = v - floorf(v);
    int x = (int)(u * (float)t.w) % t.w;
    int y = (int)(v * (float)t.h) % t.h;
    const unsigned char* p = &t.px[((size_t)y * t.w + x) * 4];
    for (int i = 0; i < 4; ++i) out[i] = p[i] / 255.0f;
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::fprintf(stderr, "usage: %s model.vpk out.ppm [yaw_deg pitch_deg dist_m]\n", argv[0]);
        return 2;
    }
    const int W = argc > 6 ? 900 : 900, H = W * 9 / 16;
    VModel model;
    std::string err;
    if (!model.load_file(argv[1], &err)) {
        std::fprintf(stderr, "load failed: %s\n", err.c_str());
        return 1;
    }
    std::printf("VPK ok: %u draws, %u textures, %u verts, %u indices\n", model.h.n_draws,
                model.h.n_textures, model.h.n_verts, model.h.n_indices);
    load_textures(model);

    OrbitCam cam;
    model.centre(cam.target);
    cam.dist = 1.55f * model.radius();
    if (argc > 3) cam.yaw = (float)atof(argv[3]) * 3.14159265f / 180.0f;
    if (argc > 4) cam.pitch = (float)atof(argv[4]) * 3.14159265f / 180.0f;
    if (argc > 5) cam.dist = (float)atof(argv[5]);
    std::printf("camera target %.2f %.2f %.2f dist %.1f yaw %.2f pitch %.2f\n",
                cam.target[0], cam.target[1], cam.target[2], cam.dist, cam.yaw, cam.pitch);

    Mat4 vp;
    cam.view_proj((float)W / H, &vp);
    std::vector<float> zbuf((size_t)W * H, 1e30f);
    std::vector<float> col((size_t)W * H * 3, 0.0f);

    // sky gradient background, same idea as the app's full-screen quad
    for (int y = 0; y < H; ++y) {
        float t = (float)y / H;
        float r = 0.62f + 0.16f * t, g = 0.71f + 0.13f * t, b = 0.82f + 0.10f * t;
        // below the horizon the backdrop is distant ground, not sky
        float gy = 0.5f + 0.5f * sinf(0.0f);
        (void)gy;
        for (int x = 0; x < W; ++x) {
            float* c = &col[((size_t)y * W + x) * 3];
            c[0] = r; c[1] = g; c[2] = b;
        }
    }

    const Vsun sun = vpk_default_sun();
    long tris = 0, drawn = 0;
    for (uint32_t di = 0; di < model.h.n_draws; ++di) {
        const VDraw& d = model.draws[di];
        const uint8_t* vb = model.draw_vertices(d);
        const uint16_t* ib = model.draw_indices(d);
        const Tex* tex = d.tex == VPK_NO_TEXTURE ? nullptr : &g_tex[d.tex];
        for (uint32_t t = 0; t + 2 < d.index_count; t += 3) {
            ++tris;
            float sc[3][4];  // clip-space x,y,z,w
            int inside = 0;
            for (int k = 0; k < 3; ++k) {
                const uint8_t* v = vb + (size_t)ib[t + k] * VPK_VERTEX_STRIDE;
                const uint16_t* pq = (const uint16_t*)v;
                float wp[3];
                for (int i = 0; i < 3; ++i)
                    wp[i] = d.pos_min[i] + (pq[i] / 65535.0f) * d.pos_scale[i];
                float c[4];
                for (int i = 0; i < 4; ++i)
                    c[i] = wp[0] * vp.m[i] + wp[1] * vp.m[4 + i] + wp[2] * vp.m[8 + i] + vp.m[12 + i];
                for (int i = 0; i < 4; ++i) sc[k][i] = c[i];
                if (c[3] > 0.05f) ++inside;
            }
            if (inside < 3) continue;  // fully behind the eye
            float sx[3], sy[3], sz[3], iw[3];
            for (int k = 0; k < 3; ++k) {
                float w = sc[k][3];
                iw[k] = 1.0f / w;
                sx[k] = (sc[k][0] * iw[k] * 0.5f + 0.5f) * W;
                sy[k] = (1.0f - (sc[k][1] * iw[k] * 0.5f + 0.5f)) * H;
                sz[k] = sc[k][2] * iw[k];
            }
            float area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0]);
            if (fabsf(area) < 1e-6f) continue;
            // screen y is flipped, so a GL front face (CCW) has negative area here
            if (!(d.flags & 2u) && area < 0.0f) continue;
            int x0 = (int)fmaxf(0, fminf(sx[0], fminf(sx[1], sx[2])));
            int x1 = (int)fminf(W - 1, fmaxf(sx[0], fmaxf(sx[1], sx[2])));
            int y0 = (int)fmaxf(0, fminf(sy[0], fminf(sy[1], sy[2])));
            int y1 = (int)fminf(H - 1, fmaxf(sy[0], fmaxf(sy[1], sy[2])));
            if (x1 < x0 || y1 < y0) continue;
            ++drawn;
            const float inv_area = 1.0f / area;
            for (int py = y0; py <= y1; ++py) {
                for (int px = x0; px <= x1; ++px) {
                    float fxp = px + 0.5f, fyp = py + 0.5f;
                    float w0 = ((sx[1] - fxp) * (sy[2] - fyp) - (sx[2] - fxp) * (sy[1] - fyp)) * inv_area;
                    float w1 = ((sx[2] - fxp) * (sy[0] - fyp) - (sx[0] - fxp) * (sy[2] - fyp)) * inv_area;
                    float w2 = 1.0f - w0 - w1;
                    if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                    float z = w0 * sz[0] + w1 * sz[1] + w2 * sz[2];
                    size_t idx = (size_t)py * W + px;
                    if (z >= zbuf[idx]) continue;
                    // perspective-correct attributes
                    float pw = w0 * iw[0] + w1 * iw[1] + w2 * iw[2];
                    float uv[2] = {0, 0}, n[3] = {0, 1, 0};
                    for (int k = 0; k < 3; ++k) {
                        const uint8_t* v = vb + (size_t)ib[t + k] * VPK_VERTEX_STRIDE;
                        const int8_t* nq = (const int8_t*)(v + 8);
                        const float* uvq = (const float*)(v + 12);
                        float wq = (k == 0 ? w0 : k == 1 ? w1 : w2) * iw[k] / pw;
                        uv[0] += uvq[0] * wq;
                        uv[1] += uvq[1] * wq;
                        for (int i = 0; i < 3; ++i) n[i] += (nq[i] / 127.0f) * wq;
                    }
                    float texel[4] = {1, 1, 1, 1};
                    if (tex) sample(*tex, uv[0], uv[1], texel);
                    if (d.alpha_cutoff > 0.0f && texel[3] < d.alpha_cutoff) continue;
                    // glass: dark cool tint, no depth write, blended over what is behind
                    const bool glass = (d.flags & 4u) != 0;
                    if (glass) {
                        const float tint[3] = {0.10f, 0.13f, 0.15f};
                        float* c = &col[idx * 3];
                        float sh = 0.55f + 0.45f * (n[1] > 0 ? n[1] : 0.0f);
                        for (int i = 0; i < 3; ++i)
                            c[i] = c[i] * (1.0f - 0.62f) + tint[i] * sh * 0.62f;
                        continue;   // keep the background depth
                    }
                    float rgb[3];
                    vpk_shade(texel, d.base_color, n, sun, 1.15f, 1.0f, 0.6f, rgb);
                    if (d.emissive[0] + d.emissive[1] + d.emissive[2] > 0.01f)
                        for (int i = 0; i < 3; ++i) rgb[i] += d.emissive[i] * 0.6f;
                    zbuf[idx] = z;
                    float* c = &col[idx * 3];
                    for (int i = 0; i < 3; ++i) c[i] = rgb[i] > 1.0f ? 1.0f : rgb[i];
                }
            }
        }
    }

    FILE* f = std::fopen(argv[2], "wb");
    std::fprintf(f, "P6\n%d %d\n255\n", W, H);
    std::vector<unsigned char> row((size_t)W * 3);
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x)
            for (int i = 0; i < 3; ++i) {
                float c = col[((size_t)y * W + x) * 3 + i];
                row[x * 3 + i] = (unsigned char)(powf(c, 1.0f) * 255.0f + 0.5f);
            }
        std::fwrite(row.data(), 1, row.size(), f);
    }
    std::fclose(f);
    std::printf("rasterised %ld tris (%ld survived culling) -> %s\n", tris, drawn, argv[2]);
    return 0;
}
