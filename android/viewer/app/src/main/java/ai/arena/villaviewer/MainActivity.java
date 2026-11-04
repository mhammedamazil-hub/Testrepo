package ai.arena.villaviewer;

import android.app.Activity;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.util.Log;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * One screen, one GLSurfaceView, no libraries.
 *
 * Drag = orbit, pinch = zoom. That is the whole UI, because the point is to look at the
 * model on a weak tablet, not to build a 3D viewer.
 */
public class MainActivity extends Activity {
    private static final String TAG = "VillaViewer";
    private GLSurfaceView view;
    private TextView hint;
    private VillaRenderer renderer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);

        FrameLayout root = new FrameLayout(this);
        renderer = new VillaRenderer(this);
        view = new GLSurfaceView(this);
        view.setEGLContextClientVersion(2);
        // 16-bit colour + a 16-bit depth buffer is enough and is the cheapest thing a
        // low-end driver can give us
        view.setEGLConfigChooser(5, 6, 5, 0, 16, 0);
        view.setRenderer(renderer);
        view.setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
        root.addView(view, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        hint = new TextView(this);
        hint.setText("Drag to orbit  ·  pinch to zoom");
        hint.setTextColor(0xE6FFFFFF);
        hint.setTextSize(13f);
        hint.setPadding(28, 22, 28, 22);
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        lp.leftMargin = 18;
        lp.topMargin = 18;
        root.addView(hint, lp);

        view.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
                    hint.setVisibility(View.GONE);
                }
                boolean used = renderer.touch(event);
                if (used) v.performClick();
                return used;
            }
        });

        setContentView(root);
        Log.i(TAG, "villa viewer started, model asset: " + assetSize());
    }

    private String assetSize() {
        try {
            return getAssets().openFd("model.vpk").getLength() / (1024 * 1024) + " MB";
        } catch (Exception e) {
            return "MISSING (run tools/villa_pack.py)";
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (view != null) view.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (view != null) view.onResume();
    }
}
