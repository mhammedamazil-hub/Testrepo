package ai.arena.villaviewer;

import android.content.Context;
import android.opengl.GLES20;
import android.opengl.GLSurfaceView;
import android.util.Log;
import android.view.MotionEvent;

import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.List;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * Draws model.vpk (see tools/villa_pack.py + cpp/vpk.h).
 *
 * Design choices, all for a weak tablet:
 *  - fixed function level GLES2 (no extensions, no GLES3);
 *  - 16-bit indices only, so no OES_element_index_uint on the driver;
 *  - lighting is per-vertex, the fragment shader is a texture multiply;
 *  - 87 draw calls, no mipmap re-upload per frame, no allocation per frame;
 *  - the model is loaded once on a worker thread; frames before it is ready just show sky.
 */
public class VillaRenderer implements GLSurfaceView.Renderer {
    private static final String TAG = "VillaViewer";

    // ---- vpk.h constants, mirrored here
    private static final int HEADER_SIZE = 84;
    private static final int DRAW_SIZE = 100;
    private static final int TEX_SIZE = 8;
    private static final int VERTEX_STRIDE = 20;
    private static final int NO_TEXTURE = 0xFFFF;
    private static final int FLAG_CUTOUT = 1;
    private static final int FLAG_TWO_SIDED = 2;
    private static final int FLAG_GLASS = 4;

    // sun direction: elevation 20 deg, azimuth 232 deg - must match vpk_default_sun() in
    // shade.h (the desktop preview tool) so the app and the test render agree
    private static final float SUN_X = -0.7405f, SUN_Y = 0.3420f, SUN_Z = 0.5785f;

    private static final String SKY_VS =
            "attribute vec2 a_p;\n" +
            "varying vec2 v_p;\n" +
            "void main(){ v_p = a_p * 0.5 + 0.5; gl_Position = vec4(a_p, 0.999, 1.0); }\n";
    private static final String SKY_FS =
            "precision mediump float;\n" +
            "varying vec2 v_p;\n" +
            "void main(){\n" +
            // sky above, distant ground below a soft horizon
            "  float t = smoothstep(0.44, 0.72, v_p.y);\n" +
            "  vec3 sky = mix(vec3(0.74,0.82,0.90), vec3(0.55,0.68,0.86), v_p.y);\n" +
            "  vec3 gnd = vec3(0.30,0.33,0.24);\n" +
            "  gl_FragColor = vec4(mix(gnd, sky, t), 1.0);\n" +
            "}\n";

    private static final String VS =
            "attribute vec3 a_pos;\n" +          // quantised: 0..65535
            "attribute vec4 a_nrm;\n" +          // int8, normalised
            "attribute vec2 a_uv;\n" +
            "uniform vec3 u_pos_min;\n" +
            "uniform vec3 u_pos_scale;\n" +
            "uniform mat4 u_vp;\n" +
            "uniform vec3 u_sun;\n" +
            "uniform vec3 u_sun_col;\n" +
            "uniform vec3 u_sky_col;\n" +
            "uniform vec3 u_gnd_col;\n" +
            "uniform float u_sun_e;\n" +
            "uniform float u_amb_e;\n" +
            "varying vec2 v_uv;\n" +
            "varying vec3 v_light;\n" +
            "void main(){\n" +
            "  vec3 wp = u_pos_min + (a_pos / 65535.0) * u_pos_scale;\n" +
            "  gl_Position = u_vp * vec4(wp, 1.0);\n" +
            "  v_uv = a_uv;\n" +
            "  vec3 n = normalize(a_nrm.xyz);\n" +
            "  float d = max(dot(n, u_sun), 0.0);\n" +
            "  float band = 0.5 + 0.5 * n.y;\n" +
            "  vec3 amb = mix(u_gnd_col, u_sky_col, band);\n" +
            "  v_light = amb * u_amb_e + u_sun_col * d * u_sun_e;\n" +
            "}\n";

    private static final String FS =
            "precision mediump float;\n" +
            "uniform sampler2D u_tex;\n" +
            "uniform float u_has_tex;\n" +
            "uniform vec4 u_base;\n" +
            "uniform float u_cutoff;\n" +
            "uniform float u_glass;\n" +
            "varying vec2 v_uv;\n" +
            "varying vec3 v_light;\n" +
            "void main(){\n" +
            "  vec4 c = u_base;\n" +
            "  if (u_has_tex > 0.5) c *= texture2D(u_tex, v_uv);\n" +
            "  if (u_cutoff > 0.0 && c.a < u_cutoff) discard;\n" +
            "  if (u_glass > 0.5) {\n" +
            // glTF transmission is not available on GLES2: glass is a dark blended tint
            "    vec3 tint = vec3(0.10, 0.13, 0.15) * (0.6 + 0.4 * length(v_light));\n" +
            "    gl_FragColor = vec4(tint, 0.62);\n" +
            "    return;\n" +
            "  }\n" +
            "  vec3 lin = c.rgb * c.rgb;      // cheap sRGB -> linear\n" +
            "  vec3 lit = lin * v_light;\n" +
            "  vec3 tm = lit / (lit + vec3(0.85));\n" +
            "  gl_FragColor = vec4(sqrt(tm * 1.30), 1.0);\n" +
            "}\n";

    private static class Draw {
        int indexOffset, indexCount, vertOffset, vertCount;
        float[] posMin = new float[3];
        float[] posScale = new float[3];
        int tex;
        int flags;
        float[] base = new float[4];
        float cutoff;
    }

    private final Context ctx;

    private int skyProg, prog;
    private int skyPosLoc;
    private int aPos, aNrm, aUv;
    private int uVp, uPosMin, uPosScale, uSun, uSunCol, uSkyCol, uGndCol, uSunE, uAmbE;
    private int uTex, uHasTex, uBase, uCutoff, uGlass;
    private final FloatBuffer skyQuad;

    private final List<Draw> draws = new ArrayList<Draw>();
    private int vboVerts, vboIdx;
    private final List<Integer> textures = new ArrayList<Integer>();
    private volatile boolean ready = false;
    private volatile String status = "loading model...";
    private int totalVerts, totalIndices;

    // camera
    private float targetX, targetY, targetZ, radius = 30f;
    private float dist = 45f, yaw = (float) Math.PI, pitch = 0.20f;

    // stats
    private long frames = 0, lastReport = 0;

    VillaRenderer(Context c) {
        ctx = c;
        float[] q = {-1f, -1f, 3f, -1f, -1f, 3f};
        skyQuad = ByteBuffer.allocateDirect(q.length * 4).order(ByteOrder.nativeOrder())
                .asFloatBuffer();
        skyQuad.put(q).position(0);
    }

    String status() { return status; }

    // ------------------------------------------------------------------ gl setup
    private static int compile(int type, String src) {
        int s = GLES20.glCreateShader(type);
        GLES20.glShaderSource(s, src);
        GLES20.glCompileShader(s);
        int[] ok = new int[1];
        GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0);
        if (ok[0] == 0) {
            Log.e(TAG, "shader: " + GLES20.glGetShaderInfoLog(s));
            GLES20.glDeleteShader(s);
            return 0;
        }
        return s;
    }

    private static int program(String vs, String fs) {
        int v = compile(GLES20.GL_VERTEX_SHADER, vs);
        int f = compile(GLES20.GL_FRAGMENT_SHADER, fs);
        if (v == 0 || f == 0) return 0;
        int p = GLES20.glCreateProgram();
        GLES20.glAttachShader(p, v);
        GLES20.glAttachShader(p, f);
        GLES20.glLinkProgram(p);
        int[] ok = new int[1];
        GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, ok, 0);
        if (ok[0] == 0) {
            Log.e(TAG, "link: " + GLES20.glGetProgramInfoLog(p));
            return 0;
        }
        return p;
    }

    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        GLES20.glClearColor(0.55f, 0.68f, 0.86f, 1f);
        GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        GLES20.glDepthFunc(GLES20.GL_LEQUAL);
        GLES20.glDisable(GLES20.GL_CULL_FACE);   // one-sided walls would vanish

        skyProg = program(SKY_VS, SKY_FS);
        prog = program(VS, FS);
        if (prog != 0) {
            aPos = GLES20.glGetAttribLocation(prog, "a_pos");
            aNrm = GLES20.glGetAttribLocation(prog, "a_nrm");
            aUv = GLES20.glGetAttribLocation(prog, "a_uv");
            uVp = GLES20.glGetUniformLocation(prog, "u_vp");
            uPosMin = GLES20.glGetUniformLocation(prog, "u_pos_min");
            uPosScale = GLES20.glGetUniformLocation(prog, "u_pos_scale");
            uSun = GLES20.glGetUniformLocation(prog, "u_sun");
            uSunCol = GLES20.glGetUniformLocation(prog, "u_sun_col");
            uSkyCol = GLES20.glGetUniformLocation(prog, "u_sky_col");
            uGndCol = GLES20.glGetUniformLocation(prog, "u_gnd_col");
            uSunE = GLES20.glGetUniformLocation(prog, "u_sun_e");
            uAmbE = GLES20.glGetUniformLocation(prog, "u_amb_e");
            uTex = GLES20.glGetUniformLocation(prog, "u_tex");
            uHasTex = GLES20.glGetUniformLocation(prog, "u_has_tex");
            uBase = GLES20.glGetUniformLocation(prog, "u_base");
            uCutoff = GLES20.glGetUniformLocation(prog, "u_cutoff");
            uGlass = GLES20.glGetUniformLocation(prog, "u_glass");
        } else {
            status = "shader compile failed - see logcat";
        }
        if (skyProg != 0) skyPosLoc = GLES20.glGetAttribLocation(skyProg, "a_p");

        // a new EGL context means every VBO/texture handle is stale: reload
        ready = false;
        startLoad();
    }

    @Override
    public void onSurfaceChanged(GL10 unused, int w, int h) {
        GLES20.glViewport(0, 0, w, h);
        aspect = (float) w / Math.max(1, h);
    }

    private float aspect = 16f / 9f;

    // ------------------------------------------------------------------ loading
    private void startLoad() {
        final Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    loadModel();
                } catch (Exception e) {
                    status = "load failed: " + e;
                    Log.e(TAG, "load", e);
                }
            }
        }, "vpk-load");
        t.setPriority(Thread.NORM_PRIORITY - 1);
        t.start();
    }

    private static int rd32(byte[] b, int o) {
        return (b[o] & 0xFF) | ((b[o + 1] & 0xFF) << 8) | ((b[o + 2] & 0xFF) << 16)
                | ((b[o + 3] & 0xFF) << 24);
    }

    private static float rdf(byte[] b, int o) {
        return Float.intBitsToFloat(rd32(b, o));
    }

    private void loadModel() throws Exception {
        InputStream in = ctx.getAssets().open("model.vpk");
        byte[] head = new byte[HEADER_SIZE];
        int got = 0;
        while (got < HEADER_SIZE) {
            int n = in.read(head, got, HEADER_SIZE - got);
            if (n <= 0) throw new Exception("short header");
            got += n;
        }
        if (head[0] != 'V' || head[1] != 'P' || head[2] != 'K' || head[3] != '1')
            throw new Exception("not a VPK1 asset - run tools/villa_pack.py");
        int nDraws = rd32(head, 8);
        int nTex = rd32(head, 12);
        int nVerts = rd32(head, 16);
        int nIdx = rd32(head, 20);
        float fx0 = rdf(head, 40), fy0 = rdf(head, 44), fz0 = rdf(head, 48);
        float fx1 = rdf(head, 52), fy1 = rdf(head, 56), fz1 = rdf(head, 60);
        targetX = 0.5f * (fx0 + fx1);
        targetY = 0.5f * (fy0 + fy1) * 0.6f;
        targetZ = 0.5f * (fz0 + fz1);
        float dx = fx1 - fx0, dz = fz1 - fz0;
        radius = Math.max(dx, dz);
        dist = radius * 1.45f;

        byte[] meta = new byte[DRAW_SIZE * nDraws + TEX_SIZE * nTex];
        got = 0;
        while (got < meta.length) {
            int n = in.read(meta, got, meta.length - got);
            if (n <= 0) throw new Exception("short draw table");
            got += n;
        }
        final List<Draw> dl = new ArrayList<Draw>(nDraws);
        for (int i = 0; i < nDraws; i++) {
            int o = i * DRAW_SIZE;
            Draw d = new Draw();
            d.indexOffset = rd32(meta, o);
            d.indexCount = rd32(meta, o + 4);
            d.vertOffset = rd32(meta, o + 8);
            d.vertCount = rd32(meta, o + 12);
            for (int k = 0; k < 3; k++) d.posMin[k] = rdf(meta, o + 16 + k * 4);
            for (int k = 0; k < 3; k++) d.posScale[k] = rdf(meta, o + 28 + k * 4);
            int to = o + 48 + TEX_SIZE * nTex;
            d.tex = ((meta[to] & 0xFF) | ((meta[to + 1] & 0xFF) << 8));
            d.flags = ((meta[to + 2] & 0xFF) | ((meta[to + 3] & 0xFF) << 8));
            for (int k = 0; k < 4; k++) d.base[k] = rdf(meta, to + 4 + k * 4);
            d.cutoff = rdf(meta, to + 20);
            dl.add(d);
        }
        // the texture table sits right after the draws, in the same read
        final int[] texOff = new int[nTex];
        final int[] texLen = new int[nTex];
        for (int i = 0; i < nTex; i++) {
            int o = DRAW_SIZE * nDraws + i * TEX_SIZE;
            texOff[i] = rd32(meta, o);
            texLen[i] = rd32(meta, o + 4);
        }
        int vertBytes = nVerts * VERTEX_STRIDE;
        byte[] verts = new byte[vertBytes];
        got = 0;
        while (got < vertBytes) {
            int n = in.read(verts, got, vertBytes - got);
            if (n <= 0) throw new Exception("short vertex data");
            got += n;
        }
        byte[] idx = new byte[nIdx * 2];
        got = 0;
        while (got < idx.length) {
            int n = in.read(idx, got, idx.length - got);
            if (n <= 0) throw new Exception("short index data");
            got += n;
        }
        byte[][] decoded = new byte[nTex][];
        int base = HEADER_SIZE + DRAW_SIZE * nDraws + TEX_SIZE * nTex + vertBytes + nIdx * 2;
        for (int i = 0; i < nTex; i++) {
            int skip = texOff[i] - base;
            while (skip > 0) {
                long s = in.skip(skip);
                if (s <= 0) throw new Exception("cannot seek to texture " + i);
                skip -= (int) s;
            }
            byte[] img = new byte[texLen[i]];
            got = 0;
            while (got < img.length) {
                int n = in.read(img, got, img.length - got);
                if (n <= 0) throw new Exception("short texture " + i);
                got += n;
            }
            decoded[i] = img;
            base = texOff[i] + texLen[i];
        }
        in.close();

        // ---- GPU upload (this thread has no EGL context: use a shared one via the
        //      GLSurfaceView queue is overkill for one asset; instead we hand the raw
        //      arrays to the GL thread through these fields)
        pendingVerts = verts;
        pendingIdx = idx;
        pendingTex = decoded;
        pendingDraws = dl;
        pendingCount = nVerts;
        pendingIdxCount = nIdx;
        status = String.format("loaded %d draws, %d triangles", dl.size(), nIdx / 3);
        uploaded = true;
    }

    private byte[] pendingVerts, pendingIdx;
    private byte[][] pendingTex;
    private List<Draw> pendingDraws;
    private int pendingCount, pendingIdxCount;
    private volatile boolean uploaded = false;

    private void uploadPending() {
        if (!uploaded) return;
        uploaded = false;
        int[] b = new int[1];
        GLES20.glGenBuffers(1, b, 0);
        vboVerts = b[0];
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vboVerts);
        ByteBuffer vb = ByteBuffer.allocateDirect(pendingVerts.length)
                .order(ByteOrder.nativeOrder());
        vb.put(pendingVerts).position(0);
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, pendingVerts.length, vb,
                GLES20.GL_STATIC_DRAW);
        GLES20.glGenBuffers(1, b, 0);
        vboIdx = b[0];
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, vboIdx);
        ByteBuffer ib = ByteBuffer.allocateDirect(pendingIdx.length)
                .order(ByteOrder.nativeOrder());
        ib.put(pendingIdx).position(0);
        GLES20.glBufferData(GLES20.GL_ELEMENT_ARRAY_BUFFER, pendingIdx.length, ib,
                GLES20.GL_STATIC_DRAW);
        pendingVerts = null;
        pendingIdx = null;

        for (int i = 0; i < pendingTex.length; i++) {
            byte[] img = pendingTex[i];
            android.graphics.Bitmap bmp = android.graphics.BitmapFactory
                    .decodeByteArray(img, 0, img.length);
            int id = 0;
            if (bmp != null) {
                int[] t = new int[1];
                GLES20.glGenTextures(1, t, 0);
                id = t[0];
                GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, id);
                GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MIN_FILTER,
                        GLES20.GL_LINEAR_MIPMAP_LINEAR);
                GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_MAG_FILTER,
                        GLES20.GL_LINEAR);
                GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_S,
                        GLES20.GL_REPEAT);
                GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, GLES20.GL_TEXTURE_WRAP_T,
                        GLES20.GL_REPEAT);
                android.opengl.GLUtils.texImage2D(GLES20.GL_TEXTURE_2D, 0, bmp, 0);
                GLES20.glGenerateMipmap(GLES20.GL_TEXTURE_2D);
                bmp.recycle();
            }
            textures.add(Integer.valueOf(id));
        }
        pendingTex = null;
        textures.clear();
        draws.clear();
        draws.addAll(pendingDraws);
        totalVerts = pendingCount;
        totalIndices = pendingIdxCount;
        pendingDraws = null;
        ready = true;
        Log.i(TAG, "uploaded " + draws.size() + " draws, " + textures.size() + " textures, "
                + totalVerts + " verts");
    }

    // ------------------------------------------------------------------ camera
    private float[] vp = new float[16];

    private void buildCamera() {
        float cp = (float) Math.cos(pitch), sp = (float) Math.sin(pitch);
        float ex = targetX + dist * cp * (float) Math.sin(yaw);
        float ey = targetY + dist * sp;
        float ez = targetZ + dist * cp * (float) Math.cos(yaw);
        // look at target
        float fx = targetX - ex, fy = targetY - ey, fz = targetZ - ez;
        float fl = (float) Math.sqrt(fx * fx + fy * fy + fz * fz);
        fx /= fl; fy /= fl; fz /= fl;
        float sx = fy * 0f - fz * 1f, sy = fz * 0f - fx * 0f, sz = fx * 1f - fy * 0f;
        float sl = (float) Math.sqrt(sx * sx + sy * sy + sz * sz);
        sx /= sl; sy /= sl; sz /= sl;
        float ux = sy * fz - sz * fy, uy = sz * fx - sx * fz, uz = sx * fy - sy * fx;
        float f = 1f / (float) Math.tan(0.5f * 38.0 * Math.PI / 180.0);
        float n = 0.4f, fa = 1400f;
        float[] p = new float[16];
        p[0] = f / Math.max(0.5f, aspect);
        p[5] = f;
        p[10] = (fa + n) / (n - fa);
        p[11] = -1f;
        p[14] = (2f * fa * n) / (n - fa);
        float[] v = new float[16];
        v[0] = sx; v[4] = sy; v[8] = sz;
        v[1] = ux; v[5] = uy; v[9] = uz;
        v[2] = -fx; v[6] = -fy; v[10] = -fz;
        v[12] = -(sx * ex + sy * ey + sz * ez);
        v[13] = -(ux * ex + uy * ey + uz * ez);
        v[14] = (fx * ex + fy * ey + fz * ez);
        v[15] = 1f;
        // vp = p * v (column major)
        for (int c = 0; c < 4; c++) {
            for (int r = 0; r < 4; r++) {
                float s = 0;
                for (int k = 0; k < 4; k++) s += p[k * 4 + r] * v[c * 4 + k];
                vp[c * 4 + r] = s;
            }
        }
    }

    // ------------------------------------------------------------------ frame
    @Override
    public void onDrawFrame(GL10 unused) {
        if (uploaded && !ready) uploadPending();

        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT | GLES20.GL_DEPTH_BUFFER_BIT);

        if (skyProg != 0) {
            GLES20.glUseProgram(skyProg);
            GLES20.glDisable(GLES20.GL_DEPTH_TEST);
            GLES20.glEnableVertexAttribArray(skyPosLoc);
            GLES20.glVertexAttribPointer(skyPosLoc, 2, GLES20.GL_FLOAT, false, 0, skyQuad);
            GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, 3);
            GLES20.glDisableVertexAttribArray(skyPosLoc);
            GLES20.glEnable(GLES20.GL_DEPTH_TEST);
        }
        if (!ready || prog == 0) {
            countFrame();
            return;
        }

        buildCamera();
        GLES20.glUseProgram(prog);
        GLES20.glUniformMatrix4fv(uVp, 1, false, vp, 0);
        GLES20.glUniform3f(uSun, SUN_X, SUN_Y, SUN_Z);
        GLES20.glUniform3f(uSunCol, 1.00f, 0.88f, 0.72f);
        GLES20.glUniform3f(uSkyCol, 0.42f, 0.50f, 0.62f);
        GLES20.glUniform3f(uGndCol, 0.24f, 0.21f, 0.16f);
        GLES20.glUniform1f(uSunE, 1.15f);
        GLES20.glUniform1f(uAmbE, 1.00f);
        GLES20.glUniform1i(uTex, 0);
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0);

        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vboVerts);
        GLES20.glBindBuffer(GLES20.GL_ELEMENT_ARRAY_BUFFER, vboIdx);
        GLES20.glEnableVertexAttribArray(aPos);
        GLES20.glEnableVertexAttribArray(aNrm);
        GLES20.glEnableVertexAttribArray(aUv);
        GLES20.glVertexAttribPointer(aPos, 3, GLES20.GL_UNSIGNED_SHORT, false, VERTEX_STRIDE, 0);
        GLES20.glVertexAttribPointer(aNrm, 4, GLES20.GL_BYTE, true, VERTEX_STRIDE, 8);
        GLES20.glVertexAttribPointer(aUv, 2, GLES20.GL_FLOAT, false, VERTEX_STRIDE, 12);

        for (int i = 0; i < draws.size(); i++) {
            Draw d = draws.get(i);
            if (d.indexCount == 0) continue;
            boolean glass = (d.flags & FLAG_GLASS) != 0;
            if (glass) {
                GLES20.glEnable(GLES20.GL_BLEND);
                GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA);
                GLES20.glDepthMask(false);
            }
            GLES20.glUniform3f(uPosMin, d.posMin[0], d.posMin[1], d.posMin[2]);
            GLES20.glUniform3f(uPosScale, d.posScale[0], d.posScale[1], d.posScale[2]);
            GLES20.glUniform4f(uBase, d.base[0], d.base[1], d.base[2], d.base[3]);
            GLES20.glUniform1f(uCutoff, d.cutoff);
            GLES20.glUniform1f(uGlass, glass ? 1f : 0f);
            boolean hasTex = d.tex != NO_TEXTURE && d.tex < textures.size()
                    && textures.get(d.tex).intValue() != 0;
            GLES20.glUniform1f(uHasTex, hasTex ? 1f : 0f);
            if (hasTex) GLES20.glBindTexture(GLES20.GL_TEXTURE_2D,
                    textures.get(d.tex).intValue());
            GLES20.glDrawElements(GLES20.GL_TRIANGLES, d.indexCount,
                    GLES20.GL_UNSIGNED_SHORT, d.indexOffset * 2);
            if (glass) {
                GLES20.glDepthMask(true);
                GLES20.glDisable(GLES20.GL_BLEND);
            }
        }
        GLES20.glDisableVertexAttribArray(aPos);
        GLES20.glDisableVertexAttribArray(aNrm);
        GLES20.glDisableVertexAttribArray(aUv);
        countFrame();
    }

    private void countFrame() {
        frames++;
        long now = System.currentTimeMillis();
        if (now - lastReport > 5000) {
            if (lastReport != 0) {
                float fps = frames * 1000f / (now - lastReport);
                Log.i(TAG, String.format("%.1f fps", fps));
            }
            frames = 0;
            lastReport = now;
        }
    }

    // ------------------------------------------------------------------ input
    private float lastX, lastY;
    private float lastPinch = 0f;
    private int pointers = 0;

    boolean touch(MotionEvent e) {
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                lastX = e.getX();
                lastY = e.getY();
                pointers = 1;
                return true;
            case MotionEvent.ACTION_POINTER_DOWN:
                pointers = e.getPointerCount();
                lastPinch = spread(e);
                return true;
            case MotionEvent.ACTION_POINTER_UP:
                pointers = e.getPointerCount() - 1;
                return true;
            case MotionEvent.ACTION_MOVE:
                if (e.getPointerCount() >= 2) {
                    float s = spread(e);
                    if (lastPinch > 1f && s > 1f) {
                        dist *= lastPinch / s;
                        if (dist < radius * 0.22f) dist = radius * 0.22f;
                        if (dist > radius * 6f) dist = radius * 6f;
                    }
                    lastPinch = s;
                } else {
                    float dx = e.getX() - lastX, dy = e.getY() - lastY;
                    yaw -= dx * 0.006f;
                    pitch += dy * 0.005f;
                    if (pitch > 1.45f) pitch = 1.45f;
                    if (pitch < -0.30f) pitch = -0.30f;
                    lastX = e.getX();
                    lastY = e.getY();
                }
                return true;
            default:
                return false;
        }
    }

    private static float spread(MotionEvent e) {
        if (e.getPointerCount() < 2) return 0f;
        float dx = e.getX(0) - e.getX(1);
        float dy = e.getY(0) - e.getY(1);
        return (float) Math.sqrt(dx * dx + dy * dy);
    }
}
