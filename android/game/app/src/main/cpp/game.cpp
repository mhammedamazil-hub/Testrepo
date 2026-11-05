// Villa Garden — the renderer and the JNI glue.
//
// Everything that decides how the picture looks is in three places and they are kept in
// sync on purpose:
//   * game_shade.h  - sun, sky/ground ambient, exposure, fog, the ACES curve
//   * game_core.h   - the player, the collision, the objectives
//   * this file     - GLES2 programs that evaluate game_shade.h's maths per pixel
// tools/game_sim.cpp compiles the first two on the desktop and rasterises in software, so
// the look and the walking are tested before an APK is built.
//
// GLES2 only: no MRT, no texture arrays, no derivatives, no float textures, no instancing.
// That is what lets this run on a 2015 tablet at 60 fps.
#include <android/asset_manager.h>
#include <android/asset_manager_jni.h>
#include <android/log.h>
#include <jni.h>

#include <GLES2/gl2.h>

#include <cmath>
#include <cstdio>
#include <cstring>
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

#define LOG_TAG "VillaGame"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

// ------------------------------------------------------------------ shader sources
// The model program: VPK vertices in, one shaded pixel out.
static const char* kModelVS =
    "precision highp float;\n"
    "attribute vec3 a_pos;\n"       // uint16, 0..65535 inside the draw's bbox
    "attribute vec4 a_nrm;\n"       // int8 normalised
    "attribute vec2 a_uv;\n"
    "uniform mat4 u_mvp;\n"
    "uniform vec3 u_posmin;\n"
    "uniform vec3 u_posscale;\n"
    "varying vec3 v_n;\n"
    "varying vec2 v_uv;\n"
    "varying vec3 v_wp;\n"
    "void main(){\n"
    "  vec3 p = u_posmin + (a_pos / 65535.0) * u_posscale;\n"
    "  v_wp = p;\n"
    "  v_n = a_nrm.xyz;\n"
    "  v_uv = a_uv;\n"
    "  gl_Position = u_mvp * vec4(p, 1.0);\n"
    "}\n";

static const char* kModelFS =
    "precision mediump float;\n"
    "varying vec3 v_n;\n"
    "varying vec2 v_uv;\n"
    "varying vec3 v_wp;\n"
    "uniform sampler2D u_tex;\n"
    "uniform float u_has_tex;\n"
    "uniform vec4 u_base;\n"
    "uniform float u_cutoff;\n"
    "uniform float u_foliage;\n"
    "uniform float u_glass;\n"
    "uniform vec3 u_emissive;\n"
    "uniform vec3 u_eye;\n"
    "uniform vec3 u_sun;\n"
    "uniform vec3 u_sun_col;\n"
    "uniform vec3 u_sky_col;\n"
    "uniform vec3 u_ground_col;\n"
    "uniform vec3 u_fog_col;\n"
    "uniform float u_exposure;\n"
    "uniform float u_fog_start;\n"
    "uniform float u_fog_density;\n"
    // ---- the same two-octave value noise as g_noise() in tools/game_sim.cpp
    "float g_hash(vec2 p){\n"
    "  p = fract(p * vec2(123.34, 456.21));\n"
    "  p += dot(p, p + 34.56);\n"
    "  return fract(p.x * p.y);\n"
    "}\n"
    "float g_noise(vec2 p){\n"
    "  vec2 i = floor(p);\n"
    "  vec2 f = p - i;\n"
    "  f = f * f * (3.0 - 2.0 * f);\n"
    "  float a = g_hash(i);\n"
    "  float b = g_hash(i + vec2(1.0, 0.0));\n"
    "  float c = g_hash(i + vec2(0.0, 1.0));\n"
    "  float d = g_hash(i + vec2(1.0, 1.0));\n"
    "  float ab = a + (b - a) * f.x;\n"
    "  float cd = c + (d - c) * f.x;\n"
    "  return ab + (cd - ab) * f.y;\n"
    "}\n"
    "float game_tonemap(float x){\n"
    "  float t = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);\n"
    "  return pow(clamp(t, 0.0, 1.0), 1.0 / 2.2);\n"
    "}\n"
    "void main(){\n"
    "  vec4 texel = vec4(1.0);\n"
    "  if (u_has_tex > 0.5) {\n"
    "    texel = texture2D(u_tex, v_uv);\n"
    "    if (u_cutoff > 0.0 && texel.a < u_cutoff) discard;\n"
    "  }\n"
    "  vec3 alb = texel.rgb * u_base.rgb;\n"
    "  float dist = length(v_wp - u_eye);\n"
    // ground detail: patchiness, grain and mown stripes, only on up-facing surfaces and
    // only up close (it would shimmer at the horizon otherwise)
    "  vec3 n = normalize(v_n);\n"
    "  float ny = abs(n.y);\n"
    "  if (ny > 0.75) {\n"
    "    float fade = clamp(1.0 - (dist - 8.0) * 0.045, 0.0, 1.0);\n"
    "    if (fade > 0.002) {\n"
    "      float patch = g_noise(v_wp.xz * 0.21);\n"
    "      float grain = g_noise(v_wp.xz * 2.3 + vec2(3.0, 0.0));\n"
    "      float fine  = g_noise(v_wp.xz * 11.0 + vec2(5.1, -3.7));\n"
    "      float m = 0.80 + 0.22 * patch + 0.20 * grain + 0.10 * fine;\n"
    "      m *= 0.965 + 0.07 * (0.5 + 0.5 * sin((v_wp.x * 0.62 + v_wp.z * 0.78) * 1.35));\n"
    "      alb *= 1.0 + (m - 1.0) * fade * (ny - 0.75) * 4.0;\n"
    "    }\n"
    "  }\n"
    "  if (u_foliage > 0.5) {\n"
    "    float lum = dot(alb, vec3(0.30, 0.59, 0.11));\n"
    "    alb = (lum * 0.55 + alb * 0.45) * 0.82;\n"
    "  } else if (alb.g > alb.r * 1.25 && alb.g > alb.b * 1.25) {\n"
    "    alb *= vec3(1.14, 0.86, 1.02);\n"     // lawn: deeper olive, like the stills
    "  }\n"
    "  if (u_glass > 0.5) {\n"
    // glazing on GLES2: a cool tint at 35 %, so rooms stay dark behind it
    "    float sh = 0.55 + 0.45 * max(n.y, 0.0);\n"
    "    vec3 tint = vec3(0.020, 0.030, 0.036) * sh * 8.0;\n"
    "    gl_FragColor = vec4(game_tonemap(tint.r * u_exposure),\n"
    "                        game_tonemap(tint.g * u_exposure),\n"
    "                        game_tonemap(tint.b * u_exposure), 0.35);\n"
    "    return;\n"
    "  }\n"
    "  float d = max(dot(n, u_sun), 0.0);\n"
    "  d = d * d * (3.0 - 2.0 * d) * 0.35 + d * 0.65;\n"
    "  float hemi = 0.5 + 0.5 * n.y;\n"
    "  vec3 amb = u_ground_col + (u_sky_col - u_ground_col) * hemi;\n"
    "  vec3 lin = alb * alb;\n"
    "  vec3 c = lin * (amb + u_sun_col * d) + u_emissive;\n"
    // grazing-angle sky sheen: a lawn seen at 80 degrees is mostly sky, and without this
    // every distant surface goes flat and muddy
    "  vec3 V = normalize(u_eye - v_wp);\n"
    "  float fres = pow(1.0 - clamp(dot(n, V), 0.0, 1.0), 3.0);\n"
    "  c += u_sky_col * fres * 0.055;\n"
    "  vec3 out_c = vec3(game_tonemap(c.r * u_exposure), game_tonemap(c.g * u_exposure),\n"
    "                    game_tonemap(c.b * u_exposure));\n"
    "  float fog = 1.0 - exp(-max(dist - u_fog_start, 0.0) * u_fog_density);\n"
    "  out_c = mix(out_c, vec3(game_tonemap(u_fog_col.r * u_exposure),\n"
    "                          game_tonemap(u_fog_col.g * u_exposure),\n"
    "                          game_tonemap(u_fog_col.b * u_exposure)), fog);\n"
    "  gl_FragColor = vec4(out_c, 1.0);\n"
    "}\n";

// Sky: one full-screen quad, the ray direction rebuilt from the camera basis. Clouds,
// sun disc and horizon haze all live here, in linear light, then through the same ACES fit.
static const char* kSkyVS =
    "attribute vec2 a_p;\n"
    "varying vec2 v_p;\n"
    "void main(){ v_p = a_p; gl_Position = vec4(a_p, 0.999, 1.0); }\n";

static const char* kSkyFS =
    "precision mediump float;\n"
    "varying vec2 v_p;\n"
    "uniform vec3 u_fwd, u_right, u_up;\n"
    "uniform float u_tan, u_aspect, u_exposure;\n"
    "uniform vec3 u_sun, u_sun_col;\n"
    "uniform vec3 u_zen, u_hor;\n"
    "float g_hash(vec2 p){\n"
    "  p = fract(p * vec2(123.34, 456.21));\n"
    "  p += dot(p, p + 34.56);\n"
    "  return fract(p.x * p.y);\n"
    "}\n"
    "float g_noise(vec2 p){\n"
    "  vec2 i = floor(p);\n"
    "  vec2 f = p - i;\n"
    "  f = f * f * (3.0 - 2.0 * f);\n"
    "  float a = g_hash(i), b = g_hash(i + vec2(1.0, 0.0));\n"
    "  float c = g_hash(i + vec2(0.0, 1.0)), d = g_hash(i + vec2(1.0, 1.0));\n"
    "  float ab = a + (b - a) * f.x, cd = c + (d - c) * f.x;\n"
    "  return ab + (cd - ab) * f.y;\n"
    "}\n"
    "float game_tonemap(float x){\n"
    "  float t = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);\n"
    "  return pow(clamp(t, 0.0, 1.0), 1.0 / 2.2);\n"
    "}\n"
    "void main(){\n"
    "  vec3 d = normalize(u_fwd + u_right * (v_p.x * u_tan * u_aspect)\n"
    "                           + u_up * (v_p.y * u_tan));\n"
    "  float y = d.y;\n"
    "  float t = y > 0.0 ? 1.0 - exp(-3.1 * y) : 0.0;\n"
    "  vec3 c = u_hor + (u_zen - u_hor) * t;\n"
    "  float cs = dot(d, u_sun);\n"
    "  if (cs > 0.0) {\n"
    "    float glow = pow(cs, 24.0) * 0.24 + pow(cs, 4.0) * 0.05;\n"
    "    float disc = cs > 0.9985 ? 1.0 : pow(cs, 900.0);\n"
    "    c += u_sun_col * glow + vec3(30.0) * disc;\n"
    "  }\n"
    "  if (y > 0.03) {\n"
    "    vec2 q = d.xz / (y + 0.10) * 7.0;\n"
    "    float f = 0.62 * g_noise(q) + 0.26 * g_noise(q * 2.1 + vec2(11.0, 0.0))\n"
    "            + 0.12 * g_noise(q * 4.3 + vec2(0.0, -7.0));\n"
    "    float cov = clamp((f - 0.56) * 4.0, 0.0, 1.0);\n"
    "    cov = cov * cov * (3.0 - 2.0 * cov) * clamp(y * 4.0, 0.0, 1.0);\n"
    "    float lit = 0.55 + 0.45 * clamp(cs * 1.6, 0.0, 1.0);\n"
    "    c = mix(c, vec3(0.105, 0.115, 0.132) * lit, cov * 0.85);\n"
    "  }\n"
    "  if (y < 0.0) c = mix(c, vec3(0.10), clamp(-y * 6.0, 0.0, 1.0));\n"
    "  gl_FragColor = vec4(vec3(game_tonemap(c.r * u_exposure), game_tonemap(c.g * u_exposure),\n"
    "                           game_tonemap(c.b * u_exposure)), 1.0);\n"
    "}\n";


// Ground skirt: one giant quad a little under the level's lawn, so the 87 m garden does not
// simply stop in mid-air. Same noise, same sun, same fog, so it blends into the haze.
static const char* kGroundVS =
    "attribute vec2 a_xz;\n"
    "uniform mat4 u_mvp;\n"
    "uniform float u_y;\n"
    "uniform vec3 u_eye;\n"
    "varying vec3 v_wp;\n"
    // the quad is a unit-sized ring around the eye, so 420 m of floor always exists in every
    // direction and the player can never walk to the end of it
    "void main(){\n"
    "  v_wp = vec3(a_xz.x + u_eye.x, u_y, a_xz.y + u_eye.z);\n"
    "  gl_Position = u_mvp * vec4(v_wp, 1.0);\n"
    "}\n";

static const char* kGroundFS =
    "precision mediump float;\n"
    "varying vec3 v_wp;\n"
    "uniform vec3 u_eye, u_sun, u_sun_col, u_sky_col, u_ground_col, u_fog_col, u_albedo;\n"
    "uniform float u_exposure, u_fog_start, u_fog_density;\n"
    "float g_hash(vec2 p){\n"
    "  p = fract(p * vec2(123.34, 456.21));\n"
    "  p += dot(p, p + 34.56);\n"
    "  return fract(p.x * p.y);\n"
    "}\n"
    "float g_noise(vec2 p){\n"
    "  vec2 i = floor(p); vec2 f = p - i; f = f * f * (3.0 - 2.0 * f);\n"
    "  float a = g_hash(i), b = g_hash(i + vec2(1.0, 0.0));\n"
    "  float c = g_hash(i + vec2(0.0, 1.0)), d = g_hash(i + vec2(1.0, 1.0));\n"
    "  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);\n"
    "}\n"
    "float game_tonemap(float x){\n"
    "  float t = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);\n"
    "  return pow(clamp(t, 0.0, 1.0), 1.0 / 2.2);\n"
    "}\n"
    "void main(){\n"
    "  float dist = length(v_wp - u_eye);\n"
    "  float patch = g_noise(v_wp.xz * 0.05);\n"
    "  vec3 alb = u_albedo * (0.85 + 0.30 * patch);\n"
    "  float d = max(u_sun.y, 0.0);\n"
    "  vec3 amb = u_sky_col;\n"
    "  vec3 c = alb * alb * (amb + u_sun_col * d);\n"
    "  vec3 out_c = vec3(game_tonemap(c.r * u_exposure), game_tonemap(c.g * u_exposure),\n"
    "                    game_tonemap(c.b * u_exposure));\n"
    "  float fog = 1.0 - exp(-max(dist - u_fog_start, 0.0) * u_fog_density);\n"
    "  out_c = mix(out_c, vec3(game_tonemap(u_fog_col.r * u_exposure),\n"
    "                          game_tonemap(u_fog_col.g * u_exposure),\n"
    "                          game_tonemap(u_fog_col.b * u_exposure)), fog);\n"
    "  gl_FragColor = vec4(out_c, 1.0);\n"
    "}\n";

// Objectives: additive billboards. A soft core plus a faint column so an orb is visible
// over the hedge line instead of being a pixel you have to hunt for.
static const char* kOrbVS =
    "attribute vec4 a_clip;\n"      // pre-projected: a billboard is 4 vertices of maths
    "attribute vec2 a_c;\n"
    "varying vec2 v_c;\n"
    "void main(){ v_c = a_c; gl_Position = a_clip; }\n";

static const char* kOrbFS =
    "precision mediump float;\n"
    "varying vec2 v_c;\n"
    "uniform float u_alpha;\n"
    "uniform float u_pulse;\n"
    "void main(){\n"
    "  float r2 = dot(v_c, v_c);\n"
    "  if (r2 > 1.0) discard;\n"
    "  float a = (1.0 - r2);\n"
    "  a = a * a * u_alpha * u_pulse;\n"
    "  gl_FragColor = vec4(vec3(1.00, 0.80, 0.34) * a, a);\n"
    "}\n";

// ------------------------------------------------------------------ GL state
struct Prog {
    GLuint id = 0;
    GLint mvp = -1, posmin = -1, posscl = -1, tex = -1, has_tex = -1, base = -1, cutoff = -1;
    GLint foliage = -1, glass = -1, emissive = -1, eye = -1, sun = -1, sun_col = -1;
    GLint sky_col = -1, ground_col = -1, fog_col = -1, exposure = -1, fog_start = -1,
          fog_density = -1;
};

static struct {
    VModel model;
    Game game;
    Level level;
    Prog model_p, sky_p, orb_p, ground_p;
    GLuint vbo = 0, ibo = 0, sky_vbo = 0, orb_vbo = 0, ground_vbo = 0;
    GLint g_mvp = -1, g_y = -1, g_eye = -1, g_sun = -1, g_sun_col = -1, g_sky_col = -1,
          g_ground_col = -1, g_fog_col = -1, g_exposure = -1, g_fog_start = -1,
          g_fog_density = -1, g_albedo = -1;
    std::vector<GLuint> tex;
    std::vector<uint8_t> tex_ready;
    int w = 1, h = 1;
    float aspect = 1.0f;
    bool ready = false;
    std::string status = "loading";
    // sky uniforms
    GLint s_fwd = -1, s_right = -1, s_up = -1, s_tan = -1, s_aspect = -1, s_exposure = -1,
          s_sun = -1, s_sun_col = -1, s_zen = -1, s_hor = -1;
    // orb uniforms
    GLint o_alpha = -1, o_pulse = -1;
    float orb_pulse = 1.0f;
    double time_s = 0.0;
} G;

static GLuint compile(GLenum type, const char* src, std::string* err) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[1024];
        glGetShaderInfoLog(s, sizeof log, nullptr, log);
        if (err) *err = log;
        LOGE("shader: %s", log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

static GLuint link(const char* vs, const char* fs, const char* const* attribs, int n_attribs,
                   std::string* err) {
    GLuint v = compile(GL_VERTEX_SHADER, vs, err);
    if (!v) return 0;
    GLuint f = compile(GL_FRAGMENT_SHADER, fs, err);
    if (!f) {
        glDeleteShader(v);
        return 0;
    }
    GLuint p = glCreateProgram();
    glAttachShader(p, v);
    glAttachShader(p, f);
    // explicit slots: the renderer hard-codes 0/1/2, and GL does not guarantee an order
    for (int i = 0; i < n_attribs; ++i) glBindAttribLocation(p, (GLuint)i, attribs[i]);
    glLinkProgram(p);
    GLint ok = 0;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    glDeleteShader(v);
    glDeleteShader(f);
    if (!ok) {
        char log[1024];
        glGetProgramInfoLog(p, sizeof log, nullptr, log);
        if (err) *err = log;
        LOGE("link: %s", log);
        glDeleteProgram(p);
        return 0;
    }
    return p;
}

static std::vector<uint8_t> read_asset(AAssetManager* mgr, const char* name, bool* ok) {
    std::vector<uint8_t> out;
    AAsset* a = AAssetManager_open(mgr, name, AASSET_MODE_BUFFER);
    if (!a) {
        LOGE("asset %s missing", name);
        if (ok) *ok = false;
        return out;
    }
    off_t n = AAsset_getLength(a);
    out.resize((size_t)n);
    int got = AAsset_read(a, out.data(), (size_t)n);
    AAsset_close(a);
    if (got != (int)n) {
        if (ok) *ok = false;
        return out;
    }
    if (ok) *ok = true;
    return out;
}

static void upload_texture(size_t i) {
    if (i >= G.tex.size() || G.tex_ready[i]) return;
    G.tex_ready[i] = 1;
    int w = 0, h = 0, n = 0;
    const uint8_t* bytes = G.model.texture_bytes((uint16_t)i);
    unsigned char* px = stbi_load_from_memory(bytes, (int)G.model.texture_length((uint16_t)i), &w,
                                              &h, &n, 4);
    if (!px) {
        LOGE("texture %zu failed: %s", i, stbi_failure_reason());
        G.tex[i] = 0;
        return;
    }
    glGenTextures(1, &G.tex[i]);
    glBindTexture(GL_TEXTURE_2D, G.tex[i]);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, px);
    const bool pot = (w & (w - 1)) == 0 && (h & (h - 1)) == 0;
    if (pot) {
        glGenerateMipmap(GL_TEXTURE_2D);   // GLES2 only allows this for power-of-two sizes
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
    } else {
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    }
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
    stbi_image_free(px);
}

static void set_model_uniforms(const VDraw& d, const Mat4& mvp, const float eye[3]) {
    const GameSun& s = game_sun();
    const Prog& p = G.model_p;
    glUniformMatrix4fv(p.mvp, 1, GL_FALSE, mvp.m);
    glUniform3fv(p.posmin, 1, d.pos_min);
    glUniform3fv(p.posscl, 1, d.pos_scale);
    glUniform4fv(p.base, 1, d.base_color);
    const bool glass = (d.flags & 4u) != 0;
    const bool cutout = d.alpha_cutoff > 0.0f;
    glUniform1f(p.has_tex, d.tex == VPK_NO_TEXTURE ? 0.0f : 1.0f);
    glUniform1f(p.cutoff, d.alpha_cutoff);
    glUniform1f(p.foliage, (cutout && (d.flags & 2u)) ? 1.0f : 0.0f);
    glUniform1f(p.glass, glass ? 1.0f : 0.0f);
    glUniform3fv(p.emissive, 1, d.emissive);
    glUniform3fv(p.eye, 1, eye);
    glUniform3fv(p.sun, 1, s.dir);
    glUniform3fv(p.sun_col, 1, s.sun_col);
    glUniform3fv(p.sky_col, 1, s.sky_col);
    glUniform3fv(p.ground_col, 1, s.ground_col);
    glUniform3fv(p.fog_col, 1, s.fog_col);
    glUniform1f(p.exposure, s.exposure);
    glUniform1f(p.fog_start, s.fog_start);
    glUniform1f(p.fog_density, s.fog_density);
}

static void init_gl() {
    std::string err;
    static const char* kModelAttribs[] = {"a_pos", "a_nrm", "a_uv"};
    G.model_p.id = link(kModelVS, kModelFS, kModelAttribs, 3, &err);
    if (!G.model_p.id) {
        G.status = "model shader: " + err;
        return;
    }
    const Prog* p = &G.model_p;
    Prog* m = &G.model_p;
    m->mvp = glGetUniformLocation(p->id, "u_mvp");
    m->posmin = glGetUniformLocation(p->id, "u_posmin");
    m->posscl = glGetUniformLocation(p->id, "u_posscale");
    m->tex = glGetUniformLocation(p->id, "u_tex");
    m->has_tex = glGetUniformLocation(p->id, "u_has_tex");
    m->base = glGetUniformLocation(p->id, "u_base");
    m->cutoff = glGetUniformLocation(p->id, "u_cutoff");
    m->foliage = glGetUniformLocation(p->id, "u_foliage");
    m->glass = glGetUniformLocation(p->id, "u_glass");
    m->emissive = glGetUniformLocation(p->id, "u_emissive");
    m->eye = glGetUniformLocation(p->id, "u_eye");
    m->sun = glGetUniformLocation(p->id, "u_sun");
    m->sun_col = glGetUniformLocation(p->id, "u_sun_col");
    m->sky_col = glGetUniformLocation(p->id, "u_sky_col");
    m->ground_col = glGetUniformLocation(p->id, "u_ground_col");
    m->fog_col = glGetUniformLocation(p->id, "u_fog_col");
    m->exposure = glGetUniformLocation(p->id, "u_exposure");
    m->fog_start = glGetUniformLocation(p->id, "u_fog_start");
    m->fog_density = glGetUniformLocation(p->id, "u_fog_density");

    static const char* kSkyAttribs[] = {"a_p"};
    G.sky_p.id = link(kSkyVS, kSkyFS, kSkyAttribs, 1, &err);
    G.sky_p.mvp = -1;
    G.s_fwd = glGetUniformLocation(G.sky_p.id, "u_fwd");
    G.s_right = glGetUniformLocation(G.sky_p.id, "u_right");
    G.s_up = glGetUniformLocation(G.sky_p.id, "u_up");
    G.s_tan = glGetUniformLocation(G.sky_p.id, "u_tan");
    G.s_aspect = glGetUniformLocation(G.sky_p.id, "u_aspect");
    G.s_exposure = glGetUniformLocation(G.sky_p.id, "u_exposure");
    G.s_sun = glGetUniformLocation(G.sky_p.id, "u_sun");
    G.s_sun_col = glGetUniformLocation(G.sky_p.id, "u_sun_col");
    G.s_zen = glGetUniformLocation(G.sky_p.id, "u_zen");
    G.s_hor = glGetUniformLocation(G.sky_p.id, "u_hor");

    static const char* kOrbAttribs[] = {"a_clip", "a_c"};
    G.orb_p.id = link(kOrbVS, kOrbFS, kOrbAttribs, 2, &err);

    static const char* kGroundAttribs[] = {"a_xz"};
    G.ground_p.id = link(kGroundVS, kGroundFS, kGroundAttribs, 1, &err);
    G.g_mvp = glGetUniformLocation(G.ground_p.id, "u_mvp");
    G.g_y = glGetUniformLocation(G.ground_p.id, "u_y");
    G.g_eye = glGetUniformLocation(G.ground_p.id, "u_eye");
    G.g_sun = glGetUniformLocation(G.ground_p.id, "u_sun");
    G.g_sun_col = glGetUniformLocation(G.ground_p.id, "u_sun_col");
    G.g_sky_col = glGetUniformLocation(G.ground_p.id, "u_sky_col");
    G.g_ground_col = glGetUniformLocation(G.ground_p.id, "u_ground_col");
    G.g_fog_col = glGetUniformLocation(G.ground_p.id, "u_fog_col");
    G.g_exposure = glGetUniformLocation(G.ground_p.id, "u_exposure");
    G.g_fog_start = glGetUniformLocation(G.ground_p.id, "u_fog_start");
    G.g_fog_density = glGetUniformLocation(G.ground_p.id, "u_fog_density");
    G.g_albedo = glGetUniformLocation(G.ground_p.id, "u_albedo");
    G.o_alpha = glGetUniformLocation(G.orb_p.id, "u_alpha");
    G.o_pulse = glGetUniformLocation(G.orb_p.id, "u_pulse");

    if (!G.sky_p.id || !G.orb_p.id || !G.ground_p.id) {
        G.status = "shader link failed: " + err;
        return;
    }

    // one static VBO for all vertices, one for all indices
    glGenBuffers(1, &G.vbo);
    glBindBuffer(GL_ARRAY_BUFFER, G.vbo);
    glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)((size_t)G.model.h.n_verts * VPK_VERTEX_STRIDE),
                 G.model.vertex_base(), GL_STATIC_DRAW);
    glGenBuffers(1, &G.ibo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, G.ibo);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, (GLsizeiptr)((size_t)G.model.h.n_indices * 2),
                 G.model.index_base(), GL_STATIC_DRAW);

    G.tex.assign(G.model.textures.size(), 0);
    G.tex_ready.assign(G.model.textures.size(), 0);

    // full-screen quad for the sky, and the dynamic buffer for the orbs
    static const float quad[] = {-1, -1, 1, -1, -1, 1, 1, 1};
    glGenBuffers(1, &G.sky_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, G.sky_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof quad, quad, GL_STATIC_DRAW);
    // the skirt is a unit quad around the eye, scaled in the shader by moving with the camera
    static const float gquad[] = {-420, -420, 420, -420, -420, 420, 420, 420};
    glGenBuffers(1, &G.ground_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, G.ground_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof gquad, gquad, GL_STATIC_DRAW);
    glGenBuffers(1, &G.orb_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, G.orb_vbo);
    // 8 orbs x 2 billboards x 6 vertices x 6 floats (clip xyzw + corner xy)
    glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)(8 * 2 * 6 * 6 * sizeof(float)), nullptr,
                 GL_DYNAMIC_DRAW);

    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glDisable(GL_CULL_FACE);   // the packer marks two-sided materials; cheaper to skip culling
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    G.ready = true;
    G.status = "ready";
    LOGI("GL ready: %u draws, %u textures", G.model.h.n_draws, G.model.h.n_textures);
}

// ------------------------------------------------------------------ frame
static void build_mvp(const float eye[3], const float yaw, const float pitch, float roll,
                      Mat4* out) {
    const float cp = cosf(pitch), sp = sinf(pitch);
    float fwd[3] = {sinf(yaw) * cp, sp, cosf(yaw) * cp};
    float up[3] = {0, 1, 0};
    // a touch of roll while walking: one line, and it stops the walk feeling like a dolly
    if (roll != 0.0f) {
        const float c = cosf(roll), s = sinf(roll);
        float r[3] = {fwd[2], 0.0f, -fwd[0]};
        float rl = sqrtf(r[0] * r[0] + r[2] * r[2]);
        if (rl > 1e-4f) {
            r[0] /= rl;
            r[2] /= rl;
            for (int i = 0; i < 3; ++i) up[i] = up[i] * c + (r[i] * s);
        }
    }
    float ctr[3] = {eye[0] + fwd[0], eye[1] + fwd[1], eye[2] + fwd[2]};
    Mat4 v = mat4_lookat(eye, ctr, up);
    Mat4 p = mat4_perspective(62.0f * 3.14159265f / 180.0f, G.aspect, 0.12f, 420.0f);
    *out = mat4_mul(p, v);
}

static void draw_sky(const float eye[3], const float yaw, const float pitch) {
    const GameSun& s = game_sun();
    const float cp = cosf(pitch), sp = sinf(pitch);
    float fwd[3] = {sinf(yaw) * cp, sp, cosf(yaw) * cp};
    float right[3] = {cosf(yaw), 0.0f, -sinf(yaw)};
    float up[3] = {right[1] * fwd[2] - right[2] * fwd[1], right[2] * fwd[0] - right[0] * fwd[2],
                   right[0] * fwd[1] - right[1] * fwd[0]};
    (void)eye;
    glUseProgram(G.sky_p.id);
    glUniform3fv(G.s_fwd, 1, fwd);
    glUniform3fv(G.s_right, 1, right);
    glUniform3fv(G.s_up, 1, up);
    glUniform1f(G.s_tan, tanf(0.5f * 62.0f * 3.14159265f / 180.0f));
    glUniform1f(G.s_aspect, G.aspect);
    glUniform1f(G.s_exposure, s.exposure);
    glUniform3fv(G.s_sun, 1, s.dir);
    glUniform3fv(G.s_sun_col, 1, s.sun_col);
    const float zen[3] = {0.030f, 0.058f, 0.125f};
    const float hor[3] = {0.090f, 0.105f, 0.120f};
    glUniform3fv(G.s_zen, 1, zen);
    glUniform3fv(G.s_hor, 1, hor);
    glBindBuffer(GL_ARRAY_BUFFER, G.sky_vbo);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}

static void draw_orbs(const float eye[3], const float yaw, const float pitch) {
    const float cp = cosf(pitch), sp = sinf(pitch);
    const float fwd[3] = {sinf(yaw) * cp, sp, cosf(yaw) * cp};
    const float right[3] = {cosf(yaw), 0.0f, -sinf(yaw)};
    const float up[3] = {right[1] * fwd[2] - right[2] * fwd[1],
                         right[2] * fwd[0] - right[0] * fwd[2],
                         right[0] * fwd[1] - right[1] * fwd[0]};
    const float ctr[3] = {eye[0] + fwd[0], eye[1] + fwd[1], eye[2] + fwd[2]};
    const float wup[3] = {0, 1, 0};
    const Mat4 v = mat4_lookat(eye, ctr, wup);
    const Mat4 pm = mat4_perspective(62.0f * 3.14159265f / 180.0f, G.aspect, 0.12f, 420.0f);
    const Mat4 vp = mat4_mul(pm, v);

    // 4 vertices per billboard: (clip x,y,z,w) + (corner x,y) = 6 floats
    float buf[8 * 2 * 6 * 6] = {0};   // 8 orbs x 2 quads x 6 verts x 6 floats
    static_assert(sizeof(buf) / sizeof(float) >= 8 * 2 * 6 * 6, "orb buffer too small");
    int vi = 0;
    const int order[6] = {0, 1, 2, 2, 1, 3};
    // 8 orbs x 2 quads x 6 verts x 6 floats fits the buffer exactly; more objectives than
    // that and the list is simply drawn in batches of eight
    size_t drawn = 0;
    for (size_t i = 0; i < G.game.lv.objs.size() && drawn < 8; ++i) {
        if (G.game.taken[i]) continue;
        ++drawn;
        const LevelObj& o = G.game.lv.objs[i];
        for (int layer = 0; layer < 2; ++layer) {
            const float halfw = layer == 0 ? 0.42f : 0.9f;
            const float halfh = layer == 0 ? 0.42f : 1.9f;
            const float cy = layer == 0 ? o.y : o.y + 1.4f;
            float px[4], py[4], pz[4], cw[4][4];
            for (int k = 0; k < 4; ++k) {
                const float ax = (k & 1) ? 1.0f : -1.0f;
                const float ay = (k >> 1) ? 1.0f : -1.0f;
                px[k] = o.x + right[0] * ax * halfw + up[0] * ay * halfh;
                py[k] = cy + right[1] * ax * halfw + up[1] * ay * halfh;
                pz[k] = o.z + right[2] * ax * halfw + up[2] * ay * halfh;
                for (int j = 0; j < 4; ++j)
                    cw[k][j] = px[k] * vp.m[j] + py[k] * vp.m[4 + j] + pz[k] * vp.m[8 + j] +
                               vp.m[12 + j];
            }
            for (int k = 0; k < 6; ++k) {
                const int q = order[k];
                for (int j = 0; j < 4; ++j) buf[vi * 6 + j] = cw[q][j];
                buf[vi * 6 + 4] = (q & 1) ? 1.0f : -1.0f;
                buf[vi * 6 + 5] = (q >> 1) ? 1.0f : -1.0f;
                ++vi;
            }
        }
    }
    if (!vi) return;

    glUseProgram(G.orb_p.id);
    glUniform1f(G.o_pulse, 0.72f + 0.28f * sinf((float)G.time_s * 3.4f));
    glBindBuffer(GL_ARRAY_BUFFER, G.orb_vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0, (GLsizeiptr)((size_t)vi * 6 * sizeof(float)), buf);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(4 * sizeof(float)));
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_ONE);
    glDepthMask(GL_FALSE);
    // halos first, then the faint columns, so a column never washes out the orb inside it
    int first = 0;
    for (size_t i = 0; i < G.game.lv.objs.size() && first / 12 < 8; ++i) {
        if (G.game.taken[i]) continue;
        glUniform1f(G.o_alpha, 0.80f);
        glDrawArrays(GL_TRIANGLES, first, 6);
        glUniform1f(G.o_alpha, 0.14f);
        glDrawArrays(GL_TRIANGLES, first + 6, 6);
        first += 12;
    }
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
}

static void draw_skirt(const Mat4& mvp, const float eye[3]) {
    const GameSun& s = game_sun();
    glUseProgram(G.ground_p.id);
    glUniformMatrix4fv(G.g_mvp, 1, GL_FALSE, mvp.m);
    glUniform1f(G.g_y, -0.55f);
    glUniform3fv(G.g_eye, 1, eye);
    glUniform3fv(G.g_sun, 1, s.dir);
    glUniform3fv(G.g_sun_col, 1, s.sun_col);
    glUniform3fv(G.g_sky_col, 1, s.sky_col);
    glUniform3fv(G.g_ground_col, 1, s.ground_col);
    glUniform3fv(G.g_fog_col, 1, s.fog_col);
    glUniform1f(G.g_exposure, s.exposure);
    glUniform1f(G.g_fog_start, s.fog_start);
    glUniform1f(G.g_fog_density, s.fog_density);
    const float albedo[3] = {0.085f, 0.135f, 0.055f};   // meadow beyond the garden
    glUniform3fv(G.g_albedo, 1, albedo);
    glBindBuffer(GL_ARRAY_BUFFER, G.ground_vbo);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
}

static void draw_model(const Mat4& mvp, const float eye[3]) {
    glUseProgram(G.model_p.id);
    glBindBuffer(GL_ARRAY_BUFFER, G.vbo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, G.ibo);
    glEnableVertexAttribArray(0);
    glEnableVertexAttribArray(1);
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(0, 3, GL_UNSIGNED_SHORT, GL_FALSE, VPK_VERTEX_STRIDE, (void*)0);
    glVertexAttribPointer(1, 4, GL_BYTE, GL_TRUE, VPK_VERTEX_STRIDE, (void*)8);
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, VPK_VERTEX_STRIDE, (void*)12);
    glActiveTexture(GL_TEXTURE0);
    glUniform1i(G.model_p.tex, 0);

    // pass 1+2: opaque and cutout, in the packer's order; pass 3: glass, blended, last
    for (int pass = 0; pass < 2; ++pass) {
        if (pass == 1) {
            glEnable(GL_BLEND);
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
            glDepthMask(GL_FALSE);
        }
        for (uint32_t i = 0; i < G.model.h.n_draws; ++i) {
            const VDraw& d = G.model.draws[i];
            const bool glass = (d.flags & 4u) != 0;
            if ((pass == 0 && glass) || (pass == 1 && !glass)) continue;
            set_model_uniforms(d, mvp, eye);
            if (d.tex != VPK_NO_TEXTURE) {
                upload_texture(d.tex);
                glBindTexture(GL_TEXTURE_2D, G.tex[d.tex]);
            }
            glDrawElements(GL_TRIANGLES, (GLsizei)d.index_count, GL_UNSIGNED_SHORT,
                           (void*)((size_t)d.index_offset * 2));
        }
        if (pass == 1) {
            glDepthMask(GL_TRUE);
            glDisable(GL_BLEND);
        }
    }
}

// ------------------------------------------------------------------ JNI
extern "C" {

JNIEXPORT jboolean JNICALL
Java_ai_arena_villagame_GameRenderer_nativeInit(JNIEnv* env, jobject, jobject asset_mgr) {
    AAssetManager* mgr = AAssetManager_fromJava(env, asset_mgr);
    if (!mgr) {
        G.status = "no asset manager";
        return JNI_FALSE;
    }
    bool ok = false;
    std::vector<uint8_t> vpk = read_asset(mgr, "model.vpk", &ok);
    if (!ok) {
        G.status = "model.vpk missing from assets";
        return JNI_FALSE;
    }
    std::string err;
    if (!G.model.load(std::move(vpk), &err)) {
        G.status = "model.vpk: " + err;
        return JNI_FALSE;
    }
    std::vector<uint8_t> lvl = read_asset(mgr, "level.bin", &ok);
    if (!ok) {
        G.status = "level.bin missing from assets";
        return JNI_FALSE;
    }
    if (!G.level.load(lvl, &err)) {
        G.status = "level.bin: " + err;
        return JNI_FALSE;
    }
    if (!G.game.bind(G.level, &err)) {
        G.status = "level: " + err;
        return JNI_FALSE;
    }
    init_gl();
    return G.ready ? JNI_TRUE : JNI_FALSE;
}

JNIEXPORT void JNICALL
Java_ai_arena_villagame_GameRenderer_nativeResize(JNIEnv*, jobject, jint w, jint h) {
    G.w = w > 0 ? w : 1;
    G.h = h > 0 ? h : 1;
    G.aspect = (float)G.w / (float)G.h;
    glViewport(0, 0, G.w, G.h);
}

JNIEXPORT void JNICALL
Java_ai_arena_villagame_GameRenderer_nativeFrame(JNIEnv*, jobject, jfloat dt, jfloat jx,
                                                 jfloat jy, jfloat dyaw, jfloat dpitch) {
    if (!G.ready) return;
    G.time_s += dt;
    // stick: +y is forward in the touch view, the player wants -z locally
    G.game.update(dt, -jy, jx, dyaw, dpitch);
    float eye[3];
    G.game.eye_pos(eye);
    const float roll = sinf(G.game.bob * 0.5f) * 0.006f * G.game.bob_amp;
    Mat4 mvp;
    build_mvp(eye, G.game.p.yaw, G.game.p.pitch, roll, &mvp);

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    draw_sky(eye, G.game.p.yaw, G.game.p.pitch);
    draw_skirt(mvp, eye);
    draw_model(mvp, eye);
    draw_orbs(eye, G.game.p.yaw, G.game.p.pitch);
}

JNIEXPORT jint JNICALL Java_ai_arena_villagame_GameRenderer_nativeOrbs(JNIEnv*, jobject) {
    return G.game.orbs;
}

JNIEXPORT jint JNICALL Java_ai_arena_villagame_GameRenderer_nativeTotal(JNIEnv*, jobject) {
    return G.game.total;
}

JNIEXPORT jfloat JNICALL Java_ai_arena_villagame_GameRenderer_nativeTime(JNIEnv*, jobject) {
    return G.game.time;
}

JNIEXPORT jint JNICALL Java_ai_arena_villagame_GameRenderer_nativeState(JNIEnv*, jobject) {
    return G.game.state;
}

JNIEXPORT jfloat JNICALL Java_ai_arena_villagame_GameRenderer_nativeBearing(JNIEnv*, jobject) {
    int idx = -1;
    float bearing = 0.0f;
    if (!G.game.nearest_orb(&idx, &bearing)) return 99.0f;   // 99 = nothing left
    return bearing;
}

JNIEXPORT void JNICALL Java_ai_arena_villagame_GameRenderer_nativeReset(JNIEnv*, jobject) {
    G.game.reset();
}

JNIEXPORT jstring JNICALL Java_ai_arena_villagame_GameRenderer_nativeStatus(JNIEnv* env,
                                                                           jobject) {
    return env->NewStringUTF(G.status.c_str());
}

}  // extern "C"
