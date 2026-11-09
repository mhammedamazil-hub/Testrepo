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

/** Offline Android host for the in-process Rust core and CPU GGUF inference. */
public class OfflineActivity extends Activity {
    private static final int PICK_FILE = 10, SAVE_FILE = 11, PICK_MODEL = 12, PICK_VIDEO = 13;
    private static native String nativeInit(String directory);
    private static native String nativeRequest(String method,String path,String body);
    private static native String nativeLoadModel(String path);
    private static native void nativeCancel();
    private volatile boolean modelLoaded;
    private volatile boolean importing;
    private volatile boolean videoBusy;
    private String videoNotebook, videoTitle;
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
        super.onCreate(state); WebView.setWebContentsDebuggingEnabled(false); newRoot();
        TextView loading=new TextView(this);loading.setText("Starting the Rust core on this phone…");loading.setPadding(dp(25),dp(50),dp(25),0);root.addView(loading);
        io.execute(()->{try{System.loadLibrary("sourcebook");org.json.JSONObject result=new org.json.JSONObject(nativeInit(getFilesDir().getAbsolutePath()));if(!result.optBoolean("ok"))throw new Exception(result.optString("error"));modelLoaded=result.optBoolean("model_loaded");runOnUiThread(()->{connect(URI.create("https://sourcebook.offline/"));String warning=result.optString("warning");if(!warning.isEmpty())notice(warning);if(!modelLoaded)notice("Storage is ready. Add an API provider in Settings; local weights are optional.");});}catch(Throwable e){runOnUiThread(()->{loading.setText("Could not initialize the embedded Rust core: "+e.getMessage());});}});
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
    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    private void connect(URI address) {
        destroyBrowser(); origin = address; newRoot();
        web = new WebView(this); WebSettings settings = web.getSettings(); settings.setJavaScriptEnabled(true); settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false); settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW); settings.setSafeBrowsingEnabled(false);
        settings.setSupportMultipleWindows(false); settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setMediaPlaybackRequiresUserGesture(true); settings.setBuiltInZoomControls(false);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web,false);
        web.addJavascriptInterface(new NativeBridge(),"SourcebookAndroid");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req) {
                String url=req.getUrl().toString();
                if(OriginPolicy.sameOrigin(origin,url))return false;
                notice("External navigation is disabled inside this workspace. Import a URL as a source instead.");
                return true;
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest req) {
                if(!OriginPolicy.sameOrigin(origin,req.getUrl().toString()))return blocked();
                String path=req.getUrl().getPath();if("/".equals(path))path="/index.html";
                String mime="/index.html".equals(path)?"text/html":"/style.css".equals(path)?"text/css":("/app.js".equals(path)||"/offline.js".equals(path))?"text/javascript":null;
                if(mime==null)return blocked();
                try{return new WebResourceResponse(mime,"UTF-8",getAssets().open("web"+path));}catch(Exception e){return blocked();}
            }
            @Override public void onReceivedSslError(WebView view,SslErrorHandler handler,SslError error) { handler.cancel(); notice("TLS certificate error. Use a server with a valid HTTPS certificate."); }
            @Override public void onReceivedError(WebView view,WebResourceRequest request,WebResourceError error) {
                if(request.isForMainFrame()) notice("Could not load packaged app assets. Restart the app.");
            }
            @Override public boolean onRenderProcessGone(WebView view,RenderProcessGoneDetail detail) { destroyBrowser();connect(URI.create("https://sourcebook.offline/"));notice("Renderer restarted; notebooks are still stored locally.");return true; }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params) {
                if(fileCallback!=null)fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);pick.setType("*/*");pick.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,params.getMode()==FileChooserParams.MODE_OPEN_MULTIPLE);
                try{startActivityForResult(pick,PICK_FILE);}catch(Exception e){fileCallback.onReceiveValue(null);fileCallback=null;notice("No file picker available");}return true;
            }
            @Override public boolean onJsAlert(WebView view,String url,String message,JsResult result){new AlertDialog.Builder(OfflineActivity.this).setMessage(message).setPositiveButton("OK",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;}
            @Override public boolean onJsConfirm(WebView view,String url,String message,JsResult result){new AlertDialog.Builder(OfflineActivity.this).setMessage(message).setNegativeButton("Cancel",(d,w)->result.cancel()).setPositiveButton("OK",(d,w)->result.confirm()).setOnCancelListener(d->result.cancel()).show();return true;}
        });
        web.setDownloadListener((url,agent,disposition,mime,length)->notice("Use the document export buttons in this offline interface."));
        root.addView(web,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,0,1));web.loadUrl(address.toString());
    }
    private boolean trustedPage() { return web!=null && OriginPolicy.sameOrigin(origin,web.getUrl()); }
    private void notice(String text) { runOnUiThread(()->Toast.makeText(this,text,Toast.LENGTH_LONG).show()); }
    private WebResourceResponse blocked(){return new WebResourceResponse("text/plain","UTF-8",403,"Network disabled",null,new ByteArrayInputStream(new byte[0]));}
    private void modelDialog(){
        new AlertDialog.Builder(this).setTitle(modelLoaded?"Optional local model loaded":"Optional local AI")
        .setMessage("Choose a decoder-only text-instruct .gguf file you already downloaded. The model is copied into this app's private storage and used by llama.cpp through Rust. This optional engine needs GGUF weights; API providers do not. No local server is used. Start with a small 0.5B–1.5B Q4 model; larger models can exceed your phone's RAM. CPU inference may be slow. Import replaces the current model.\n\nOffline speech/transcription are not included. Direct APIs and website imports require Internet. yt-dlp/FFmpeg are not bundled.")
        .setNegativeButton("Close",null).setPositiveButton("Choose GGUF",(d,w)->{if(importing){notice("Model import already in progress");return;}Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);pick.setType("*/*");try{startActivityForResult(pick,PICK_MODEL);}catch(Exception e){notice("No file picker available");}}).show();
    }
    private void importModel(Uri uri){
        importing=true;notice("Copying and loading model. Keep the app open; this may take a few minutes.");getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        io.execute(()->{
            java.io.File temp=new java.io.File(getFilesDir(),"model-import-"+java.util.UUID.randomUUID()+".partial");
            try(java.io.InputStream input=getContentResolver().openInputStream(uri);java.io.FileOutputStream output=new java.io.FileOutputStream(temp)){
                if(input==null)throw new java.io.IOException("Cannot open selected file");
                byte[] magic=new byte[4];int read=0;while(read<4){int n=input.read(magic,read,4-read);if(n<0)break;read+=n;}
                if(read!=4||magic[0]!='G'||magic[1]!='G'||magic[2]!='U'||magic[3]!='F')throw new java.io.IOException("Not a GGUF model");
                output.write(magic);long total=4;long limit=Math.min(8L*1024*1024*1024,Math.max(0,getFilesDir().getUsableSpace()-64L*1024*1024));byte[] buffer=new byte[1024*1024];int n;
                while((n=input.read(buffer))!=-1){total+=n;if(total>limit)throw new java.io.IOException("Model exceeds available storage or 8 GB limit");output.write(buffer,0,n);}output.getFD().sync();
                org.json.JSONObject result=new org.json.JSONObject(nativeLoadModel(temp.getAbsolutePath()));if(!result.optBoolean("ok")){modelLoaded=false;throw new java.io.IOException(result.optString("error"));}
                java.nio.file.Files.move(temp.toPath(),new java.io.File(getFilesDir(),"model.gguf").toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING,java.nio.file.StandardCopyOption.ATOMIC_MOVE);modelLoaded=true;notice("GGUF loaded. Chat and study generation now run on your phone.");
                runOnUiThread(()->{if(web!=null)web.reload();});
            }catch(Exception e){temp.delete();notice("Model import failed: "+e.getMessage());}finally{importing=false;runOnUiThread(()->getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON));}
        });
    }
    public final class NativeBridge {
        @JavascriptInterface public boolean isOffline(){return true;}
        @JavascriptInterface public boolean networkEnabled(){return true;}
        @JavascriptInterface public void reloadWorkspace(){runOnUiThread(()->{if(trustedPage())web.reload();});}
        @JavascriptInterface public void openLocalAI(){runOnUiThread(()->{if(trustedPage())modelDialog();});}
        @JavascriptInterface public void cancelAI(){runOnUiThread(()->{if(trustedPage()){nativeCancel();notice("Local generation cancellation requested");}});}
        @JavascriptInterface public void setAppearance(boolean dark){runOnUiThread(()->{if(!trustedPage())return;int bg=dark?Color.rgb(22,24,23):Color.rgb(248,249,247);root.setBackgroundColor(bg);getWindow().setStatusBarColor(bg);getWindow().setNavigationBarColor(bg);root.setSystemUiVisibility(dark?0:android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);});}
        @JavascriptInterface public boolean modelLoaded(){return modelLoaded;}
        @JavascriptInterface public void request(String id,String method,String path,String body){
            if(id==null||!id.matches("[0-9]{1,10}")||body==null||body.length()>16*1024*1024)return;
            io.execute(()->{String reply;try{reply=nativeRequest(method,path,body);}catch(Throwable e){reply="{\"status\":500,\"type\":\"application/json\",\"body\":\"eyJlcnJvciI6Ik5hdGl2ZSByZXF1ZXN0IGZhaWxlZCJ9\"}";}final String payload=reply;runOnUiThread(()->{if(web!=null){for(int offset=0;offset<payload.length();offset+=48000){String chunk=payload.substring(offset,Math.min(offset+48000,payload.length()));web.evaluateJavascript("window.__sourcebookNativeChunk("+id+","+offset+","+payload.length()+","+org.json.JSONObject.quote(chunk)+")",null);}}});});
        }

        @JavascriptInterface public void chooseVideo(String notebook,String title){runOnUiThread(()->{
            if(!trustedPage())return;if(videoBusy){notice("A video is already being processed");return;}
            if(notebook==null||!notebook.matches("[a-fA-F0-9-]{36}")||title==null||title.trim().isEmpty()||title.length()>300){notice("Open a notebook and enter a video title first");return;}
            videoBusy=true;videoNotebook=notebook;videoTitle=title;
            Intent pick=new Intent(Intent.ACTION_OPEN_DOCUMENT);pick.addCategory(Intent.CATEGORY_OPENABLE);pick.setType("video/*");
            try{startActivityForResult(pick,PICK_VIDEO);}catch(Exception e){videoBusy=false;videoResult(false,"No video picker available","",notebook);}
        });}

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
                printWeb=new WebView(OfflineActivity.this);printWeb.getSettings().setJavaScriptEnabled(false);printWeb.getSettings().setAllowFileAccess(false);printWeb.getSettings().setAllowContentAccess(false);printWeb.getSettings().setBlockNetworkLoads(true);
                printWeb.setWebViewClient(new WebViewClient(){
                    @Override public void onPageFinished(WebView view,String url){PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);manager.print(OriginPolicy.filename(title),view.createPrintDocumentAdapter(OriginPolicy.filename(title)),new PrintAttributes.Builder().build());}
                });printWeb.loadDataWithBaseURL(null,html,"text/html","UTF-8",null);
            });
        }
    }
    private void videoResult(boolean ok,String message,String source,String notebook){
        runOnUiThread(()->{try{if(trustedPage()){org.json.JSONObject result=new org.json.JSONObject();result.put("ok",ok);result.put("message",message);result.put("source",source);result.put("notebook",notebook);web.evaluateJavascript("window.__sourcebookVideoResult&&window.__sourcebookVideoResult("+result.toString()+")",null);}}catch(Exception e){notice(message);}});
    }
    private void extractVideo(Uri uri,String notebook,String title){
        io.execute(()->{android.media.MediaMetadataRetriever reader=new android.media.MediaMetadataRetriever();
            try{
                if(!"content".equals(uri.getScheme()))throw new Exception("Choose a video with the Android document picker");
                reader.setDataSource(this,uri);String duration=reader.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_DURATION);long length=Long.parseLong(duration);if(length<=0)throw new Exception("Video duration unavailable");
                long window=Math.min(length,600000L);org.json.JSONArray frames=new org.json.JSONArray();
                int width=640,height=360;try{int w=Integer.parseInt(reader.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)),h=Integer.parseInt(reader.extractMetadata(android.media.MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT));if(w>0&&h>0){width=w>=h?640:Math.max(2,640*w/h);height=h>=w?640:Math.max(2,640*h/w);}}catch(Exception ignored){}
                for(int i=0;i<8;i++){
                    long millis=i*Math.max(0,window-1)/7;
                    android.graphics.Bitmap bitmap=reader.getScaledFrameAtTime(millis*1000,android.media.MediaMetadataRetriever.OPTION_CLOSEST_SYNC,width,height);
                    if(bitmap==null)continue;
                    java.io.ByteArrayOutputStream output=new java.io.ByteArrayOutputStream();bitmap.compress(android.graphics.Bitmap.CompressFormat.JPEG,72,output);bitmap.recycle();byte[] bytes=output.toByteArray();if(bytes.length>300000)throw new Exception("Video frame exceeds size limit");
                    org.json.JSONObject frame=new org.json.JSONObject();frame.put("seconds",millis/1000);frame.put("jpeg",Base64.encodeToString(bytes,Base64.NO_WRAP));frames.put(frame);
                }
                if(frames.length()==0)throw new Exception("Android could not decode this video. Try a standard MP4/H.264 file.");
                org.json.JSONObject body=new org.json.JSONObject();body.put("title",title);body.put("frames",frames);
                org.json.JSONObject reply=new org.json.JSONObject(nativeRequest("POST","/api/notebooks/"+notebook+"/video-frames",body.toString()));
                org.json.JSONObject payload=new org.json.JSONObject(new String(Base64.decode(reply.getString("body"),Base64.DEFAULT),java.nio.charset.StandardCharsets.UTF_8));
                if(reply.getInt("status")>=400)throw new Exception(payload.optString("error","Video analysis failed"));
                videoResult(true,"Sampled video frames analyzed. No audio was processed.",payload.getString("id"),notebook);
            }catch(Exception e){videoResult(false,e.getMessage()==null?"Video processing failed":e.getMessage(),"",notebook);}finally{try{reader.release();}catch(Exception ignored){}videoBusy=false;}
        });
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==PICK_VIDEO){final String notebook=videoNotebook,title=videoTitle;videoNotebook=null;videoTitle=null;if(result==RESULT_OK&&data!=null&&data.getData()!=null){notice("Sampling up to 8 frames locally, then sending them to your vision provider. No audio is analyzed.");extractVideo(data.getData(),notebook,title);}else{videoBusy=false;videoResult(false,"Video selection cancelled","",notebook);}}
        if(request==PICK_MODEL && result==RESULT_OK && data!=null && data.getData()!=null)importModel(data.getData());
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
