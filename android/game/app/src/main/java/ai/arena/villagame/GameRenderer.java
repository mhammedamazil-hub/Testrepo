package ai.arena.villagame;

import android.content.Context;
import android.opengl.GLSurfaceView;
import android.util.Log;

import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/**
 * The bridge. All gameplay lives in C++ (cpp/game_core.h + game.cpp); this class only
 * forwards time and touch deltas in, and reads a few small integers back out for the HUD.
 */
public class GameRenderer implements GLSurfaceView.Renderer {

    private static final String TAG = "VillaGame";
    private static boolean loaded = false;

    private final Context ctx;
    private final GameSurface surface;
    private long lastNs = 0;
    private boolean initOk = false;
    private String status = "starting";
    private int frames = 0;
    private long fpsNs = 0;
    private float fps = 0f;

    // JNI
    private native boolean nativeInit(Object assetManager);
    private native void nativeResize(int w, int h);
    private native void nativeFrame(float dt, float jx, float jy, float dyaw, float dpitch);
    private native int nativeOrbs();
    private native int nativeTotal();
    private native float nativeTime();
    private native int nativeState();
    private native float nativeBearing();
    private native void nativeReset();
    private native String nativeStatus();

    public GameRenderer(Context ctx, GameSurface surface) {
        this.ctx = ctx;
        this.surface = surface;
        if (!loaded) {
            try {
                System.loadLibrary("villagame");
                loaded = true;
            } catch (Throwable t) {
                // A load failure is not fatal to the process; onDrawFrame will paint the
                // reason on the HUD instead of showing a black screen.
                Log.e(TAG, "libvillagame failed to load: " + t);
                status = "libvillagame: " + t;
            }
        }
    }

    public String status() { return status; }
    public float fps() { return fps; }

    public int orbs() {
        try {
            return initOk ? nativeOrbs() : 0;
        } catch (Throwable t) {
            return 0;
        }
    }

    public int total() {
        try {
            return initOk ? nativeTotal() : 0;
        } catch (Throwable t) {
            return 0;
        }
    }

    public float time() {
        try {
            return initOk ? nativeTime() : 0f;
        } catch (Throwable t) {
            return 0f;
        }
    }

    public int state() {
        try {
            return initOk ? nativeState() : 0;
        } catch (Throwable t) {
            return 0;
        }
    }

    public float bearing() {
        try {
            return initOk ? nativeBearing() : 99f;
        } catch (Throwable t) {
            return 99f;
        }
    }

    /** Start a fresh run (called when the player taps the win screen). */
    public void reset() {
        try {
            if (initOk) nativeReset();
        } catch (Throwable ignored) {
        }
    }

    @Override
    public void onSurfaceCreated(GL10 unused, EGLConfig config) {
        if (!loaded) return;
        try {
            initOk = nativeInit(ctx.getAssets());
            status = nativeStatus();
        } catch (Throwable t) {
            initOk = false;
            status = "nativeInit: " + t;
            Log.e(TAG, "nativeInit failed", t);
        }
        Log.i(TAG, "init ok=" + initOk + " status=" + status);
        lastNs = System.nanoTime();
    }

    @Override
    public void onSurfaceChanged(GL10 unused, int width, int height) {
        if (!initOk) return;
        nativeResize(width, height);
    }

    @Override
    public void onDrawFrame(GL10 unused) {
        long now = System.nanoTime();
        float dt = (now - lastNs) / 1e9f;
        lastNs = now;
        if (dt < 0f) dt = 0f;
        if (dt > 0.1f) dt = 0.1f;      // coming back from the home screen is not a jump
        if (!initOk) return;

        GameSurface.Stick st = surface.getStick();
        nativeFrame(dt, st.active ? st.x : 0f, st.active ? st.y : 0f,
                surface.takeYawDelta(), surface.takePitchDelta());
        surface.onFrame(dt);

        frames++;
        fpsNs += (long) (dt * 1e9);
        if (fpsNs > 500000000L) {
            fps = frames * 1e9f / fpsNs;
            frames = 0;
            fpsNs = 0;
        }
    }
}
