package ai.arena.villagame;

import android.content.Context;
import android.opengl.GLSurfaceView;
import android.view.MotionEvent;

/**
 * The GL surface plus the only input the game has: a thumb stick on the left and a look
 * drag on the right.
 *
 * Both are tracked by pointer id, so you can hold the stick and turn at the same time, and
 * putting a second thumb down on the right does not steal the stick. The stick is
 * "floating": it appears wherever you first press on the left half, which is what makes a
 * game feel right on a phone you are holding one-handed and on a tablet lying on a table.
 */
public class GameSurface extends GLSurfaceView {

    /** Where the stick is drawn; the HUD reads this every frame. */
    public static class Stick {
        public boolean active = false;
        public float baseX = 0, baseY = 0;   // pixels, screen space (y down)
        public float knobX = 0, knobY = 0;
        public float x = 0, y = 0;           // -1..1, y up
        public float radiusPx = 1;
    }

    private final GameRenderer renderer;
    private final Stick stick = new Stick();
    private final Audio audio;

    private int stickId = -1;
    private int lookId = -1;
    private float lookX = 0, lookY = 0;
    private float pendingYaw = 0, pendingPitch = 0;
    private float stepTimer = 0f;
    private int lastOrbs = 0;

    static final float LOOK_SENS = 0.0042f;   // radians per pixel of drag

    public GameSurface(Context ctx, Audio audio) {
        super(ctx);
        this.audio = audio;
        setEGLContextClientVersion(2);
        // 16-bit depth is enough for a 90 m garden and saves bandwidth on old GPUs
        setEGLConfigChooser(8, 8, 8, 0, 16, 0);
        renderer = new GameRenderer(ctx, this);
        setRenderer(renderer);
        setRenderMode(GLSurfaceView.RENDERMODE_CONTINUOUSLY);
        setPreserveEGLContextOnPause(true);
        setFocusable(true);
    }

    public GameRenderer getRenderer() {
        return renderer;
    }

    public Stick getStick() {
        return stick;
    }

    /** Look delta accumulated since the last frame, in radians. Consumed by the renderer. */
    public float takeYawDelta() {
        float v = pendingYaw;
        pendingYaw = 0;
        return v;
    }

    public float takePitchDelta() {
        float v = pendingPitch;
        pendingPitch = 0;
        return v;
    }

    /** Called by the renderer: one footstep per ~0.55 s while the stick is pushed. */
    void onFrame(float dt) {
        float mag = (float) Math.hypot(stick.x, stick.y);
        if (mag > 0.35f && renderer.state() == 0) {
            stepTimer -= dt * (0.6f + 0.7f * mag);
            if (stepTimer <= 0f) {
                audio.footstep(mag);
                stepTimer = 0.55f;
            }
        } else {
            stepTimer = 0f;
        }
        int orbs = renderer.orbs();
        if (orbs > lastOrbs) {
            audio.pickup();
            lastOrbs = orbs;
        } else if (orbs < lastOrbs) {
            lastOrbs = orbs;      // a new run started
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent e) {
        final int action = e.getActionMasked();
        switch (action) {
            case MotionEvent.ACTION_DOWN:
            case MotionEvent.ACTION_POINTER_DOWN: {
                int idx = e.getActionIndex();
                int id = e.getPointerId(idx);
                float x = e.getX(idx), y = e.getY(idx);
                if (x < getWidth() * 0.45f && !stick.active) {
                    stickId = id;
                    stick.active = true;
                    stick.baseX = x;
                    stick.baseY = y;
                    stick.knobX = x;
                    stick.knobY = y;
                    stick.radiusPx = Math.min(getWidth(), getHeight()) * 0.13f;
                    if (stick.radiusPx < 60f) stick.radiusPx = 60f;
                } else {
                    lookId = id;
                    lookX = x;
                    lookY = y;
                }
                // tapping the win screen starts a new run
                if (renderer.state() == 1) {
                    renderer.reset();
                    audio.click();
                }
                break;
            }
            case MotionEvent.ACTION_MOVE: {
                for (int i = 0; i < e.getPointerCount(); i++) {
                    int id = e.getPointerId(i);
                    float x = e.getX(i), y = e.getY(i);
                    if (id == stickId) {
                        float dx = x - stick.baseX;
                        float dy = y - stick.baseY;
                        float r = stick.radiusPx;
                        float len = (float) Math.hypot(dx, dy);
                        if (len > r) {           // let the base follow a long drag
                            stick.baseX += dx * (1f - r / len);
                            stick.baseY += dy * (1f - r / len);
                            dx = x - stick.baseX;
                            dy = y - stick.baseY;
                            len = r;
                        }
                        stick.knobX = stick.baseX + dx;
                        stick.knobY = stick.baseY + dy;
                        // Screen y grows downwards, so a drag towards the top of the screen is a
                        // negative dy - and that is "forward". Hence y = -dy/r, which is what
                        // the stick has always meant; the bug was that nativeFrame() negated it
                        // again before handing it to the movement code.
                        stick.x = dx / r;
                        stick.y = -dy / r;
                    } else if (id == lookId) {
                        float dx = x - lookX;
                        float dy = y - lookY;
                        lookX = x;
                        lookY = y;
                        pendingYaw += dx * LOOK_SENS;      // drag right, turn right
                        // Drag up (dy < 0) must look up. game_core adds dpitch straight into
                        // pitch, and positive pitch is up, so this has to be negated. v3.0
                        // did not, so the whole look axis ran backwards too.
                        pendingPitch -= dy * LOOK_SENS;
                    }
                }
                break;
            }
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_POINTER_UP:
            case MotionEvent.ACTION_CANCEL: {
                int idx = e.getActionIndex();
                int id = e.getPointerId(idx);
                if (id == stickId) {
                    stickId = -1;
                    stick.active = false;
                    stick.x = 0;
                    stick.y = 0;
                } else if (id == lookId) {
                    lookId = -1;
                }
                break;
            }
            default:
                break;
        }
        return true;
    }
}
