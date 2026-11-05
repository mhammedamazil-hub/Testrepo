package ai.arena.villagame;

import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;

/**
 * One activity, one GLSurfaceView, one HUD view on top.
 *
 * The 3D side is native (see cpp/game.cpp); everything you can read - joystick, counter,
 * timer, compass, win screen - is drawn by {@link HudView} with Canvas, so text is crisp at
 * any density and no font atlas is needed in GL.
 */
public class MainActivity extends Activity {

    private GameSurface surface;
    private HudView hud;
    private Audio audio;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        audio = new Audio(this);
        surface = new GameSurface(this, audio);
        hud = new HudView(this);
        hud.setRenderer(surface.getRenderer());
        hud.bindStick(surface.getStick());

        FrameLayout root = new FrameLayout(this);
        root.addView(surface, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        root.addView(hud, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);
        hideSystemUi();
    }

    private void hideSystemUi() {
        View decor = getWindow().getDecorView();
        decor.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @Override
    protected void onResume() {
        super.onResume();
        surface.onResume();
        audio.resume();
    }

    @Override
    protected void onPause() {
        audio.pause();
        surface.onPause();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        audio.release();
        super.onDestroy();
    }
}
