package app.sourcebook.mobile;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.util.Base64;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.*;
import android.widget.*;
import java.io.ByteArrayInputStream;
import java.io.OutputStream;
import java.net.URI;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Android shell; all notebook/AI business logic remains on the Rust server. */
public class MainActivity extends Activity {
    private static final int PICK_FILE = 10, SAVE_FILE = 11;
    private static final int MAX_EXPORT = 24 * 1024 * 1024;
    private volatile URI origin;
    private WebView web;
    private WebView printWeb;
    private LinearLayout root;
    private ValueCallback<Uri[]> fileCallback;
    private byte[] pendingExport;
    private boolean exporting;
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        WebView.setWebContentsDebuggingEnabled(false);
        String server = getPreferences(MODE_PRIVATE).getString("server", "");
        boolean http = getPreferences(MODE_PRIVATE).getBoolean("http", false);
        if (server.isEmpty()) connectionScreen(null); else {
            try { connect(OriginPolicy.server(server, http)); }
            catch (Exception e) { connectionScreen(e.getMessage()); }
        }
    }
    private int dp(int value) { return (int)(value * getResources().getDisplayMetrics().density + .5f); }
    private void newRoot() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(247,248,250));
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(), insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        setContentView(root); root.requestApplyInsets();
    }
    private void connectionScreen(String error) {
        destroyBrowser(); origin = null; newRoot();
        ScrollView scroll = new ScrollView(this);
        LinearLayout form = new LinearLayout(this); form.setOrientation(LinearLayout.VERTICAL); form.setPadding(dp(25),dp(42),dp(25),dp(30));
        TextView heading = new TextView(this); heading.setText("Sourcebook"); heading.setTextSize(32); heading.setTextColor(Color.rgb(39,99,75)); form.addView(heading);
        TextView help = new TextView(this); help.setText("Your research, in your pocket.\n\nConnect to your running Rust Sourcebook server. The APK does not contain a backend or an AI model. Enter your server access token on the next screen.\n\nOnly connect to a server you trust: its interface can request file saves and printing."); help.setTextSize(15); help.setPadding(0,dp(18),0,dp(24)); form.addView(help);
        EditText url = new EditText(this); url.setSingleLine(true); url.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_URI); url.setHint("https://your-sourcebook-server.com"); url.setText(getPreferences(MODE_PRIVATE).getString("server", "")); form.addView(url);
        CheckBox insecure = new CheckBox(this); insecure.setText("Allow unencrypted HTTP (trusted LAN/testing only)"); insecure.setChecked(getPreferences(MODE_PRIVATE).getBoolean("http",false)); form.addView(insecure);
        TextView warning = new TextView(this); warning.setText("Use HTTPS outside a trusted LAN. HTTP exposes your access token and source data. localhost on your phone is NOT your computer; use its LAN IP or a secure public address."); warning.setTextSize(12); warning.setPadding(0,dp(8),0,dp(15)); form.addView(warning);
        TextView errors = new TextView(this); errors.setTextColor(Color.rgb(170,60,45)); if (error != null) errors.setText(error); form.addView(errors);
        Button button = new Button(this); button.setText("Connect workspace"); button.setOnClickListener(v -> {
            try {
                URI address = OriginPolicy.server(url.getText().toString(),insecure.isChecked());
                getPreferences(MODE_PRIVATE).edit().putString("server",address.toString()).putBoolean("http",insecure.isChecked()).apply();
                connect(address);
            } catch (Exception e) { errors.setText(e.getMessage()); }
        }); form.addView(button);
        TextView privacy = new TextView(this); privacy.setText("No analytics. No broad storage, microphone, or camera permissions. Files are selected with the Android picker. AI keys stay on your server."); privacy.setTextSize(12); privacy.setPadding(0,dp(25),0,0); form.addView(privacy);
        scroll.addView(form); root.addView(scroll);
    }
    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    private void connect(URI address) {
        destroyBrowser(); origin = address; newRoot();
        LinearLayout toolbar = new LinearLayout(this); toolbar.setPadding(dp(8),0,dp(8),0); toolbar.setGravity(android.view.Gravity.CENTER_VERTICAL);
        TextView label = new TextView(this); label.setText(address.getHost()); label.setTextSize(12); label.setMaxLines(1); label.setEllipsize(android.text.TextUtils.TruncateAt.END); toolbar.addView(label,new LinearLayout.LayoutParams(0,dp(48),1));
        Button refresh = new Button(this); refresh.setText("Reload"); refresh.setOnClickListener(v -> {if(web!=null)web.reload();}); toolbar.addView(refresh);
        Button server = new Button(this); server.setText("Server"); server.setOnClickListener(v -> new AlertDialog.Builder(this).setTitle("Change server?").setMessage("This closes your current workspace and clears its browser session. Your server-side notebooks remain unchanged.").setNegativeButton("Cancel",null).setPositiveButton("Change",(d,w)->connectionScreen(null)).show()); toolbar.addView(server); root.addView(toolbar);
        web = new WebView(this); WebSettings settings = web.getSettings(); settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); settings.setSafeBrowsingEnabled(true);
        settings.setSupportMultipleWindows(false); settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setMediaPlaybackRequiresUserGesture(true); settings.setBuiltInZoomControls(false);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.addJavascriptInterface(new NativeBridge(),"SourcebookAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req) {
                String url=req.getUrl().toString();
                if(OriginPolicy.sameOrigin(origin,url))return false;
                if(req.hasGesture() && ("https".equals(req.getUrl().getScheme()) || "http".equals(req.getUrl().getScheme()))) {
                    new AlertDialog.Builder(MainActivity.this).setTitle("Open external website?").setMessage(req.getUrl().getHost()).setNegativeButton("Cancel",null).setPositiveButton("Open browser",(d,w)->{try{startActivity(new Intent(Intent.ACTION_VIEW,req.getUrl()));}catch(Exception e){notice("No browser available");}}).show();
                }
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest req) {
                String scheme=req.getUrl().getScheme();
                if ("http".equals(scheme)||"https".equals(scheme)) {
                    if (!OriginPolicy.sameOrigin(origin,req.getUrl().toString())) return new WebResourceResponse("text/plain","UTF-8",403,"External origin blocked",null,new ByteArrayInputStream(new byte[0]));
                }
                return super.shouldInterceptRequest(view,req);
            }
            @Override public void onReceivedSslError(WebView view,SslErrorHandler handler,SslError error) { handler.cancel(); notice("TLS certificate error. Use a server with a valid HTTPS certificate."); }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error) {
                if(request.isForMainFrame()) connectionScreen("Could not reach the server. Check the URL, network, firewall and whether the Rust server is running.");
            }
            @Override public boolean onRenderProcessGone(WebView view,RenderProcessGoneDetail detail) { connectionScreen("Android closed the web renderer. Reconnect to continue.");return true; }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params) {
                if(fileCallback!=null)fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);pick.setType("*/*");pick.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,params.getMode()==FileChooserParams.MODE_OPEN_MULTIPLE);
                try{startActivityForResult(pick,PICK_FILE);}catch(Exception e){fileCallback.onReceiveValue(null);fileCallback=null;notice("No file picker available");}return true;
            }
            @Override public boolean onJsAlert(WebView view,String url,String message,JsResult result){new AlertDialog.Builder(MainActivity.this).setMessage(message).setPositiveButton("OK",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;}
            @Override public boolean onJsConfirm(WebView view,String url,String message,JsResult result){new AlertDialog.Builder(MainActivity.this).setMessage(message).setNegativeButton("Cancel",(d,w)->result.cancel()).setPositiveButton("OK",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;}
        });
        web.setDownloadListener((url,agent,disposition,mime,length)->notice("Use the download buttons in the updated Sourcebook interface. Update the server if needed."));
        root.addView(web,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));web.loadUrl(address.toString());
    }
    private boolean trustedPage() { return web!=null && OriginPolicy.sameOrigin(origin,web.getUrl()); }
    private void notice(String text) { runOnUiThread(()->Toast.makeText(this,text,Toast.LENGTH_LONG).show()); }
    public final class NativeBridge {
        @JavascriptInterface public void saveFile(String filename,String mime,String base64) {
            if(base64==null || base64.length()>MAX_EXPORT*4/3+8){notice("Export exceeds the Android save limit (24 MB)");return;}
            runOnUiThread(()->{
                if(!trustedPage())return;
                if(exporting){notice("Finish the current save dialog first");return;}
                try {
                    byte[] bytes=Base64.decode(base64,Base64.DEFAULT);
                    if(bytes.length>MAX_EXPORT){notice("File too large");return;}
                    pendingExport=bytes;exporting=true;
                    Intent save=new Intent(Intent.ACTION_CREATE_DOCUMENT);save.addCategory(Intent.CATEGORY_OPENABLE);save.setType(mime!=null&&mime.matches("[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+")?mime:"application/octet-stream");save.putExtra(Intent.EXTRA_TITLE,OriginPolicy.filename(filename));startActivityForResult(save,SAVE_FILE);
                }catch(Exception e){pendingExport=null;exporting=false;notice("Could not open the save dialog");}
            });
        }
        @JavascriptInterface public void printDocument(String title,String html) {
            if(html==null||html.length()>4*1024*1024){notice("Print document too large");return;}
            runOnUiThread(()->{
                if(!trustedPage())return;
                if(printWeb!=null){printWeb.destroy();printWeb=null;}
                printWeb=new WebView(MainActivity.this);printWeb.getSettings().setJavaScriptEnabled(false);printWeb.getSettings().setAllowFileAccess(false);printWeb.getSettings().setAllowContentAccess(false);printWeb.getSettings().setBlockNetworkLoads(true);
                printWeb.setWebViewClient(new WebViewClient(){
                    @Override public void onPageFinished(WebView view,String url){PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);manager.print(OriginPolicy.filename(title),view.createPrintDocumentAdapter(OriginPolicy.filename(title)),new PrintAttributes.Builder().build());}
                });printWeb.loadDataWithBaseURL(null,html,"text/html","UTF-8",null);
            });
        }
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==PICK_FILE && fileCallback!=null){
            Uri[] chosen=null;
            if(result==RESULT_OK&&data!=null){if(data.getClipData()!=null){chosen=new Uri[data.getClipData().getItemCount()];for(int i=0;i<chosen.length;i++)chosen[i]=data.getClipData().getItemAt(i).getUri();}else if(data.getData()!=null)chosen=new Uri[]{data.getData()};}
            fileCallback.onReceiveValue(chosen);fileCallback=null;
        }
        if(request==SAVE_FILE){final byte[] bytes=pendingExport;pendingExport=null;exporting=false;if(result==RESULT_OK&&data!=null&&data.getData()!=null&&bytes!=null){final Uri destination=data.getData();io.execute(()->{try(OutputStream output=getContentResolver().openOutputStream(destination)){if(output==null)throw new java.io.IOException();output.write(bytes);notice("File saved");}catch(Exception e){notice("Could not save file");}});}}
    }
    @Override public void onBackPressed(){if(web!=null){web.evaluateJavascript("(function(){var m=document.querySelector('dialog[open]');if(m){m.close();return true;}var w=document.querySelector('#workspace');if(w&&!w.hidden&&!new URLSearchParams(location.search).has('share')){document.querySelector('#back').click();return true;}return false;})()",result->{if(!"true".equals(result)){if(web!=null&&web.canGoBack())web.goBack();else new AlertDialog.Builder(this).setMessage("Close Sourcebook?").setNegativeButton("Stay",null).setPositiveButton("Close",(d,w)->finish()).show();}});}else super.onBackPressed();}
    private void destroyBrowser(){if(fileCallback!=null){fileCallback.onReceiveValue(null);fileCallback=null;}if(web!=null){web.removeJavascriptInterface("SourcebookAndroid");web.stopLoading();web.clearHistory();web.destroy();web=null;}}
    @Override protected void onDestroy(){destroyBrowser();if(printWeb!=null){printWeb.destroy();printWeb=null;}pendingExport=null;io.shutdown();super.onDestroy();}
}
