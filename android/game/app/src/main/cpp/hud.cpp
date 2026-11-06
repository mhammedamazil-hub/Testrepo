#include "hud.h"

#include <android/asset_manager.h>
#include <android/log.h>
#include <GLES2/gl2.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

#define LOG_TAG "VillaHud"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

#define STB_IMAGE_IMPLEMENTATION_ONCE
#include "stb_image.h"

namespace {

// One interleaved vertex: position (pixels), uv, rgba.
struct V {
    float x, y, u, v, r, g, b, a;
};

const char* kVSHud =
    "attribute vec2 a_p;\n"
    "attribute vec2 a_uv;\n"
    "attribute vec4 a_c;\n"
    "uniform vec2 u_screen;\n"          // w, h in pixels
    "varying vec2 v_uv;\n"
    "varying vec4 v_c;\n"
    "void main(){\n"
    "  vec2 ndc = vec2(a_p.x / u_screen.x * 2.0 - 1.0, 1.0 - a_p.y / u_screen.y * 2.0);\n"
    "  gl_Position = vec4(ndc, 0.0, 1.0);\n"
    "  v_uv = a_uv; v_c = a_c;\n"
    "}\n";

const char* kFSHud =
    "precision mediump float;\n"
    "varying vec2 v_uv;\n"
    "varying vec4 v_c;\n"
    "uniform sampler2D u_tex;\n"
    "uniform float u_use_tex;\n"
    "void main(){\n"
    "  vec4 t = u_use_tex > 0.5 ? texture2D(u_tex, v_uv) : vec4(1.0);\n"
    "  gl_FragColor = vec4(v_c.rgb * t.rgb, v_c.a * t.a);\n"
    "}\n";

enum Type { TYPE_SOLID = 0, TYPE_TEXT = 1 };

struct Hud {
    bool ready = false;
    int w = 1, h = 1;
    GLuint prog = 0, vbo = 0;
    GLint u_screen = -1, u_tex = -1, u_use_tex = -1;
    GLuint font = 0;
    int atlas_cols = 16, atlas_rows = 6, cell_w = 30, cell_h = 44;
    bool have_font = false;
    std::vector<V> verts;
    Type type = TYPE_SOLID;
    float r = 1, g = 1, b = 1, a = 1;
    GLuint last_bound = (GLuint)-1;

    void flush() {
        if (verts.empty()) return;
        glUniform1f(u_use_tex, type == TYPE_TEXT ? 1.0f : 0.0f);
        if (type == TYPE_TEXT && last_bound != font) {
            glBindTexture(GL_TEXTURE_2D, font);
            last_bound = font;
        }
        glBindBuffer(GL_ARRAY_BUFFER, vbo);
        glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)(verts.size() * sizeof(V)), verts.data(),
                     GL_STREAM_DRAW);
        // 8 floats per vertex: x,y,u,v,r,g,b,a
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)0);
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, sizeof(V), (void*)(2 * sizeof(float)));
        glVertexAttribPointer(2, 4, GL_FLOAT, GL_FALSE, sizeof(V), (void*)(4 * sizeof(float)));
        glDrawArrays(GL_TRIANGLES, 0, (GLsizei)verts.size());
        verts.clear();
    }

    void set_type(Type t) {
        if (t == type) return;
        flush();
        type = t;
    }

    void set_colour(float cr, float cg, float cb, float ca) {
        r = cr;
        g = cg;
        b = cb;
        a = ca;
    }

    void push(float x, float y, float u, float v) {
        verts.push_back(V{x, y, u, v, r, g, b, a});
    }

    void quad(float x, float y, float w, float h, float u0, float v0, float u1, float v1) {
        push(x, y, u0, v0);
        push(x + w, y, u1, v0);
        push(x, y + h, u0, v1);
        push(x + w, y, u1, v0);
        push(x + w, y + h, u1, v1);
        push(x, y + h, u0, v1);
    }
};

Hud H;

GLuint compile(GLenum type, const char* src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetShaderInfoLog(s, sizeof log, nullptr, log);
        LOGE("hud shader: %s", log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

// The atlas and its header ship as assets, so the font is identical on every device and the
// build never depends on a system font being installed.
bool load_font(AAssetManager* mgr) {
    if (!mgr) return false;
    // header
    AAsset* f = AAssetManager_open(mgr, "hud_font.txt", AASSET_MODE_BUFFER);
    if (f) {
        char buf[128] = {0};
        const int n = AAsset_read(f, buf, sizeof buf - 1);
        AAsset_close(f);
        if (n > 0) {
            int first = 32, count = 95;
            if (std::sscanf(buf, "%d %d %d %d %d %d", &H.atlas_cols, &H.atlas_rows, &H.cell_w,
                            &H.cell_h, &first, &count) < 6) {
                LOGE("hud_font.txt is malformed: %s", buf);
                return false;
            }
        }
    } else {
        LOGE("hud_font.txt missing");
        return false;
    }
    AAsset* p = AAssetManager_open(mgr, "hud_font.png", AASSET_MODE_BUFFER);
    if (!p) {
        LOGE("hud_font.png missing");
        return false;
    }
    const void* data = AAsset_getBuffer(p);
    const off_t len = AAsset_getLength(p);
    int w = 0, h = 0, n = 0;
    unsigned char* px = stbi_load_from_memory((const unsigned char*)data, (int)len, &w, &h, &n, 4);
    AAsset_close(p);
    if (!px) {
        LOGE("hud_font.png failed to decode");
        return false;
    }
    glGenTextures(1, &H.font);
    glBindTexture(GL_TEXTURE_2D, H.font);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, px);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    stbi_image_free(px);
    H.have_font = true;
    LOGI("hud font %dx%d, %dx%d cells", w, h, H.atlas_cols, H.atlas_rows);
    return true;
}

}  // namespace

bool hud_init(AAssetManager* mgr) {
    if (H.ready) return true;
    GLuint vs = compile(GL_VERTEX_SHADER, kVSHud);
    GLuint fs = compile(GL_FRAGMENT_SHADER, kFSHud);
    if (!vs || !fs) return false;
    H.prog = glCreateProgram();
    glAttachShader(H.prog, vs);
    glAttachShader(H.prog, fs);
    glBindAttribLocation(H.prog, 0, "a_p");
    glBindAttribLocation(H.prog, 1, "a_uv");
    glBindAttribLocation(H.prog, 2, "a_c");
    glLinkProgram(H.prog);
    glDeleteShader(vs);
    glDeleteShader(fs);
    GLint ok = 0;
    glGetProgramiv(H.prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetProgramInfoLog(H.prog, sizeof log, nullptr, log);
        LOGE("hud link: %s", log);
        H.prog = 0;
        return false;
    }
    H.u_screen = glGetUniformLocation(H.prog, "u_screen");
    H.u_tex = glGetUniformLocation(H.prog, "u_tex");
    H.u_use_tex = glGetUniformLocation(H.prog, "u_use_tex");
    glGenBuffers(1, &H.vbo);
    load_font(mgr);
    H.ready = true;
    H.verts.reserve(4096);
    return true;
}

void hud_begin(int w, int h) {
    H.w = w > 0 ? w : 1;
    H.h = h > 0 ? h : 1;
    H.verts.clear();
    H.type = TYPE_SOLID;
    H.set_colour(1, 1, 1, 1);
    if (!H.ready) return;
    glUseProgram(H.prog);
    glUniform2f(H.u_screen, (float)H.w, (float)H.h);
    glUniform1i(H.u_tex, 0);
    glUniform1f(H.u_use_tex, 0.0f);
    glActiveTexture(GL_TEXTURE0);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    // the HUD is drawn over the finished frame, in the order it is submitted
    for (int i = 0; i < 4; ++i) {
        if (i < 3) glEnableVertexAttribArray((GLuint)i);
        else glDisableVertexAttribArray((GLuint)i);
    }
    H.last_bound = (GLuint)-1;
}

void hud_end() {
    if (H.ready) H.flush();
    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
}

void hud_on_gl_lost() {
    H.ready = false;
    H.have_font = false;
    H.font = 0;
    H.prog = 0;
    H.vbo = 0;
    H.verts.clear();
}

void hud_shutdown() {
    if (!H.ready) return;
    if (H.vbo) glDeleteBuffers(1, &H.vbo);
    if (H.font) glDeleteTextures(1, &H.font);
    if (H.prog) glDeleteProgram(H.prog);
    hud_on_gl_lost();
}

void hud_rect(float x, float y, float w, float h, float r, float g, float b, float a) {
    if (!H.ready) return;
    H.set_type(TYPE_SOLID);
    H.set_colour(r, g, b, a);
    H.quad(x, y, w, h, 0, 0, 0, 0);
}

void hud_panel(float x, float y, float w, float h) {
    hud_rect(x, y, w, h, 0.063f, 0.078f, 0.094f, 0.72f);
    // one hairline along the top edge reads as a card rather than a smudge
    hud_rect(x, y, w, 1.5f, 1.0f, 1.0f, 1.0f, 0.06f);
}

void hud_disc(float cx, float cy, float radius, float r, float g, float b, float a) {
    if (!H.ready) return;
    H.set_type(TYPE_SOLID);
    H.set_colour(r, g, b, a);
    const int seg = 32;
    for (int i = 0; i < seg; ++i) {
        const float a0 = (float)i / seg * 6.2831853f;
        const float a1 = (float)(i + 1) / seg * 6.2831853f;
        H.push(cx, cy, 0, 0);
        H.push(cx + cosf(a0) * radius, cy + sinf(a0) * radius, 0, 0);
        H.push(cx + cosf(a1) * radius, cy + sinf(a1) * radius, 0, 0);
    }
}

void hud_ring(float cx, float cy, float radius, float thickness, float r, float g, float b,
              float a) {
    if (!H.ready) return;
    H.set_type(TYPE_SOLID);
    H.set_colour(r, g, b, a);
    const int seg = 48;
    const float ri = radius - thickness;
    for (int i = 0; i < seg; ++i) {
        const float a0 = (float)i / seg * 6.2831853f;
        const float a1 = (float)(i + 1) / seg * 6.2831853f;
        const float c0 = cosf(a0), s0 = sinf(a0), c1 = cosf(a1), s1 = sinf(a1);
        H.push(cx + c0 * ri, cy + s0 * ri, 0, 0);
        H.push(cx + c0 * radius, cy + s0 * radius, 0, 0);
        H.push(cx + c1 * ri, cy + s1 * ri, 0, 0);
        H.push(cx + c1 * ri, cy + s1 * ri, 0, 0);
        H.push(cx + c0 * radius, cy + s0 * radius, 0, 0);
        H.push(cx + c1 * radius, cy + s1 * radius, 0, 0);
    }
}

void hud_dim(float alpha) {
    hud_rect(0, 0, (float)H.w, (float)H.h, 0.02f, 0.03f, 0.04f, alpha);
}

float hud_text_width(const char* text, float size) {
    if (!text) return 0;
    const float scale = size / (float)H.cell_h;
    return (float)std::strlen(text) * (float)H.cell_w * scale * 0.82f;
}

void hud_text(const char* text, float x, float y, float size, float r, float g, float b, float a) {
    if (!H.ready || !text) return;
    if (!H.have_font) {   // no atlas: draw the message as a bar so it is at least visible
        hud_rect(x, y, hud_text_width(text, size), size * 0.6f, r, g, b, a * 0.6f);
        return;
    }
    H.set_type(TYPE_TEXT);
    H.set_colour(r, g, b, a);
    const float scale = size / (float)H.cell_h;      // size = pixel height of a cap
    const float cw = (float)H.cell_w * scale;
    const float ch = (float)H.cell_h * scale;
    const float du = 1.0f / (float)(H.atlas_cols * H.cell_w);
    const float dv = 1.0f / (float)(H.atlas_rows * H.cell_h);
    float cx = x;
    for (const char* p = text; *p; ++p) {
        int code = (unsigned char)*p;
        if (code < 32 || code > 126) code = '?';
        const int idx = code - 32;
        const int col = idx % H.atlas_cols;
        const int row = idx / H.atlas_cols;
        const float u0 = (float)(col * H.cell_w) * du;
        const float v0 = (float)(row * H.cell_h) * dv;
        const float u1 = u0 + (float)H.cell_w * du;
        const float v1 = v0 + (float)H.cell_h * dv;
        H.quad(cx, y, cw, ch, u0, v0, u1, v1);
        cx += cw * 0.82f;      // the cells have slack; tighten so text does not look spaced out
    }
}

void hud_text_right(const char* text, float right_x, float y, float size, float r, float g,
                    float b, float a) {
    hud_text(text, right_x - hud_text_width(text, size), y, size, r, g, b, a);
}

void hud_text_centered(const char* text, float cx, float y, float size, float r, float g,
                       float b, float a) {
    hud_text(text, cx - hud_text_width(text, size) * 0.5f, y, size, r, g, b, a);
}

void hud_crosshair(float cx, float cy, float radius, float dp) {
    hud_disc(cx, cy, radius + 1.5f * dp, 0.0f, 0.0f, 0.0f, 0.55f);
    hud_disc(cx, cy, radius, 1.0f, 1.0f, 1.0f, 0.85f);
}

void hud_chevron(float cx, float cy, float size, float bearing, float dp) {
    if (!H.ready) return;
    // bearing is 0 = ahead, +pi/2 = to the right; the glyph points up when ahead
    const float ang = bearing - 1.5707963f;
    H.set_type(TYPE_SOLID);
    H.set_colour(1.0f, 0.80f, 0.25f, 1.0f);
    const float c = cosf(ang), s = sinf(ang);
    const float pts[3][2] = {{0.0f, -size}, {size * 0.72f, size * 0.72f}, {-size * 0.72f, size * 0.72f}};
    for (int i = 0; i < 3; ++i) {
        H.push(cx + pts[i][0] * c - pts[i][1] * s, cy + pts[i][0] * s + pts[i][1] * c, 0, 0);
    }
    (void)dp;
}

void hud_diag(const char* text) {
    if (!text || !*text) return;
    // count lines so the panel can be sized before it is drawn
    int lines = 1;
    size_t longest = 0, run = 0;
    for (const char* p = text; *p; ++p) {
        if (*p == '\n') {
            ++lines;
            if (run > longest) longest = run;
            run = 0;
        } else {
            ++run;
        }
    }
    if (run > longest) longest = run;
    const float dp = (float)H.h / 800.0f;
    const float size = 10.0f * dp;
    const float lh = size * 1.30f;
    const float w = (float)longest * (float)H.cell_w * (size / (float)H.cell_h) * 0.82f +
                    14.0f * dp;
    const float h = lh * (float)lines + 10.0f * dp;
    const float x = 9.0f * dp;
    const float y = (float)H.h - h - 9.0f * dp;
    hud_rect(x, y, w, h, 0.03f, 0.035f, 0.045f, 0.62f);
    float ty = y + 5.0f * dp + size;
    std::string line;
    for (const char* p = text;; ++p) {
        if (*p == '\n' || *p == '\0') {
            hud_text(line.c_str(), x + 7.0f * dp, ty, size, 0.88f, 0.91f, 0.94f, 0.95f);
            line.clear();
            if (*p == '\0') break;
            ty += lh;
        } else {
            line.push_back(*p);
        }
    }
}
