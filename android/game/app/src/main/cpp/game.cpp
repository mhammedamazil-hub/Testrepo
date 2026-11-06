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
#include <cstdarg>
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
//
// GLSL ES 2.0. Two rules are enforced by tools/gles_shader_check.py, which CI runs before
// Gradle: every cross-stage symbol is declared with the XPREC token (so vertex and fragment
// stages can never disagree about precision - that error shipped a black screen once), and
// every attribute is bound explicitly.

// ---- shared GLSL, prepended to every fragment shader by compile()
//
// The scene shaders now write *display* colour: exposure, the ACES fit and the sRGB curve all
// happen here, in the pass that knows the light. That is what game_sim.cpp does, and it means
// the final image never depends on the post chain: if the off-screen targets or the composite
// ever fail on a device, skipping post costs bloom and god rays and nothing else. v4.0 put the
// tone curve in the composite, so any failure in that last full-screen pass turned the whole
// game black while the Java HUD kept drawing - exactly the screenshot that came back.
static const char* kCommonGlsl =
    "float aces_fit(float x){\n"
    "  float t = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14);\n"
    "  return clamp(t, 0.0, 1.0);\n"
    "}\n"
    "vec3 to_display(vec3 c){\n"
    "  c = max(c, vec3(0.0));\n"
    "  return pow(vec3(aces_fit(c.r), aces_fit(c.g), aces_fit(c.b)), vec3(1.0 / 2.2));\n"
    "}\n";

// ---- the model: VPK vertices in, display colour out
static const char* kModelVS =
    "#define XPREC_SYM\n"
    "attribute vec3 a_pos;\n"        // uint16 inside the draw's bbox
    "attribute vec4 a_nrm;\n"        // int8 normalised
    "attribute vec2 a_uv;\n"
    "attribute vec2 a_ao;\n"         // baked: x = ambient visibility, y = sun visibility
    "uniform mat4 u_mvp;\n"
    "uniform vec3 u_posmin;\n"
    "uniform vec3 u_posscale;\n"
    "uniform XPREC float u_time;\n"
    "uniform float u_wind;\n"
    "varying XPREC vec3 v_n;\n"
    "varying XPREC vec2 v_uv;\n"
    "varying XPREC vec3 v_wp;\n"
    "varying XPREC vec2 v_ao;\n"
    "void main(){\n"
    "  vec3 p = u_posmin + (a_pos / 65535.0) * u_posscale;\n"
    // wind: only foliage sways (the host harness does exactly this in the same way)
    "  if (u_wind > 0.0) {\n"
    "    float ph = p.x * 0.31 + p.z * 0.23;\n"
    "    float h = max(p.y, 0.0);\n"
    "    float amp = u_wind * (0.012 + 0.020 * h) * (0.7 + 0.3 * sin(u_time * 0.37 + ph * 0.2));\n"
    "    float sw = sin(u_time * 2.1 + ph) + 0.45 * sin(u_time * 3.7 + ph * 1.7);\n"
    "    p.x += sw * amp;\n"
    "    p.z += 0.6 * sin(u_time * 1.7 + ph * 1.3) * amp;\n"
    "  }\n"
    "  v_wp = p;\n"
    "  v_n = a_nrm.xyz;\n"
    "  v_uv = a_uv;\n"
    "  v_ao = a_ao;\n"
    "  gl_Position = u_mvp * vec4(p, 1.0);\n"
    "}\n";

static const char* kModelFS =
    "precision XPREC float;\n"
    "varying XPREC vec3 v_n;\n"
    "varying XPREC vec2 v_uv;\n"
    "varying XPREC vec3 v_wp;\n"
    "varying XPREC vec2 v_ao;\n"
    "uniform sampler2D u_tex;\n"
    "uniform float u_has_tex;\n"
    "uniform vec4 u_base;\n"
    "uniform float u_cutoff;\n"
    "uniform float u_foliage;\n"
    "uniform float u_glass;\n"
    "uniform float u_water;\n"
    "uniform vec3 u_emissive;\n"
    "uniform XPREC vec3 u_eye;\n"
    "uniform XPREC vec3 u_sun;\n"
    "uniform XPREC vec3 u_sun_col;\n"
    "uniform XPREC vec3 u_sky_col;\n"
    "uniform XPREC vec3 u_ground_col;\n"
    "uniform XPREC vec3 u_fog_col;\n"
    "uniform XPREC float u_exposure;\n"
    "uniform XPREC float u_fog_start;\n"
    "uniform XPREC float u_fog_density;\n"
    "uniform XPREC float u_time;\n"
    "float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 34.56);\n"
    "                   return fract(p.x * p.y); }\n"
    "float noise2(vec2 p){\n"
    "  vec2 i = floor(p); vec2 f = p - i; f = f * f * (3.0 - 2.0 * f);\n"
    "  float a = h21(i), b = h21(i + vec2(1.0, 0.0));\n"
    "  float c = h21(i + vec2(0.0, 1.0)), d = h21(i + vec2(1.0, 1.0));\n"
    "  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);\n"
    "}\n"
    // sky, shared by the skybox, glass reflections and water reflections. Must match
    // sky_colour() in tools/game_sim.cpp.
    "vec3 sky_at(vec3 d, vec3 sun, vec3 sun_col, vec3 zen, vec3 hor){\n"
    "  float y = d.y;\n"
    "  float t = y > 0.0 ? 1.0 - exp(-3.1 * y) : 0.0;\n"
    "  vec3 c = mix(hor, zen, t);\n"
    "  float cs = dot(d, sun);\n"
    "  if (cs > 0.0) {\n"
    "    float glow = pow(cs, 24.0) * 0.24 + pow(cs, 4.0) * 0.05;\n"
    "    float disc = cs > 0.9985 ? 1.0 : pow(cs, 900.0);\n"
    "    c += sun_col * glow + vec3(30.0) * disc;\n"
    "  }\n"
    "  if (y > 0.03) {\n"
    "    vec2 q = d.xz / (y + 0.10) * 7.0;\n"
    "    float f = 0.62 * noise2(q) + 0.26 * noise2(q * 2.1 + vec2(11.0, 0.0))\n"
    "            + 0.12 * noise2(q * 4.3 + vec2(0.0, -7.0));\n"
    "    float cov = clamp((f - 0.56) * 4.0, 0.0, 1.0);\n"
    "    cov = cov * cov * (3.0 - 2.0 * cov) * clamp(y * 4.0, 0.0, 1.0);\n"
    "    float lit = 0.55 + 0.45 * clamp(cs * 1.6, 0.0, 1.0);\n"
    "    c = mix(c, vec3(0.105, 0.115, 0.132) * lit, cov * 0.85);\n"
    "  }\n"
    "  if (y < 0.0) c = mix(c, vec3(0.10), clamp(-y * 6.0, 0.0, 1.0));\n"
    "  return c;\n"
    "}\n"
    "void main(){\n"
    "  vec4 texel = vec4(1.0);\n"
    "  if (u_has_tex > 0.5) {\n"
    "    texel = texture2D(u_tex, v_uv);\n"
    "    if (u_cutoff > 0.0 && texel.a < u_cutoff) discard;\n"
    "  }\n"
    "  vec3 alb = texel.rgb * u_base.rgb;\n"
    "  vec3 n = normalize(v_n);\n"
    "  float dist = length(v_wp - u_eye);\n"
    "  vec3 V = normalize(u_eye - v_wp);\n"
    "  float fres = pow(1.0 - clamp(dot(n, V), 0.0, 1.0), 3.0);\n"
    // baked occlusion, smoothed
    "  float ao = 0.26 + 0.74 * (v_ao.x * v_ao.x);\n"
    "  float sv = 0.10 + 0.90 * v_ao.y;\n"
    "  vec3 zen = vec3(0.105, 0.175, 0.335);\n"
    "  vec3 hor = vec3(0.330, 0.360, 0.390);\n"
    // ground detail: patches, grain and mown stripes on up-facing surfaces, near only
    "  float ny = abs(n.y);\n"
    "  if (ny > 0.75) {\n"
    "    float fade = clamp(1.0 - (dist - 8.0) * 0.045, 0.0, 1.0);\n"
    "    if (fade > 0.002) {\n"
    "      float patch = noise2(v_wp.xz * 0.21);\n"
    "      float grain = noise2(v_wp.xz * 2.3 + vec2(3.0, 0.0));\n"
    "      float fine  = noise2(v_wp.xz * 11.0 + vec2(5.1, -3.7));\n"
    "      float m = 0.80 + 0.22 * patch + 0.20 * grain + 0.10 * fine;\n"
    "      m *= 0.965 + 0.07 * (0.5 + 0.5 * sin((v_wp.x * 0.62 + v_wp.z * 0.78) * 1.35));\n"
    "      alb *= 1.0 + (m - 1.0) * fade * (ny - 0.75) * 4.0;\n"
    "    }\n"
    "  } else {\n"
    // walls: plaster/brick grain, world space, so a white facade is not a flat sheet
    "    float wf = clamp(1.0 - (dist - 5.0) * 0.075, 0.0, 1.0);\n"
    "    if (wf > 0.002 && u_foliage < 0.5) {\n"
    "      float g1 = noise2(v_wp.xy * 5.7 + v_wp.zz * 1.9);\n"
    "      float g2 = noise2(v_wp.zy * 17.0 + 4.3);\n"
    "      alb *= 1.0 + ((g1 - 0.5) * 0.10 + (g2 - 0.5) * 0.05) * wf;\n"
    "    }\n"
    "  }\n"
    "  if (u_foliage > 0.5) {\n"
    "    float lum = dot(alb, vec3(0.30, 0.59, 0.11));\n"
    "    alb = (lum * 0.55 + alb * 0.45) * 0.82;\n"
    "    sv *= 0.55;\n"                    // a leaf is a thin sheet, not a diffuse block
    "  } else if (alb.g > alb.r * 1.25 && alb.g > alb.b * 1.25) {\n"
    "    alb = pow(alb, vec3(0.55));\n"    // the lawn texture is authored nearly black
    "    alb *= vec3(1.10, 0.90, 1.02);\n"
    "  }\n"
    // White paint is not a perfect reflector: capping the albedo keeps a sunlit facade from
    // clipping to a blank 255 sheet while the lawn and the trees stay where they are.
    "  alb = min(alb, vec3(0.75));\n"
    "  float fog = 1.0 - exp(-max(dist - u_fog_start, 0.0) * u_fog_density);\n"
    "  vec3 fog_c = u_fog_col * u_exposure;\n"
    "  if (u_glass > 0.5) {\n"
    // A window from outside: a dim room behind a sheet of reflected sky.
    "    vec3 rd = reflect(-V, n);\n"
    "    float fren = 0.28 + 0.60 * pow(1.0 - clamp(dot(n, V), 0.0, 1.0), 4.0);\n"
    "    vec3 c = (vec3(0.020, 0.024, 0.028) + sky_at(rd, u_sun, u_sun_col, zen, hor) * fren * 0.55\n"
    "              + u_sky_col * 0.10) * u_exposure;\n"
    "    c = mix(c, fog_c, fog);\n"
    "    gl_FragColor = vec4(to_display(c), 1.0);\n"   // opaque: blending made it milky
    "    return;\n"
    "  }\n"
    "  if (u_water > 0.5) {\n"
    // Water: moving normals, a sky mirror, and a sun glint far brighter than the water.
    "    float t = u_time;\n"
    "    float s1 = sin(v_wp.x * 3.1 + t * 1.9) * cos(v_wp.z * 2.7 - t * 1.3);\n"
    "    float s2 = sin((v_wp.x + v_wp.z) * 7.3 - t * 2.6);\n"
    "    float s3 = cos(v_wp.z * 11.7 + v_wp.x * 5.1 + t * 3.4);\n"
    "    float fd = 1.0 / (1.0 + dist * 0.35);\n"
    "    vec3 wn = normalize(vec3((s1 * 0.5 + s2 * 0.22 + s3 * 0.10) * fd * 0.9, 1.0,\n"
    "                             (s2 * 0.4 - s3 * 0.16) * fd * 0.9));\n"
    "    vec3 rd = reflect(-V, wn);\n"
    "    vec3 sky_r = sky_at(rd, u_sun, u_sun_col, zen, hor);\n"
    "    float ndv = clamp(dot(wn, V), 0.0, 1.0);\n"
    "    float fren = 0.03 + 0.97 * pow(1.0 - ndv, 5.0);\n"
    "    vec3 hv = normalize(u_sun + V);\n"
    "    float ndh = max(dot(hv, wn), 0.0);\n"
    "    float spec = pow(ndh, 900.0) * 26.0 + pow(ndh, 90.0) * 0.8;\n"
    "    vec3 body = vec3(0.035, 0.105, 0.115) * (0.55 + 0.45 * ao);\n"
    "    vec3 c = body + sky_r * (0.16 + 0.58 * fren) + u_sun_col * spec * sv;\n"
    "    c *= u_exposure;\n"
    "    c = mix(c, fog_c, fog);\n"
    "    gl_FragColor = vec4(to_display(c), 1.0);\n"
    "    return;\n"
    "  }\n"
    "  float d = max(dot(n, u_sun), 0.0);\n"
    "  d = d * d * (3.0 - 2.0 * d) * 0.35 + d * 0.65;\n"
    "  float hemi = 0.5 + 0.5 * n.y;\n"
    "  vec3 amb = (u_ground_col + (u_sky_col - u_ground_col) * hemi) * ao;\n"
    "  vec3 lin = alb * alb;\n"
    "  vec3 c = lin * (amb + u_sun_col * d * sv) + u_sky_col * fres * 0.055 * ao\n"
    "         + u_emissive * 6.0;\n"
    "  c *= u_exposure;\n"
    "  c = mix(c, fog_c, fog);\n"
    "  gl_FragColor = vec4(to_display(c), 1.0);\n"
    "}\n";

// ---- sky: one full-screen quad, the ray rebuilt from the camera basis
static const char* kSkyVS =
    "attribute vec2 a_p;\n"
    "varying XPREC vec2 v_p;\n"
    "void main(){ v_p = a_p; gl_Position = vec4(a_p, 0.999, 1.0); }\n";

static const char* kSkyFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_p;\n"
    "uniform XPREC vec3 u_fwd, u_right, u_up;\n"
    "uniform XPREC float u_tan, u_aspect, u_exposure;\n"
    "uniform XPREC vec3 u_sun, u_sun_col;\n"
    "uniform XPREC vec3 u_zen, u_hor;\n"
    "float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 34.56);\n"
    "                   return fract(p.x * p.y); }\n"
    "float noise2(vec2 p){\n"
    "  vec2 i = floor(p); vec2 f = p - i; f = f * f * (3.0 - 2.0 * f);\n"
    "  float a = h21(i), b = h21(i + vec2(1.0, 0.0));\n"
    "  float c = h21(i + vec2(0.0, 1.0)), d = h21(i + vec2(1.0, 1.0));\n"
    "  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);\n"
    "}\n"
    "void main(){\n"
    "  vec3 d = normalize(u_fwd + u_right * (v_p.x * u_tan * u_aspect)\n"
    "                           + u_up * (v_p.y * u_tan));\n"
    "  float y = d.y;\n"
    "  float t = y > 0.0 ? 1.0 - exp(-3.1 * y) : 0.0;\n"
    "  vec3 c = mix(u_hor, u_zen, t);\n"
    "  float cs = dot(d, u_sun);\n"
    "  if (cs > 0.0) {\n"
    "    float glow = pow(cs, 24.0) * 0.24 + pow(cs, 4.0) * 0.05;\n"
    "    float disc = cs > 0.9985 ? 1.0 : pow(cs, 900.0);\n"
    "    c += u_sun_col * glow + vec3(30.0) * disc;\n"
    "  }\n"
    "  if (y > 0.03) {\n"
    "    vec2 q = d.xz / (y + 0.10) * 7.0;\n"
    "    float f = 0.62 * noise2(q) + 0.26 * noise2(q * 2.1 + vec2(11.0, 0.0))\n"
    "            + 0.12 * noise2(q * 4.3 + vec2(0.0, -7.0));\n"
    "    float cov = clamp((f - 0.56) * 4.0, 0.0, 1.0);\n"
    "    cov = cov * cov * (3.0 - 2.0 * cov) * clamp(y * 4.0, 0.0, 1.0);\n"
    "    float lit = 0.55 + 0.45 * clamp(cs * 1.6, 0.0, 1.0);\n"
    "    c = mix(c, vec3(0.105, 0.115, 0.132) * lit, cov * 0.85);\n"
    "  }\n"
    "  if (y < 0.0) c = mix(c, vec3(0.10), clamp(-y * 6.0, 0.0, 1.0));\n"
    "  gl_FragColor = vec4(to_display(c * u_exposure), 1.0);\n"
    "}\n";

// ---- ground skirt: a huge quad under the level, so the 87 m lawn never ends in mid-air
static const char* kGroundVS =
    "attribute vec2 a_xz;\n"
    "uniform mat4 u_mvp;\n"
    "uniform float u_y;\n"
    "uniform XPREC vec3 u_eye;\n"
    "varying XPREC vec3 v_wp;\n"
    "void main(){\n"
    "  v_wp = vec3(a_xz.x + u_eye.x, u_y, a_xz.y + u_eye.z);\n"
    "  gl_Position = u_mvp * vec4(v_wp, 1.0);\n"
    "}\n";

static const char* kGroundFS =
    "precision XPREC float;\n"
    "varying XPREC vec3 v_wp;\n"
    "uniform XPREC vec3 u_eye, u_sun, u_sun_col, u_sky_col, u_fog_col, u_albedo;\n"
    "uniform XPREC float u_exposure, u_fog_start, u_fog_density;\n"
    "float h21(vec2 p){ p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 34.56);\n"
    "                   return fract(p.x * p.y); }\n"
    "void main(){\n"
    "  float dist = length(v_wp - u_eye);\n"
    "  float patch = h21(floor(v_wp.xz * 0.05));\n"
    "  vec3 alb = u_albedo * (0.85 + 0.30 * patch);\n"
    "  vec3 c = alb * alb * (u_sky_col + u_sun_col * max(u_sun.y, 0.0));\n"
    "  c *= u_exposure;\n"
    "  float fog = 1.0 - exp(-max(dist - u_fog_start, 0.0) * u_fog_density);\n"
    "  c = mix(c, u_fog_col * u_exposure, fog);\n"
    "  gl_FragColor = vec4(to_display(c), 1.0);\n"
    "}\n";

// ---- objectives: additive billboards (clip-space corners, pre-projected by the CPU)
static const char* kOrbVS =
    "attribute vec4 a_clip;\n"
    "attribute vec2 a_c;\n"
    "varying XPREC vec2 v_c;\n"
    "void main(){ v_c = a_c; gl_Position = a_clip; }\n";

static const char* kOrbFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_c;\n"
    "uniform float u_alpha;\n"
    "uniform float u_pulse;\n"
    "void main(){\n"
    "  float r2 = dot(v_c, v_c);\n"
    "  if (r2 > 1.0) discard;\n"
    "  float a = 1.0 - r2; a = a * a * u_alpha * u_pulse;\n"
    "  gl_FragColor = vec4(to_display(vec3(2.4, 1.9, 0.75) * a * 2.0), a);\n"
    "}\n";

// ---- post processing: bright pass -> separable blur -> god rays -> composite
static const char* kPostQuadVS =
    "attribute vec2 a_p;\n"          // -1..1 clip space
    "varying XPREC vec2 v_uv;\n"
    "uniform vec2 u_scale;\n"        // cover scale about the centre (1 = full target)
    "uniform vec2 u_shift;\n"
    // a_p is clip space, so it has to be mapped into 0..1 before it can be a texture
    // coordinate. Writing v_uv = a_p directly (as v3.0 did) makes every sample with a
    // negative coordinate clamp to the edge texel: the left half of the screen became a
    // smear of the left column and the whole post chain - bloom, rays, composite - was
    // reading the wrong pixels.
    "void main(){\n"
    "  vec2 q = a_p * 0.5 + 0.5;\n"
    "  v_uv = (q - 0.5) * u_scale + 0.5 + u_shift;\n"
    "  gl_Position = vec4(a_p, 0.0, 1.0);\n"
    "}\n";

static const char* kBrightFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_uv;\n"
    "uniform sampler2D u_tex;\n"
    "void main(){\n"
    "  vec3 c = texture2D(u_tex, v_uv).rgb;\n"
    "  float lum = max(max(c.r, c.g), c.b);\n"
    // the scene arrives in display space now, so the knee sits just under white: this is a
    // bloom on highlights and the sun, not an HDR extraction
    "  float k = clamp((lum - 0.68) / max(lum, 1e-4), 0.0, 1.0);\n"   // soft knee
    "  gl_FragColor = vec4(c * k, 1.0);\n"
    "}\n";

static const char* kBlurFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_uv;\n"
    "uniform sampler2D u_tex;\n"
    "uniform XPREC vec2 u_dir;\n"        // texel-sized step
    "void main(){\n"
    "  vec3 c = texture2D(u_tex, v_uv).rgb * 0.2270270270;\n"
    "  c += texture2D(u_tex, v_uv + u_dir * 1.3846153846).rgb * 0.3162162162;\n"
    "  c += texture2D(u_tex, v_uv - u_dir * 1.3846153846).rgb * 0.3162162162;\n"
    "  c += texture2D(u_tex, v_uv + u_dir * 3.2307692308).rgb * 0.0702702703;\n"
    "  c += texture2D(u_tex, v_uv - u_dir * 3.2307692308).rgb * 0.0702702703;\n"
    "  gl_FragColor = vec4(c, 1.0);\n"
    "}\n";

static const char* kRaysFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_uv;\n"
    "uniform sampler2D u_tex;\n"
    "uniform XPREC vec2 u_sun;      // sun position in uv space\n"
    "uniform XPREC float u_strength;\n"
    "void main(){\n"
    "  if (u_strength <= 0.0) { gl_FragColor = vec4(0.0); return; }\n"
    "  vec2 delta = (u_sun - v_uv) / 40.0;\n"
    "  vec2 p = v_uv;\n"
    "  vec3 acc = vec3(0.0);\n"
    "  float decay = 1.0, wsum = 0.0;\n"
    "  for (int i = 0; i < 40; ++i) {\n"
    "    p += delta;\n"
    "    if (p.x < 0.0 || p.y < 0.0 || p.x > 1.0 || p.y > 1.0) break;\n"
    "    acc += texture2D(u_tex, p).rgb * decay;\n"
    "    wsum += decay;\n"
    "    decay *= 0.955;\n"
    "  }\n"
    "  gl_FragColor = vec4(acc / max(wsum, 1e-4) * u_strength, 1.0);\n"
    "}\n";

static const char* kCompositeFS =
    "precision XPREC float;\n"
    "varying XPREC vec2 v_uv;\n"
    "uniform sampler2D u_scene;\n"
    "uniform sampler2D u_bloom;\n"
    "uniform sampler2D u_rays;\n"
    "uniform float u_bloom_amt;\n"
    "uniform float u_rays_amt;\n"
    "void main(){\n"
    // Display space in, display space out. The scene pass already applied exposure, ACES and
    // the sRGB curve (see kCommonGlsl), so all this pass does is add glow.
    "  vec3 c = texture2D(u_scene, v_uv).rgb;\n"
    "  c += texture2D(u_bloom, v_uv).rgb * u_bloom_amt;\n"
    "  c += texture2D(u_rays, v_uv).rgb * u_rays_amt;\n"
    "  vec3 o = clamp(c, 0.0, 1.0);\n"
    // 8-bit output over a 3-stop sky gradient bands badly without a dither
    "  float d = fract(sin(dot(v_uv, vec2(12.9898, 78.233))) * 43758.5453) / 255.0;\n"
    "  gl_FragColor = vec4(o + d - 0.5 / 255.0, 1.0);\n"
    "}\n";

// ------------------------------------------------------------------ GL state
struct Prog {
    GLuint id = 0;
    GLint mvp = -1, posmin = -1, posscl = -1, tex = -1, has_tex = -1, base = -1, cutoff = -1;
    GLint foliage = -1, glass = -1, water = -1, emissive = -1, eye = -1, sun = -1, sun_col = -1;
    GLint sky_col = -1, ground_col = -1, fog_col = -1, exposure = -1, fog_start = -1,
          fog_density = -1, time = -1, wind = -1;
};

// A render target: colour texture + framebuffer. No depth for the post targets.
struct Target {
    GLuint fbo = 0, tex = 0;
    int w = 0, h = 0;
    bool create(int nw, int nh, bool depth) {
        w = nw;
        h = nh;
        glGenTextures(1, &tex);
        glBindTexture(GL_TEXTURE_2D, tex);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glGenFramebuffers(1, &fbo);
        glBindFramebuffer(GL_FRAMEBUFFER, fbo);
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0);
        if (depth) {
            glGenRenderbuffers(1, &rb);
            glBindRenderbuffer(GL_RENDERBUFFER, rb);
            glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT16, w, h);
            glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, rb);
        }
        const GLenum st = glCheckFramebufferStatus(GL_FRAMEBUFFER);
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        return st == GL_FRAMEBUFFER_COMPLETE;
    }
    void destroy() {
        if (fbo) glDeleteFramebuffers(1, &fbo);
        if (tex) glDeleteTextures(1, &tex);
        if (rb) glDeleteRenderbuffers(1, &rb);
        fbo = tex = rb = 0;
        w = h = 0;
    }
    GLuint rb = 0;
};

static struct {
    VModel model;
    Game game;
    Level level;
    Prog model_p, sky_p, orb_p, ground_p, bright_p, blur_p, rays_p, comp_p;
    Target scene, bright, blur_a, blur_b, rays;
    GLuint quad_vbo = 0;
    GLint q_scale = -1, q_shift = -1;                 // quad VS (per program)
    GLint b_tex = -1, bl_tex = -1, bl_dir = -1, r_tex = -1, r_sun = -1, r_strength = -1;
    GLint c_scene = -1, c_bloom = -1, c_rays = -1, c_bloom_amt = -1, c_rays_amt = -1;
    bool post_ok = false;
    float render_scale = 1.0f;                        // 1080p cap, see rebuild_targets()
    float ft_avg = 0.0f, last_scale_change = 0.0f;    // frame-rate governor state
    float ao_mean = 0.0f, sun_mean = 0.0f;            // logged once, for diagnostics
    bool attr_checked = false;
    GLenum last_gl_error = 0;

    // ---- on-device self-diagnosis. This sandbox has no phone, and two shipped builds were
    // diagnosed only from JPEG screenshots. Everything the renderer can measure about itself
    // is collected into `diag` and printed on screen by HudView, so the next screenshot IS
    // the bug report.
    std::string diag;                 // one fact per line, shown in-game
    int frames_drawn = 0;
    bool probed_clear = false, probed_frame = false;
    unsigned char px_clear[4] = {0, 0, 0, 0};
    unsigned char px_scene[4] = {0, 0, 0, 0};
    unsigned char px_final[4] = {0, 0, 0, 0};
    bool post_auto_disabled = false;
    // if the scene pass ever draws nothing, clear to saturated blue instead of black: the
    // next screenshot then says "a frame was presented but empty" instead of a mute black
    bool alert_clear = false;
    int probe_x = 4, probe_y = 4;
    GLuint vbo = 0, ibo = 0, sky_vbo = 0, orb_vbo = 0, ground_vbo = 0, white_tex = 0;
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

// Cross-stage precision. GLSL ES requires the *same* precision for a varying, and for any
// uniform declared in both stages - otherwise the program refuses to link, which is exactly
// how v1 of this game shipped a black screen ("L0001 ... The precision does not match",
// reporting only the first of seven mismatches). Both stages are compiled with this same
// token, chosen once from what the driver actually supports, so they can never disagree.
static std::string g_prec_token = "highp";

static GLuint compile(GLenum type, const char* src, std::string* err) {
    GLuint s = glCreateShader(type);
    // ORDER IS SEMANTICS in GLSL ES: the default float precision has to be declared before
    // any function that takes or returns a float. The first cut injected kCommonGlsl straight
    // after "#define XPREC", i.e. ahead of the shader's own `precision` line, and every scene
    // program died with "no default precision defined for function 'aces_fit'" - a black
    // screen on the device that no host test could see. Declaring the precision here, in the
    // prefix, makes the order correct for every shader by construction (a second
    // `precision` statement later in the source is a harmless redeclaration).
    // A vertex shader is guaranteed highp, and should keep it: downgrading the vertex stage
    // to mediump would quantise world positions at ~1 m in a 90 m garden.
    const std::string prec = type == GL_VERTEX_SHADER ? std::string("highp") : g_prec_token;
    const std::string prefix = std::string("#define XPREC ") + prec + "\nprecision " + prec +
                               " float;\n";
    const char* parts[3] = {prefix.c_str(), kCommonGlsl, src};
    glShaderSource(s, 3, parts, nullptr);
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
    // The post chain leaves unit 2 active. Uploading here without saying which unit is
    // meant put the model textures somewhere the model shader never samples.
    glActiveTexture(GL_TEXTURE0);
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

static void make_white_texture() {
    const unsigned char px[4] = {255, 255, 255, 255};
    glGenTextures(1, &G.white_tex);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, G.white_tex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, px);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
}

static void diag_add(const char* fmt, ...) {
    char buf[256];
    va_list ap;
    va_start(ap, fmt);
    std::vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (!G.diag.empty()) G.diag += "\n";
    G.diag += buf;
    LOGI("diag: %s", buf);
}

static void attribs_only(int count) {
    for (int i = 0; i < 4; ++i) {
        if (i < count) glEnableVertexAttribArray((GLuint)i);
        else glDisableVertexAttribArray((GLuint)i);
    }
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
    glUniform1f(p.water, (d.flags & VPK_FLAG_WATER) ? 1.0f : 0.0f);
    glUniform1f(p.time, (float)G.time_s);
    glUniform1f(p.wind, (d.flags & VPK_FLAG_CUTOUT) ? 1.0f : 0.0f);
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
    // highp in the fragment stage is optional in ES 2.0: ask the driver, then use the same
    // answer in both stages
    g_prec_token = "mediump";
    const char* exts = (const char*)glGetString(GL_SHADING_LANGUAGE_VERSION);
    if (exts) LOGI("GLSL: %s", exts);
    GLint range[2] = {0, 0}, precision = 0;
    glGetShaderPrecisionFormat(GL_FRAGMENT_SHADER, GL_HIGH_FLOAT, range, &precision);
    if (precision > 0) g_prec_token = "highp";
    LOGI("cross-stage precision: %s", g_prec_token.c_str());
    static const char* kModelAttribs[] = {"a_pos", "a_nrm", "a_uv", "a_ao"};
    G.model_p.id = link(kModelVS, kModelFS, kModelAttribs, 4, &err);
    if (!G.model_p.id) {
        G.status = "model shader: " + err;
        return;
    }
    const Prog* p = &G.model_p;
    Prog* m = &G.model_p;
    m->mvp = glGetUniformLocation(p->id, "u_mvp");
    m->time = glGetUniformLocation(p->id, "u_time");
    m->wind = glGetUniformLocation(p->id, "u_wind");
    m->water = glGetUniformLocation(p->id, "u_water");
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

    // ---- post-processing programs: all draw one full-screen quad in clip space
    static const char* kQuadAttribs[] = {"a_p"};
    G.bright_p.id = link(kPostQuadVS, kBrightFS, kQuadAttribs, 1, &err);
    G.blur_p.id = link(kPostQuadVS, kBlurFS, kQuadAttribs, 1, &err);
    G.rays_p.id = link(kPostQuadVS, kRaysFS, kQuadAttribs, 1, &err);
    G.comp_p.id = link(kPostQuadVS, kCompositeFS, kQuadAttribs, 1, &err);
    G.q_scale = glGetUniformLocation(G.comp_p.id, "u_scale");
    G.q_shift = glGetUniformLocation(G.comp_p.id, "u_shift");
    G.b_tex = glGetUniformLocation(G.bright_p.id, "u_tex");
    G.bl_tex = glGetUniformLocation(G.blur_p.id, "u_tex");
    G.bl_dir = glGetUniformLocation(G.blur_p.id, "u_dir");
    G.r_tex = glGetUniformLocation(G.rays_p.id, "u_tex");
    G.r_sun = glGetUniformLocation(G.rays_p.id, "u_sun");
    G.r_strength = glGetUniformLocation(G.rays_p.id, "u_strength");
    G.c_scene = glGetUniformLocation(G.comp_p.id, "u_scene");
    G.c_bloom = glGetUniformLocation(G.comp_p.id, "u_bloom");
    G.c_rays = glGetUniformLocation(G.comp_p.id, "u_rays");
    G.c_bloom_amt = glGetUniformLocation(G.comp_p.id, "u_bloom_amt");
    G.c_rays_amt = glGetUniformLocation(G.comp_p.id, "u_rays_amt");
    G.post_ok = G.bright_p.id && G.blur_p.id && G.rays_p.id && G.comp_p.id;
    if (!G.post_ok) LOGE("post-processing programs failed: %s", err.c_str());

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
    // full-screen quad for the post passes
    static const float quad2[] = {-1, -1, 1, -1, -1, 1, 1, 1};
    glGenBuffers(1, &G.quad_vbo);
    glBindBuffer(GL_ARRAY_BUFFER, G.quad_vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof quad2, quad2, GL_STATIC_DRAW);

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
    make_white_texture();

    // what we are actually running on
    {
        const char* vendor = (const char*)glGetString(GL_VENDOR);
        const char* rend = (const char*)glGetString(GL_RENDERER);
        const char* ver = (const char*)glGetString(GL_VERSION);
        diag_add("gpu: %s | %s | %s", vendor ? vendor : "?", rend ? rend : "?",
                 ver ? ver : "?");
        diag_add("precision: %s", g_prec_token.c_str());
        const char* names[8] = {"model", "sky", "orb", "ground", "bright", "blur", "rays", "comp"};
        const GLuint ids[8] = {G.model_p.id, G.sky_p.id, G.orb_p.id, G.ground_p.id,
                               G.bright_p.id, G.blur_p.id, G.rays_p.id, G.comp_p.id};
        std::string failed;
        for (int i = 0; i < 8; ++i)
            if (!ids[i]) failed += std::string(failed.empty() ? "" : " ") + names[i];
        diag_add("programs: %s", failed.empty() ? "all 8 linked"
                                                : ("FAILED: " + failed).c_str());
        diag_add("post: %s", G.post_ok ? "on" : "off (direct to screen)");
    }
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

// The orthonormal camera basis the *view matrix* uses. mat4_lookat builds its right axis as
// fwd x world-up, so screen right is (-fwd.z, 0, fwd.x) - the opposite of (cos yaw, -sin yaw).
// v3.0 used that opposite vector here, and up = right x fwd then came out as (0,-1,0): the
// skybox was rendered rotated 180 degrees, showing the "below the horizon" haze over the top
// half of the screen and putting the sun's disc on the wrong side of the sky.
static void camera_basis(const float yaw, const float pitch, float fwd[3], float right[3],
                         float up[3]) {
    const float cp = cosf(pitch), sp = sinf(pitch);
    fwd[0] = sinf(yaw) * cp;
    fwd[1] = sp;
    fwd[2] = cosf(yaw) * cp;
    const float rl = sqrtf(fwd[0] * fwd[0] + fwd[2] * fwd[2]);
    if (rl > 1e-5f) {
        right[0] = -fwd[2] / rl;
        right[1] = 0.0f;
        right[2] = fwd[0] / rl;
    } else {   // looking straight up or down: any right vector will do
        right[0] = 1.0f;
        right[1] = 0.0f;
        right[2] = 0.0f;
    }
    up[0] = right[1] * fwd[2] - right[2] * fwd[1];
    up[1] = right[2] * fwd[0] - right[0] * fwd[2];
    up[2] = right[0] * fwd[1] - right[1] * fwd[0];
    const float ul = sqrtf(up[0] * up[0] + up[1] * up[1] + up[2] * up[2]);
    if (ul > 1e-5f) {
        up[0] /= ul;
        up[1] /= ul;
        up[2] /= ul;
    }
}

static void draw_sky(const float eye[3], const float yaw, const float pitch) {
    const GameSun& s = game_sun();
    float fwd[3], right[3], up[3];
    camera_basis(yaw, pitch, fwd, right, up);
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
    // Must equal zen/hor in sky_at() in kModelFS: the glass and the pool reflect sky_at(),
    // so a different gradient up here made the reflected sky brighter than the real one.
    const float zen[3] = {0.105f, 0.175f, 0.335f};
    const float hor[3] = {0.330f, 0.360f, 0.390f};
    glUniform3fv(G.s_zen, 1, zen);
    glUniform3fv(G.s_hor, 1, hor);
    glBindBuffer(GL_ARRAY_BUFFER, G.sky_vbo);
    attribs_only(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
}

static void draw_orbs(const float eye[3], const float yaw, const float pitch) {
    float fwd[3], right[3], up[3];
    camera_basis(yaw, pitch, fwd, right, up);
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
    attribs_only(2);
    glVertexAttribPointer(0, 4, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
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
    const float albedo[3] = {0.105f, 0.165f, 0.062f};   // must match game_sim.cpp
    glUniform3fv(G.g_albedo, 1, albedo);
    glBindBuffer(GL_ARRAY_BUFFER, G.ground_vbo);
    attribs_only(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
}

static void draw_model(const Mat4& mvp, const float eye[3]) {
    glUseProgram(G.model_p.id);
    glBindBuffer(GL_ARRAY_BUFFER, G.vbo);
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, G.ibo);
    attribs_only(4);
    glVertexAttribPointer(0, 3, GL_UNSIGNED_SHORT, GL_FALSE, VPK_VERTEX_STRIDE, (void*)0);
    glVertexAttribPointer(1, 4, GL_BYTE, GL_TRUE, VPK_VERTEX_STRIDE, (void*)8);
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, VPK_VERTEX_STRIDE, (void*)12);
    // bytes 6..7 are the baked occlusion pair, normalised to 0..1
    glVertexAttribPointer(3, 2, GL_UNSIGNED_BYTE, GL_TRUE, VPK_VERTEX_STRIDE, (void*)6);
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
            glActiveTexture(GL_TEXTURE0);
            if (d.tex != VPK_NO_TEXTURE) {
                upload_texture(d.tex);
                glBindTexture(GL_TEXTURE_2D, G.tex[d.tex]);
            } else {
                glBindTexture(GL_TEXTURE_2D, G.white_tex);
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

// Rebuild the off-screen targets at the current render_scale. Called on resize and by the
// frame-rate governor below.
static void rebuild_targets() {
    int rw = G.w, rh = G.h;
    if (rh > 1080) {
        rw = (int)((float)G.w * 1080.0f / (float)G.h + 0.5f);
        rh = 1080;
    }
    rw = (int)((float)rw * G.render_scale + 0.5f);
    rh = (int)((float)rh * G.render_scale + 0.5f);
    if (rw < 2) rw = 2;
    if (rh < 2) rh = 2;
    const int qw = rw / 4 > 0 ? rw / 4 : 1, qh = rh / 4 > 0 ? rh / 4 : 1;
    G.scene.destroy();
    G.bright.destroy();
    G.blur_a.destroy();
    G.blur_b.destroy();
    G.rays.destroy();
    bool ok = G.scene.create(rw, rh, true);
    if (ok) ok = G.bright.create(qw, qh, false);
    if (ok) ok = G.blur_a.create(qw, qh, false);
    if (ok) ok = G.blur_b.create(qw, qh, false);
    if (ok) ok = G.rays.create(qw, qh, false);
    G.post_ok = ok;
    if (!ok) {
        G.status = "render target incomplete at " + std::to_string(rw) + "x" + std::to_string(rh);
        LOGE("%s", G.status.c_str());
    }
    LOGI("surface %dx%d, rendering %dx%d (scale %.2f)", G.w, G.h, rw, rh, G.render_scale);
}

JNIEXPORT void JNICALL
Java_ai_arena_villagame_GameRenderer_nativeResize(JNIEnv*, jobject, jint w, jint h) {
    G.w = w > 0 ? w : 1;
    G.h = h > 0 ? h : 1;
    G.aspect = (float)G.w / (float)G.h;
    rebuild_targets();
}

// Sun position in uv space, or (-10,-10) when it is behind the camera.
static void sun_uv(const float eye[3], float yaw, float pitch, float* u, float* v) {
    const GameSun& s = game_sun();
    Mat4 vp;
    build_mvp(eye, yaw, pitch, 0.0f, &vp);
    const float p[3] = {eye[0] + s.dir[0] * 500.0f, eye[1] + s.dir[1] * 500.0f,
                        eye[2] + s.dir[2] * 500.0f};
    float c[4];
    for (int i = 0; i < 4; ++i)
        c[i] = p[0] * vp.m[i] + p[1] * vp.m[4 + i] + p[2] * vp.m[8 + i] + vp.m[12 + i];
    if (c[3] <= 0.0f) {
        *u = -10.0f;
        *v = -10.0f;
        return;
    }
    *u = (c[0] / c[3] * 0.5f + 0.5f);
    *v = (1.0f - (c[1] / c[3] * 0.5f + 0.5f));
}

static void post_chain(const float eye[3], float yaw, float pitch) {
    const int rw = G.scene.w, rh = G.scene.h;
    const int qw = G.bright.w, qh = G.bright.h;
    const GameSun& gs = game_sun();

    // 1. bright pass: the scene, reduced 4x, thresholded
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glBindFramebuffer(GL_FRAMEBUFFER, G.bright.fbo);
    glViewport(0, 0, qw, qh);
    glUseProgram(G.bright_p.id);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, G.scene.tex);
    glUniform1i(G.b_tex, 0);
    glBindBuffer(GL_ARRAY_BUFFER, G.quad_vbo);
    attribs_only(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

    // 2. two blur directions
    const float tx = 1.0f / (float)qw, ty = 1.0f / (float)qh;
    glUseProgram(G.blur_p.id);
    glUniform1i(G.bl_tex, 0);
    glBindFramebuffer(GL_FRAMEBUFFER, G.blur_a.fbo);
    glViewport(0, 0, qw, qh);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, G.bright.tex);
    glUniform2f(G.bl_dir, tx * 1.5f, 0.0f);
    glBindBuffer(GL_ARRAY_BUFFER, G.quad_vbo);
    attribs_only(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

    glBindFramebuffer(GL_FRAMEBUFFER, G.blur_b.fbo);
    glViewport(0, 0, qw, qh);
    glBindTexture(GL_TEXTURE_2D, G.blur_a.tex);
    glUniform2f(G.bl_dir, 0.0f, ty * 1.5f);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

    // 3. god rays along the line to the sun, from the blurred bright buffer
    float su, sv;
    sun_uv(eye, yaw, pitch, &su, &sv);
    const bool rays_on = su > -1.0f && sv > -1.0f && (su < 1.6f && su > -0.6f) &&
                         (sv < 1.6f && sv > -0.6f);
    glUseProgram(G.rays_p.id);
    glUniform1i(G.r_tex, 0);
    glUniform2f(G.r_sun, su, sv);
    glUniform1f(G.r_strength, rays_on ? 1.0f : 0.0f);
    glBindFramebuffer(GL_FRAMEBUFFER, G.rays.fbo);
    glViewport(0, 0, qw, qh);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, G.blur_b.tex);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);

    // 4. composite to the screen, through ACES
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glViewport(0, 0, G.w, G.h);
    glUseProgram(G.comp_p.id);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, G.scene.tex);
    glUniform1i(G.c_scene, 0);
    glActiveTexture(GL_TEXTURE1);
    glBindTexture(GL_TEXTURE_2D, G.blur_b.tex);
    glUniform1i(G.c_bloom, 1);
    glActiveTexture(GL_TEXTURE2);
    glBindTexture(GL_TEXTURE_2D, G.rays.tex);
    glUniform1i(G.c_rays, 2);
    glUniform1f(G.c_bloom_amt, 0.34f);
    glUniform1f(G.c_rays_amt, rays_on ? 0.55f : 0.0f);
    glUniform2f(G.q_scale, 1.0f, 1.0f);
    glUniform2f(G.q_shift, 0.0f, 0.0f);
    glBindBuffer(GL_ARRAY_BUFFER, G.quad_vbo);
    attribs_only(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, (void*)0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glActiveTexture(GL_TEXTURE0);
    glEnable(GL_DEPTH_TEST);
    (void)gs;
}

// Read one pixel from whatever framebuffer is currently bound.
static void probe_px(unsigned char out[4]) {
    out[0] = out[1] = out[2] = out[3] = 0;
    glReadPixels(G.probe_x, G.probe_y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, out);
}

static int px_sum(const unsigned char p[4]) { return p[0] + p[1] + p[2]; }

// Frame 1: can we render into the off-screen target and read it back at all? If not, post
// processing is switched off before anything else is drawn, and the game renders straight to
// the screen - correct, just without bloom and god rays.
static void self_test_target() {
    const bool offscreen = G.post_ok && G.scene.fbo != 0;
    if (!offscreen) {
        diag_add("self-test: no off-screen target, drawing direct");
        return;
    }
    glBindFramebuffer(GL_FRAMEBUFFER, G.scene.fbo);
    glViewport(0, 0, G.scene.w, G.scene.h);
    glClearColor(1.0f, 0.0f, 1.0f, 1.0f);          // magenta: unmistakable
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    probe_px(G.px_clear);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    const bool ok = G.px_clear[0] > 200 && G.px_clear[1] < 60 && G.px_clear[2] > 200;
    diag_add("self-test fbo %dx%d: clear reads %d,%d,%d -> %s", G.scene.w, G.scene.h,
             G.px_clear[0], G.px_clear[1], G.px_clear[2], ok ? "ok" : "BROKEN");
    if (!ok) {
        G.post_ok = false;
        G.post_auto_disabled = true;
        diag_add("post disabled: cannot read the off-screen target");
    }
    G.probed_clear = true;
}

JNIEXPORT void JNICALL
Java_ai_arena_villagame_GameRenderer_nativeFrame(JNIEnv*, jobject, jfloat dt, jfloat jx,
                                                 jfloat jy, jfloat dyaw, jfloat dpitch) {
    if (!G.ready) return;
    G.time_s += dt;
    // Stick convention, in one place: the Java side reports x = right, y = *up* (a drag
    // towards the top of the screen is +y). game_core wants +fwd = the way the camera faces,
    // which is what +y already means, so the value passes through unchanged. v3.0 negated it
    // here while the Java side also negated the pitch, which made both the stick and the look
    // run backwards.
    G.game.update(dt, jy, jx, dyaw, dpitch);

    // One-time self-check of the baked lighting attribute: if the pack's AO/sun bytes ever
    // stop arriving (a wrong attribute slot, a bad stride), every surface goes flat and dark.
    // Reading them back once at runtime is the only way to see that from a device log.
    if (!G.attr_checked && G.model.h.n_verts > 0) {
        G.attr_checked = true;
        const uint8_t* vb = G.model.vertex_base();
        double ao = 0, sun = 0;
        const uint32_t n = G.model.h.n_verts < 4096 ? G.model.h.n_verts : 4096;
        for (uint32_t i = 0; i < n; ++i) {
            ao += vb[(size_t)i * VPK_VERTEX_STRIDE + 6];
            sun += vb[(size_t)i * VPK_VERTEX_STRIDE + 7];
        }
        ao /= 255.0 * n;
        sun /= 255.0 * n;
        LOGI("baked lighting: ao %.2f sun %.2f over %u verts", ao, sun, n);
        if (sun < 0.01) LOGE("the pack carries no sun visibility - rebuild model.vpk");
        G.ao_mean = (float)ao;
        G.sun_mean = (float)sun;
    }

    // Frame-rate governor. The post chain is four extra full-screen passes; on a phone that
    // could not hold 30 fps at the panel resolution, render fewer pixels rather than stutter.
    // It never goes below half resolution, and it climbs back up if the device had headroom.
    if (G.post_ok) {
        G.ft_avg = G.ft_avg <= 0.0f ? dt : G.ft_avg * 0.9f + dt * 0.1f;
        if (G.time_s - G.last_scale_change > 2.0 && G.ft_avg > 0.0f) {
            if (G.ft_avg > 0.045f && G.render_scale > 0.51f) {
                G.render_scale = G.render_scale > 0.7f ? 0.7f : 0.5f;
                G.last_scale_change = G.time_s;
                rebuild_targets();
            } else if (G.ft_avg < 0.019f && G.render_scale < 0.99f) {
                G.render_scale = G.render_scale < 0.6f ? 0.7f : 1.0f;
                G.last_scale_change = G.time_s;
                rebuild_targets();
            }
        }
    }
    float eye[3];
    G.game.eye_pos(eye);
    const float yaw = G.game.p.yaw, pitch = G.game.p.pitch;
    const float roll = sinf(G.game.bob * 0.5f) * 0.006f * G.game.bob_amp;
    Mat4 mvp;
    build_mvp(eye, yaw, pitch, roll, &mvp);

    // first frame: prove the off-screen target works before trusting it with the whole image
    if (!G.probed_clear) self_test_target();

    const bool offscreen = G.post_ok && G.scene.fbo != 0;
    glBindFramebuffer(GL_FRAMEBUFFER, offscreen ? G.scene.fbo : 0);
    glViewport(0, 0, offscreen ? G.scene.w : G.w, offscreen ? G.scene.h : G.h);
    glDisable(GL_SCISSOR_TEST);
    glDepthMask(GL_TRUE);
    if (G.alert_clear) glClearColor(0.0f, 0.22f, 0.65f, 1.0f);
    else glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    draw_sky(eye, yaw, pitch);
    draw_skirt(mvp, eye);
    draw_model(mvp, eye);
    draw_orbs(eye, yaw, pitch);

    // Frame 3: is anything actually being drawn, and does the composite survive the trip?
    const bool probe_now = G.frames_drawn == 2 && !G.probed_frame;
    if (probe_now && offscreen) probe_px(G.px_scene);

    if (offscreen) {
        post_chain(eye, yaw, pitch);
        if (probe_now) probe_px(G.px_final);
    }

    if (probe_now) {
        G.probed_frame = true;
        const int scene = px_sum(G.px_scene), fin = offscreen ? px_sum(G.px_final) : scene;
        if (offscreen) {
            diag_add("frame probe: scene %d,%d,%d -> post %d,%d,%d", G.px_scene[0],
                     G.px_scene[1], G.px_scene[2], G.px_final[0], G.px_final[1], G.px_final[2]);
        } else {
            diag_add("frame probe (direct): %d,%d,%d", G.px_scene[0], G.px_scene[1],
                     G.px_scene[2]);
        }
        // If the scene has colour and the composite is black, the post chain is the fault:
        // turn it off and carry on drawing a correct, unbloomed image.
        if (offscreen && scene > 12 && fin < 8) {
            G.post_ok = false;
            G.post_auto_disabled = true;
            diag_add("post disabled: it turned a non-black scene black");
        }
        if (scene < 8 && fin < 8) {
            G.alert_clear = true;
            diag_add("scene probe is black: drew %u draws at eye %.1f %.1f %.1f yaw %.2f",
                     G.model.h.n_draws, eye[0], eye[1], eye[2], yaw);
            diag_add("clearing blue from now on: a blue screen means the frame is presented");
        }
    }
    ++G.frames_drawn;

    // One glGetError per frame for the first second: a silently ignored GL error here is
    // exactly how a broken device build gets mistaken for "the mesh is wrong".
    if (G.time_s < 1.0f) {
        const GLenum e = glGetError();
        if (e != GL_NO_ERROR && G.last_gl_error != e) {
            G.last_gl_error = e;
            LOGE("GL error 0x%04x at t=%.2fs", (unsigned)e, G.time_s);
        }
    }
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
    const std::string& text = G.diag.empty() ? G.status : G.diag;
    return env->NewStringUTF(text.c_str());
}

}  // extern "C"
