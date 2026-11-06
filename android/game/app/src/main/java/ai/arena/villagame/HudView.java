package ai.arena.villagame;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

/**
 * Everything you can read: crosshair, orb counter, run timer, a compass chevron that points
 * at the nearest collection, the thumb stick, and the win card.
 *
 * Drawn with Canvas on top of the GLView, which costs almost nothing and stays sharp on any
 * screen density - no bitmap font in the renderer, nothing to scale.
 */
public class HudView extends View {

    private GameRenderer renderer;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF rect = new RectF();
    private float dp = 1f;

    private int shownOrbs = -1, shownTotal = -1;
    private String statusText = null;

    public HudView(Context ctx) {
        super(ctx);
        dp = getResources().getDisplayMetrics().density;
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setStrokeWidth(2f * dp);
        paint.setColor(Color.WHITE);
        setWillNotDraw(false);
    }

    public void setRenderer(GameRenderer r) {
        renderer = r;
    }

    @Override
    protected void onDraw(Canvas c) {
        super.onDraw(c);
        if (renderer == null) return;
        final float w = getWidth(), h = getHeight();
        final float pad = 18f * dp;

        int orbs = renderer.orbs();
        int total = renderer.total();
        if (orbs != shownOrbs || total != shownTotal) {
            shownOrbs = orbs;
            shownTotal = total;
        }

        // a soft dark scrim behind the text so it reads against a bright lawn
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(0x66101418);
        rect.set(pad * 0.5f, pad * 0.5f, pad * 0.5f + 168f * dp, pad * 0.5f + 66f * dp);
        c.drawRoundRect(rect, 12f * dp, 12f * dp, paint);

        paint.setColor(Color.WHITE);
        paint.setTextSize(15f * dp);
        paint.setFakeBoldText(false);
        c.drawText("VILLA GARDEN", pad + 6f * dp, pad + 22f * dp, paint);

        if (shownTotal > 0) {
            paint.setTextSize(26f * dp);
            paint.setFakeBoldText(true);
            c.drawText(shownOrbs + " / " + shownTotal, pad + 6f * dp, pad + 52f * dp, paint);
            paint.setFakeBoldText(false);
        } else {
            paint.setTextSize(15f * dp);
            c.drawText("loading...", pad + 6f * dp, pad + 46f * dp, paint);
        }

        // timer, top right
        float t = renderer.time();
        int mins = (int) (t / 60f);
        int secs = (int) (t - mins * 60f);
        String clock = String.format(java.util.Locale.US, "%d:%02d", mins, secs);
        paint.setTextSize(22f * dp);
        paint.setTextAlign(Paint.Align.RIGHT);
        paint.setFakeBoldText(true);
        c.drawText(clock, w - pad, pad + 30f * dp, paint);
        paint.setFakeBoldText(false);
        paint.setTextAlign(Paint.Align.LEFT);

        // compass chevron: nearest uncollected orb, relative to where you are looking
        float bearing = renderer.bearing();
        if (bearing < 90f && renderer.state() == 0) {
            paint.setColor(0xFFFFC857);
            float cx = w * 0.5f;
            float cy = pad + 26f * dp;
            float r = 15f * dp;
            // bearing > 0 means "to my right": draw the arrow rotated by that angle
            c.save();
            c.rotate(bearing * 180f / (float) Math.PI, cx, cy);
            android.graphics.Path path = new android.graphics.Path();
            path.moveTo(cx, cy - r);
            path.lineTo(cx + r * 0.78f, cy + r * 0.7f);
            path.lineTo(cx, cy + r * 0.28f);
            path.lineTo(cx - r * 0.78f, cy + r * 0.7f);
            path.close();
            c.drawPath(path, paint);
            c.restore();
        }

        // crosshair
        paint.setColor(0xDDFFFFFF);
        c.drawCircle(w * 0.5f, h * 0.5f, 2.2f * dp, paint);

        // thumb stick: the surface owns it and the activity hands this view the instance
        if (stick != null && stick.active) {
            paint.setColor(0x33FFFFFF);
            c.drawCircle(stick.baseX, stick.baseY, stick.radiusPx, paint);
            paint.setColor(0x88FFFFFF);
            c.drawCircle(stick.knobX, stick.knobY, stick.radiusPx * 0.36f, paint);
        }

        // win card
        if (renderer.state() == 1) {
            paint.setColor(0xB2070A0D);
            c.drawRect(0, 0, w, h, paint);
            paint.setColor(Color.WHITE);
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTextSize(30f * dp);
            paint.setFakeBoldText(true);
            c.drawText("GARDEN CLEARED", w * 0.5f, h * 0.5f - 24f * dp, paint);
            paint.setTextSize(20f * dp);
            paint.setFakeBoldText(false);
            c.drawText("all " + shownTotal + " collected in " + clock, w * 0.5f,
                    h * 0.5f + 12f * dp, paint);
            paint.setTextSize(15f * dp);
            paint.setColor(0xCCDDE3E8);
            c.drawText("tap anywhere to walk it again", w * 0.5f, h * 0.5f + 52f * dp, paint);
            paint.setTextAlign(Paint.Align.LEFT);
        }

        if (renderer.fps() > 0f) {
            paint.setColor(0x88FFFFFF);
            paint.setTextSize(11f * dp);
            paint.setTextAlign(Paint.Align.RIGHT);
            c.drawText((int) renderer.fps() + " fps", w - pad, h - pad * 0.6f, paint);
            paint.setTextAlign(Paint.Align.LEFT);
        }

        // The self-diagnosis the native renderer collects (gpu, precision, program links,
        // frame-buffer selftest, pixel probes). It used to be drawn only when `total` was
        // zero, which meant every real error was invisible: two shipped builds were debugged
        // from a screenshot that showed nothing but black and a timer. Always show it.
        String s = renderer.status();
        if (s != null && !s.isEmpty()) {
            String[] lines = s.split("\n");
            paint.setStyle(Paint.Style.FILL);
            paint.setColor(0x99080A0C);
            float lh = 13f * dp;
            float boxH = lh * lines.length + 10f * dp;
            float boxW = 0f;
            paint.setTextSize(10f * dp);
            paint.setTextAlign(Paint.Align.LEFT);
            for (String l : lines) boxW = Math.max(boxW, paint.measureText(l));
            rect.set(pad * 0.5f, h - boxH - pad * 0.5f,
                     Math.min(w - pad * 0.5f, pad * 0.5f + boxW + 14f * dp), h - pad * 0.5f);
            c.drawRoundRect(rect, 8f * dp, 8f * dp, paint);
            paint.setColor(0xE6E8F0F4);
            float y = rect.top + 5f * dp + lh * 0.8f;
            for (String l : lines) {
                c.drawText(l, rect.left + 7f * dp, y, paint);
                y += lh;
            }
        }
        invalidate();
    }

    /** Set by MainActivity once the surface exists, so the stick is drawn where it is. */
    private GameSurface.Stick stick;

    public void bindStick(GameSurface.Stick s) {
        stick = s;
    }
}
