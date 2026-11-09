package dev.tabletagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.util.Base64;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import com.jcraft.jsch.ChannelShell;
import com.jcraft.jsch.HostKey;
import com.jcraft.jsch.HostKeyRepository;
import com.jcraft.jsch.JSch;
import com.jcraft.jsch.Session;
import com.jcraft.jsch.UserInfo;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends Activity {
    private static final int PICK_KEY = 17;
    private EditText host, port, user, password, passphrase;
    private TextView status, keyStatus;
    private LinearLayout setup;
    private WebView terminal;
    private byte[] privateKey;
    private volatile Session session;
    private volatile ChannelShell channel;
    private volatile OutputStream output;
    private volatile int cols = 80, rows = 24;
    private volatile int generation = 0;
    private final Object connectionLock = new Object();
    private final ExecutorService inputExecutor = Executors.newSingleThreadExecutor();
    private SharedPreferences prefs;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("hosts", MODE_PRIVATE);
        buildUi();
    }

    private int dp(int n) { return (int)(n * getResources().getDisplayMetrics().density + .5f); }
    private TextView label(String text, int size, int color) {
        TextView t = new TextView(this); t.setText(text); t.setTextSize(size); t.setTextColor(color); return t;
    }
    private Button button(String text, Runnable action) {
        Button b = new Button(this); b.setText(text); b.setAllCaps(false); b.setOnClickListener(v -> action.run()); return b;
    }
    private EditText field(String hint, boolean secret) {
        EditText e = new EditText(this); e.setSingleLine(true); e.setHint(hint); e.setTextColor(Color.WHITE); e.setHintTextColor(0xff91a3b0);
        if (secret) e.setInputType(129); else e.setInputType(1);
        return e;
    }
    private void buildUi() {
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(0xff101720); setContentView(root);
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(dp(12),dp(4),dp(8),dp(4));
        TextView title = label("TABLET AGENT", 17, 0xffb0e2dc); title.setTypeface(null, 1); header.addView(title, new LinearLayout.LayoutParams(0, -2, 1));
        status = label("Disconnected", 12, 0xffa9bac5); header.addView(status);
        header.addView(button("Setup", () -> {}));
        root.addView(header);
        setup = new LinearLayout(this); setup.setOrientation(LinearLayout.VERTICAL); setup.setPadding(dp(12),0,dp(12),dp(8));
        ScrollView setupScroll = new ScrollView(this); setupScroll.setFillViewport(false); setupScroll.addView(setup);
        root.addView(setupScroll, new LinearLayout.LayoutParams(-1, dp(250)));
        // Hide the container too, so the terminal can use the whole screen.
        header.getChildAt(2).setOnClickListener(v -> setupScroll.setVisibility(setupScroll.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE));
        TextView help = label("Connect to a trusted computer running SSH. Your agents and files stay on that computer.", 13, 0xffb8c8d1); setup.addView(help);
        LinearLayout address = new LinearLayout(this); host = field("Host or IP", false); port = field("Port", false); port.setInputType(2); port.setText("22"); user = field("Username", false);
        address.addView(host, new LinearLayout.LayoutParams(0,-2,3)); address.addView(port, new LinearLayout.LayoutParams(0,-2,1)); address.addView(user, new LinearLayout.LayoutParams(0,-2,2)); setup.addView(address);
        LinearLayout auth = new LinearLayout(this); password = field("SSH password (optional)",true); passphrase = field("Key passphrase (optional)",true);
        auth.addView(password,new LinearLayout.LayoutParams(0,-2,1)); auth.addView(passphrase,new LinearLayout.LayoutParams(0,-2,1)); setup.addView(auth);
        LinearLayout controls = new LinearLayout(this); controls.addView(button("Choose private key", this::pickKey)); controls.addView(button("Clear key", () -> {privateKey=null; keyStatus.setText("No key selected");}));
        keyStatus = label("No key selected",12,0xffa9bac5); controls.addView(keyStatus); setup.addView(controls);
        LinearLayout connections = new LinearLayout(this);
        connections.addView(button("Connect", () -> {connect();})); connections.addView(button("Disconnect", this::disconnect));
        connections.addView(button("Forget host keys", () -> new AlertDialog.Builder(this).setTitle("Forget all trusted host keys?").setMessage("You will need to verify fingerprints again.").setNegativeButton("Cancel",null).setPositiveButton("Forget",(d,w)->prefs.edit().clear().apply()).show())); setup.addView(connections);
        terminal = new WebView(this); terminal.setBackgroundColor(0xff0b1119); terminal.getSettings().setJavaScriptEnabled(true); terminal.getSettings().setAllowFileAccess(true); terminal.getSettings().setAllowContentAccess(false); terminal.getSettings().setAllowFileAccessFromFileURLs(false); terminal.getSettings().setAllowUniversalAccessFromFileURLs(false);
        terminal.setWebViewClient(new WebViewClient() { @Override public boolean shouldOverrideUrlLoading(WebView v, android.webkit.WebResourceRequest r) { return true; } });
        terminal.addJavascriptInterface(new Bridge(), "Android"); terminal.loadUrl("file:///android_asset/terminal.html"); root.addView(terminal, new LinearLayout.LayoutParams(-1,0,1));
        HorizontalKeys keys = new HorizontalKeys(this); root.addView(keys);
    }
    private class HorizontalKeys extends android.widget.HorizontalScrollView {
        HorizontalKeys(Context c) { super(c); setFillViewport(false); LinearLayout row = new LinearLayout(c); addView(row);
            row.addView(button("Keyboard", () -> {terminal.evaluateJavascript("focusTerminal()", null); terminal.requestFocus(); ((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showSoftInput(terminal, InputMethodManager.SHOW_IMPLICIT);}));
            row.addView(button("Esc", () -> send("\u001b"))); row.addView(button("Tab", () -> send("\t"))); row.addView(button("Ctrl-C", () -> send("\u0003"))); row.addView(button("↑", () -> send("\u001b[A"))); row.addView(button("↓", () -> send("\u001b[B")));
            row.addView(button("←", () -> send("\u001b[D"))); row.addView(button("→", () -> send("\u001b[C")));
            row.addView(button("jcode", () -> command("jcode"))); row.addView(button("Claude", () -> command("claude"))); row.addView(button("OpenCode", () -> command("opencode")));
        }
    }
    private void command(String cmd) { if (output == null) { setStatus("Connect first"); return; } new AlertDialog.Builder(this).setTitle("Send " + cmd + "?").setMessage("This types and runs the command in the current remote terminal. Make sure the shell is ready.").setNegativeButton("Cancel", null).setPositiveButton("Send", (d,w) -> send(cmd + "\r")).show(); }
    private void pickKey() { Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT); i.setType("*/*"); i.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(i, PICK_KEY); }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request,result,data);
        if (request != PICK_KEY || result != RESULT_OK || data == null || data.getData() == null) return;
        try (InputStream in = getContentResolver().openInputStream(data.getData()); ByteArrayOutputStream buf = new ByteArrayOutputStream()) {
            byte[] chunk = new byte[4096]; int n; while ((n=in.read(chunk)) != -1) { if (buf.size()+n > 131072) throw new IllegalArgumentException("Key file too large"); buf.write(chunk,0,n); }
            privateKey = buf.toByteArray(); keyStatus.setText("Key loaded for this session");
        } catch (Exception e) { privateKey=null; keyStatus.setText("Could not read key"); }
    }
    private void setStatus(String s) { runOnUiThread(() -> status.setText(s)); }
    private void connect() {
        String h = host.getText().toString().trim(), u = user.getText().toString().trim(); int p;
        try { p = Integer.parseInt(port.getText().toString()); if (p < 1 || p > 65535 || h.isEmpty() || u.isEmpty()) throw new Exception(); }
        catch (Exception e) { setStatus("Enter host, username and valid port"); return; }
        disconnect(); final int id = generation;
        final String pw = password.getText().toString(), phrase = passphrase.getText().toString(); final byte[] key = privateKey == null ? null : privateKey.clone();
        password.setText(""); passphrase.setText(""); setStatus("Connecting…");
        new Thread(() -> {
            Session s = null; ChannelShell ch = null;
            try {
                JSch jsch = new JSch(); jsch.setHostKeyRepository(new VerifiedHosts(id));
                if (key != null) jsch.addIdentity("selected-key", key, null, phrase.isEmpty() ? null : phrase.getBytes(StandardCharsets.UTF_8));
                s = jsch.getSession(u,h,p); if (!pw.isEmpty()) s.setPassword(pw);
                s.setConfig("StrictHostKeyChecking", "yes"); s.setConfig("PreferredAuthentications", "publickey,password");
                synchronized (connectionLock) { if (id != generation) return; session = s; }
                s.connect(20000); if (id != generation) return;
                ch = (ChannelShell)s.openChannel("shell"); ch.setPtyType("xterm-256color"); ch.setPtySize(cols, rows, 0, 0);
                InputStream in = ch.getInputStream(); OutputStream out = ch.getOutputStream(); synchronized (connectionLock) { if (id != generation) return; channel=ch; } ch.connect(20000); synchronized (connectionLock) { if (id != generation) return; output=out; }
                setStatus("Connected · " + u + "@" + h); runOnUiThread(() -> terminal.evaluateJavascript("resetTerminal()",null));
                byte[] buf = new byte[8192]; int n; while (id == generation && (n=in.read(buf)) != -1) { String b64 = Base64.encodeToString(buf, 0, n, Base64.NO_WRAP); runOnUiThread(() -> terminal.evaluateJavascript("receive('" + b64 + "')", null)); }
                if (id == generation) setStatus("Connection closed");
            } catch (Exception e) { if (id == generation) setStatus("SSH: " + (e.getMessage() == null ? "connection failed" : e.getMessage())); }
            finally { if (ch != null) ch.disconnect(); if (s != null) s.disconnect(); synchronized (connectionLock) { if (id == generation) { output=null; channel=null; session=null; } } }
        }, "ssh-session").start();
    }
    private void disconnect() { ChannelShell c; Session s; synchronized (connectionLock) { generation++; output=null; c=channel; channel=null; s=session; session=null; } if (c != null) c.disconnect(); if (s != null) s.disconnect(); setStatus("Disconnected"); }
    private void send(String data) { OutputStream out=output; if (out==null) return; inputExecutor.execute(() -> { try { if (out == output) { out.write(data.getBytes(StandardCharsets.UTF_8)); out.flush(); } } catch (Exception ignored) {} }); }
    private class Bridge {
        @JavascriptInterface public void send(String data) { MainActivity.this.send(data); }
        @JavascriptInterface public void resize(int c, int r) { if(c < 1 || r < 1 || c > 1000 || r > 1000) return; cols=c; rows=r; ChannelShell ch=channel; if(ch != null && ch.isConnected()) ch.setPtySize(c,r,0,0); }
    }
    private class VerifiedHosts implements HostKeyRepository {
        private final int id;
        VerifiedHosts(int id) { this.id=id; }
        @Override public int check(String hostName, byte[] key) {
            String encoded=Base64.encodeToString(key, Base64.NO_WRAP); String saved=prefs.getString(hostName, null);
            if (saved != null) return saved.equals(encoded) ? OK : CHANGED;
            try {
                String algorithm = new HostKey(hostName, key).getType();
                String fingerprint=Fingerprints.sha256(key);
                CountDownLatch latch=new CountDownLatch(1); AtomicBoolean accepted=new AtomicBoolean(false);
                runOnUiThread(() -> {
                    if (id != generation || isFinishing() || isDestroyed()) { latch.countDown(); return; }
                    new AlertDialog.Builder(MainActivity.this).setTitle("Verify SSH host key").setMessage("Host: " + hostName + "\nKey type: " + algorithm + "\nFingerprint: " + fingerprint + "\n\nCompare this with the server's fingerprint using a trusted channel. Only accept if they match. A changed key is always rejected.")
                        .setPositiveButton("Trust", (d,w) -> { accepted.set(true); latch.countDown(); }).setNegativeButton("Reject", (d,w) -> latch.countDown()).setOnCancelListener(d -> latch.countDown()).show();
                });
                if (!latch.await(90, TimeUnit.SECONDS) || !accepted.get() || id != generation) return CHANGED;
                prefs.edit().putString(hostName,encoded).commit(); return OK;
            } catch (Exception e) { return CHANGED; }
        }
        @Override public void add(HostKey hostkey, UserInfo ui) {}
        @Override public void remove(String host, String type) {}
        @Override public void remove(String host, String type, byte[] key) {}
        @Override public String getKnownHostsRepositoryID() { return "verified-hosts"; }
        @Override public HostKey[] getHostKey() { return new HostKey[0]; }
        @Override public HostKey[] getHostKey(String host, String type) { return new HostKey[0]; }
    }
    @Override protected void onDestroy() { disconnect(); inputExecutor.shutdownNow(); terminal.removeJavascriptInterface("Android"); terminal.destroy(); super.onDestroy(); }
}
