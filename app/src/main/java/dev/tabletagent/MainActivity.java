package dev.tabletagent;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.util.Base64;
import android.view.Gravity;
import android.view.inputmethod.InputMethodManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.util.Enumeration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/** Experimental on-device jcode terminal, not a remote shell. */
public class MainActivity extends Activity {
    private static final int IMPORT = 1, EXPORT = 2;
    private static final long MAX_IMPORT = 100L * 1024 * 1024;
    private final ExecutorService writes = Executors.newSingleThreadExecutor();
    private WebView terminal;
    private TextView status;
    private File home, workspace, caFile;
    private volatile int fd = -1, pid = -1, cols = 80, rows = 24;
    private volatile boolean starting = false;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        home = new File(getFilesDir(), "home"); workspace = new File(getFilesDir(), "workspace");
        home.mkdirs(); workspace.mkdirs(); caFile = new File(getFilesDir(), "android-ca.pem");
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(0xff101720); setContentView(root);
        LinearLayout header = new LinearLayout(this); header.setGravity(Gravity.CENTER_VERTICAL); header.setPadding(12, 4, 8, 4);
        TextView title = new TextView(this); title.setText("jcode · on device"); title.setTextSize(18); title.setTextColor(0xffb0e2dc);
        header.addView(title, new LinearLayout.LayoutParams(0,-2,1)); status = new TextView(this); status.setTextColor(0xffb8c8d1); status.setText("Stopped"); header.addView(status); root.addView(header);
        terminal = new WebView(this); terminal.setBackgroundColor(0xff0b1119); terminal.getSettings().setJavaScriptEnabled(true); terminal.getSettings().setAllowFileAccess(true); terminal.getSettings().setAllowContentAccess(false); terminal.getSettings().setAllowFileAccessFromFileURLs(false); terminal.getSettings().setAllowUniversalAccessFromFileURLs(false);
        terminal.setWebViewClient(new WebViewClient() { @Override public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest request) { return true; } });
        terminal.addJavascriptInterface(new Bridge(), "Android"); terminal.loadUrl("file:///android_asset/terminal.html"); root.addView(terminal, new LinearLayout.LayoutParams(-1,0,1));
        HorizontalScrollView scroll = new HorizontalScrollView(this); LinearLayout actions = new LinearLayout(this); scroll.addView(actions); root.addView(scroll);
        add(actions,"Start",this::start); add(actions,"Stop",this::stop);
        add(actions,"Import ZIP",this::importZip); add(actions,"Export ZIP",this::exportZip);
        add(actions,"Keyboard",() -> { terminal.evaluateJavascript("focusTerminal()",null); terminal.requestFocus(); ((InputMethodManager)getSystemService(Context.INPUT_METHOD_SERVICE)).showSoftInput(terminal,InputMethodManager.SHOW_IMPLICIT); });
        add(actions,"Esc",() -> send("\u001b")); add(actions,"Tab",() -> send("\t")); add(actions,"Ctrl-C",() -> send("\u0003"));
        add(actions,"↑",() -> send("\u001b[A")); add(actions,"↓",() -> send("\u001b[B")); add(actions,"←",() -> send("\u001b[D")); add(actions,"→",() -> send("\u001b[C"));
    }
    private void add(LinearLayout row, String text, Runnable r) { Button b = new Button(this); b.setText(text); b.setAllCaps(false); b.setOnClickListener(v -> r.run()); row.addView(b); }
    private void status(String message) { runOnUiThread(() -> status.setText(message)); }
    private void show(String title, String message) { runOnUiThread(() -> new AlertDialog.Builder(this).setTitle(title).setMessage(message).setPositiveButton("OK",null).show()); }
    private void start() {
        if (fd >= 0 || starting) return;
        starting = true; status("Starting…");
        new Thread(() -> {
            try {
                File exe = new File(getApplicationInfo().nativeLibraryDir, "libjcode.so");
                if (!exe.isFile()) throw new Exception("The native jcode binary is missing from this APK.");
                writeCertificates();
                long[] p = LocalPty.start(exe.getAbsolutePath(),home.getAbsolutePath(),workspace.getAbsolutePath(),caFile.getAbsolutePath(),cols,rows);
                if (p == null) throw new Exception("Could not start local PTY.");
                fd=(int)p[0]; pid=(int)p[1]; starting=false; status("Running locally");
                byte[] buf=new byte[8192]; int n; while ((n=LocalPty.read(fd,buf)) > 0) { String data=Base64.encodeToString(buf,0,n,Base64.NO_WRAP); runOnUiThread(() -> terminal.evaluateJavascript("receive('"+data+"')",null)); }
                int oldFd=fd, oldPid=pid; fd=-1; pid=-1; int exit=LocalPty.finish(oldFd,oldPid); status("Stopped (status " + exit + ")");
            } catch (Exception ex) { starting=false; status("Start failed"); show("jcode could not start", String.valueOf(ex.getMessage())); }
        },"jcode-pty").start();
    }
    private void writeCertificates() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidCAStore"); store.load(null);
        try (FileOutputStream out=new FileOutputStream(caFile)) {
            Enumeration<String> aliases=store.aliases(); int count=0;
            while (aliases.hasMoreElements()) { Certificate cert=store.getCertificate(aliases.nextElement()); if (cert == null) continue;
                out.write("-----BEGIN CERTIFICATE-----\n".getBytes(StandardCharsets.US_ASCII));
                out.write(Base64.encode(cert.getEncoded(),Base64.NO_WRAP)); out.write("\n-----END CERTIFICATE-----\n".getBytes(StandardCharsets.US_ASCII)); count++;
            }
            if (count==0) throw new Exception("Android trust store is empty");
        }
    }
    private void stop() { int current=pid; if (current > 0) LocalPty.stop(current); }
    private void send(String s) { int current=fd; if (current < 0) return; writes.execute(() -> { if (fd == current) LocalPty.write(current,s.getBytes(StandardCharsets.UTF_8)); }); }
    private class Bridge {
        @JavascriptInterface public void send(String s) { MainActivity.this.send(s); }
        @JavascriptInterface public void resize(int c,int r) { if(c<1 || r<1 || c>1000 || r>1000) return; cols=c; rows=r; int current=fd; if(current>=0) LocalPty.resize(current,c,r); }
    }
    private void importZip() {
        if (fd >= 0 || starting) { show("Stop jcode first", "Importing changes the workspace. Stop jcode before importing."); return; }
        new AlertDialog.Builder(this).setTitle("Import into workspace?").setMessage("ZIP files overwrite matching workspace files. Maximum 100 MB of extracted data. Only import files you trust.").setNegativeButton("Cancel",null).setPositiveButton("Select ZIP",(d,w) -> {Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT); i.setType("application/zip"); i.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(i,IMPORT);}).show();
    }
    private void exportZip() { Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT); i.setType("application/zip"); i.addCategory(Intent.CATEGORY_OPENABLE); i.putExtra(Intent.EXTRA_TITLE,"jcode-workspace.zip"); startActivityForResult(i,EXPORT); }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data); if(result!=RESULT_OK || data==null || data.getData()==null) return;
        new Thread(() -> { try {
            if(request==IMPORT) { if(fd>=0 || starting) throw new Exception("Stop jcode first"); try(InputStream in=getContentResolver().openInputStream(data.getData()); ZipInputStream zip=new ZipInputStream(in)) { unzip(zip); } show("Import complete","Files are in the private jcode workspace."); }
            else if(request==EXPORT) { try(OutputStream out=getContentResolver().openOutputStream(data.getData()); ZipOutputStream zip=new ZipOutputStream(out)) { zipDirectory(zip,workspace,""); } show("Export complete","The workspace ZIP was saved."); }
        } catch(Exception e) { show("Workspace operation failed",String.valueOf(e.getMessage())); } },"workspace-io").start();
    }
    private void unzip(ZipInputStream zip) throws Exception {
        String root=workspace.getCanonicalPath()+File.separator; ZipEntry entry; byte[] buf=new byte[8192]; long total=0; int entries=0;
        while((entry=zip.getNextEntry())!=null) { if(++entries>10000) throw new Exception("Too many ZIP entries"); File target=new File(workspace,entry.getName()); if(!target.getCanonicalPath().startsWith(root)) throw new Exception("Unsafe ZIP path");
            if(entry.isDirectory()) { if(!target.isDirectory() && !target.mkdirs()) throw new Exception("Could not create directory"); }
            else { File parent=target.getParentFile(); if(!parent.isDirectory() && !parent.mkdirs()) throw new Exception("Could not create directory"); try(FileOutputStream out=new FileOutputStream(target)) { int n; while((n=zip.read(buf))!=-1) { total+=n; if(total>MAX_IMPORT) throw new Exception("ZIP exceeds size limit"); out.write(buf,0,n); } } }
            zip.closeEntry();
        }
    }
    private void zipDirectory(ZipOutputStream zip,File dir,String path) throws Exception {
        File[] files=dir.listFiles(); if(files==null) return; byte[] buf=new byte[8192];
        for(File f:files) { if(java.nio.file.Files.isSymbolicLink(f.toPath())) continue; String name=path+f.getName(); if(f.isDirectory()) zipDirectory(zip,f,name+"/"); else if(f.isFile()) { zip.putNextEntry(new ZipEntry(name)); try(InputStream in=new java.io.FileInputStream(f)) { int n; while((n=in.read(buf))!=-1) zip.write(buf,0,n); } zip.closeEntry(); } }
    }
    @Override protected void onDestroy() { stop(); writes.shutdownNow(); terminal.removeJavascriptInterface("Android"); terminal.destroy(); super.onDestroy(); }
}
