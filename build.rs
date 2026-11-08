fn main() {
    if std::env::var_os("CARGO_FEATURE_ANDROID_OFFLINE").is_none()
        || std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default() != "android"
    {
        return;
    }
    let path = std::env::var("SOURCEBOOK_NATIVE_LIBS")
        .expect("Set SOURCEBOOK_NATIVE_LIBS to the compiled llama.cpp archive directory");
    println!("cargo:rustc-link-search=native={path}");
    for lib in ["sourcebook_llama", "llama", "ggml", "ggml-cpu", "ggml-base"] {
        println!("cargo:rustc-link-lib=static:+whole-archive={lib}");
    }
    println!("cargo:rustc-link-lib=dylib=c++_shared");
    println!("cargo:rustc-link-lib=log");
    println!("cargo:rustc-link-lib=android");
    println!("cargo:rustc-link-lib=dl");
    println!("cargo:rerun-if-env-changed=SOURCEBOOK_NATIVE_LIBS");
}
