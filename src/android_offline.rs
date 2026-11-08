//! Socket-free Android JNI: Java calls the Rust router in memory and runs GGUF inference.
use super::*;
use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use jni::{
    objects::{JClass, JString},
    sys::jstring,
    JNIEnv,
};
use std::{
    ffi::{c_char, CStr, CString},
    sync::OnceLock,
};
use tower::ServiceExt;
const TOKEN: &str = "local-android-session-no-network";
struct Embedded {
    runtime: tokio::runtime::Runtime,
    router: Router,
}
static EMBEDDED: OnceLock<Embedded> = OnceLock::new();
#[repr(C)]
struct SbMessage {
    role: *const c_char,
    content: *const c_char,
}
extern "C" {
    fn sb_load(path: *const c_char) -> i32;
    fn sb_loaded() -> bool;
    fn sb_cancel();
    fn sb_complete(messages: *const SbMessage, count: usize) -> *mut c_char;
    fn sb_error() -> *const c_char;
    fn sb_free(p: *mut c_char);
}
fn native_error() -> String {
    unsafe { CStr::from_ptr(sb_error()).to_string_lossy().into_owned() }
}
pub(super) async fn complete(messages: Vec<Value>) -> Result<String> {
    tokio::task::spawn_blocking(move || {
        let parts: Vec<_> = messages
            .iter()
            .map(|m| {
                Ok((
                    CString::new(m["role"].as_str().unwrap_or("user"))
                        .map_err(|_| bad("Invalid role"))?,
                    CString::new(m["content"].as_str().unwrap_or(""))
                        .map_err(|_| bad("Prompt contains NUL byte"))?,
                ))
            })
            .collect::<Result<Vec<_>>>()?;
        let raw: Vec<_> = parts
            .iter()
            .map(|(r, c)| SbMessage {
                role: r.as_ptr(),
                content: c.as_ptr(),
            })
            .collect();
        let result = unsafe { sb_complete(raw.as_ptr(), raw.len()) };
        if result.is_null() {
            return Err(bad(native_error()));
        }
        let text = unsafe { CStr::from_ptr(result).to_string_lossy().into_owned() };
        unsafe { sb_free(result) };
        Ok(text)
    })
    .await
    .map_err(internal)?
}
fn output(env: &JNIEnv, value: Value) -> jstring {
    env.new_string(value.to_string())
        .map(|s| s.into_raw())
        .unwrap_or(std::ptr::null_mut())
}
fn java_string(env: &mut JNIEnv, value: &JString) -> std::result::Result<String, String> {
    env.get_string(value)
        .map(Into::into)
        .map_err(|_| "Invalid JNI string".into())
}
#[no_mangle]
pub extern "system" fn Java_app_sourcebook_mobile_OfflineActivity_nativeInit(
    mut env: JNIEnv,
    _class: JClass,
    directory: JString,
) -> jstring {
    let result = (|| -> std::result::Result<Value, String> {
        let directory = java_string(&mut env, &directory)?;
        if EMBEDDED.get().is_none() {
            let runtime = tokio::runtime::Builder::new_multi_thread()
                .worker_threads(2)
                .enable_all()
                .build()
                .map_err(|e| e.to_string())?;
            let app = runtime
                .block_on(App::open(Config {
                    data: PathBuf::from(&directory).join("notebooks.json"),
                    token: TOKEN.into(),
                    base_url: "http://127.0.0.1:1/disabled".into(),
                    model: "On-device GGUF".into(),
                    api_key: String::new(),
                }))
                .map_err(|e| e.to_string())?;
            let _ = EMBEDDED.set(Embedded {
                runtime,
                router: router(app),
            });
        }
        let path = PathBuf::from(directory).join("model.gguf");
        let mut warning = String::new();
        if path.is_file() && !unsafe { sb_loaded() } {
            let path =
                CString::new(path.to_string_lossy().as_bytes()).map_err(|e| e.to_string())?;
            if unsafe { sb_load(path.as_ptr()) } != 0 {
                warning = native_error();
            }
        }
        Ok(json!({"ok":true,"model_loaded":unsafe{sb_loaded()},"warning":warning}))
    })();
    output(
        &env,
        result.unwrap_or_else(|e| json!({"ok":false,"error":e})),
    )
}
#[no_mangle]
pub extern "system" fn Java_app_sourcebook_mobile_OfflineActivity_nativeRequest(
    mut env: JNIEnv,
    _class: JClass,
    method: JString,
    path: JString,
    body: JString,
) -> jstring {
    let result = (|| -> std::result::Result<Value, String> {
        let method = java_string(&mut env, &method)?;
        let path = java_string(&mut env, &path)?;
        let body = java_string(&mut env, &body)?;
        if !path.starts_with("/api/") || path.len() > 2000 || body.len() > 16 * 1024 * 1024 {
            return Err("Invalid or oversized local request".into());
        }
        let embedded = EMBEDDED.get().ok_or("Rust core is not initialized")?;
        let request = Request::builder()
            .method(method.as_str())
            .uri(path)
            .header("authorization", format!("Bearer {TOKEN}"))
            .header("content-type", "application/json")
            .body(Body::from(body))
            .map_err(|e| e.to_string())?;
        embedded.runtime.block_on(async{
   let response=embedded.router.clone().oneshot(request).await.map_err(|e|e.to_string())?;
   let status=response.status().as_u16();let mime=response.headers().get("content-type").and_then(|v|v.to_str().ok()).unwrap_or("application/octet-stream").to_string();
   let bytes=response.into_body().collect().await.map_err(|e|e.to_string())?.to_bytes();
   Ok(json!({"status":status,"type":mime,"body":base64::engine::general_purpose::STANDARD.encode(bytes)}))
  })
    })();
    output(&env,result.unwrap_or_else(|e|json!({"status":500,"type":"application/json","body":base64::engine::general_purpose::STANDARD.encode(json!({"error":e}).to_string())})))
}
#[no_mangle]
pub extern "system" fn Java_app_sourcebook_mobile_OfflineActivity_nativeLoadModel(
    mut env: JNIEnv,
    _class: JClass,
    path: JString,
) -> jstring {
    let result = (|| -> std::result::Result<Value, String> {
        let path = java_string(&mut env, &path)?;
        let path = CString::new(path).map_err(|e| e.to_string())?;
        if unsafe { sb_load(path.as_ptr()) } != 0 {
            return Err(native_error());
        }
        Ok(json!({"ok":true}))
    })();
    output(
        &env,
        result.unwrap_or_else(|e| json!({"ok":false,"error":e})),
    )
}
#[no_mangle]
pub extern "system" fn Java_app_sourcebook_mobile_OfflineActivity_nativeCancel(
    _env: JNIEnv,
    _class: JClass,
) {
    unsafe { sb_cancel() }
}
