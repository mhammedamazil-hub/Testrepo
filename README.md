# jcode for Android — work in progress

This repository is being changed from an unrelated SSH terminal into an **on-device port of jcode**. The earlier `tablet-agent-debug-apk` artifact was an SSH client, **not** jcode, and should not be used for this project.

`vendor/jcode` is the actual upstream [1jehuang/jcode](https://github.com/1jehuang/jcode) repository, pinned as a Git submodule (MIT license). Run `git submodule update --init --recursive` after cloning. Its current pin is `bc06755d155c2719b4cc7ac75fb0cbfeaaa9d209`.

## Current status

The GitHub Actions workflow currently attempts to cross-compile the real Rust jcode binary for Android ARM64. This is **not yet an installable jcode APK**. The previous Android module still contains the SSH prototype; it is not built by the current workflow and will need to be replaced by an on-device frontend. Android is not the same as Linux: running jcode requires an Android-compatible terminal/process integration, a working TLS certificate store, a local project workspace and a way to run the tools that jcode invokes. These need implementation and testing; merely compiling a Linux executable or wrapping a WebView would not satisfy the goal.

Build attempt: see Actions → Build jcode for Android. Android NDK 27.2, Rust with the `aarch64-linux-android` target, and the vendored OpenSSL feature are used. The Galaxy Tab A9 uses ARM64; an actual device test is needed before claiming compatibility.
