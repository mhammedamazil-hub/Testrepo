# jcode for Android — experimental, not yet verified

This is an in-progress **on-device** Android port of [1jehuang/jcode](https://github.com/1jehuang/jcode), not an SSH client. `vendor/jcode` is the actual upstream Git repository, pinned as a submodule at `bc06755d155c2719b4cc7ac75fb0cbfeaaa9d209` (MIT). Clone with `git clone --recurse-submodules` or run `git submodule update --init --recursive`.

The earlier `tablet-agent-debug-apk` artifact was an unrelated SSH client. **Do not use it for this project.** The previous app has been replaced by an experimental local PTY frontend; this work is not yet verified on a tablet.

## Install and try

A first ARM64 debug APK was built by [this Actions run](https://github.com/mhammedamazil-hub/Testrepo/actions/runs/42659504625). Download `jcode-android-arm64-debug` from its artifacts, unzip it, then install `app-debug.apk`. If you previously installed the old SSH prototype, uninstall it first: this build has the same application ID but a different debug signing key. Uninstalling removes that app’s private files.

Open the app, optionally import a trusted project ZIP while stopped, then tap **Start** to launch the local jcode TUI. Use **Keyboard** to enter text and follow jcode’s provider setup. Stop jcode and use **Export ZIP** to save your workspace. The app-private workspace is not the tablet’s shared Downloads folder.

This is an experimental build: the compiler and packaging succeeded, but it has **not** been run on a Galaxy Tab A9, so startup and provider setup remain unverified.

## Architecture and limitations

The Actions build attempts to compile jcode for Android ARM64 using the Android NDK, package it in the app's native library directory, and run it locally under a pseudo-terminal. A private workspace supports ZIP import/export; the terminal has a keyboard and extra keys. It uses the Android CA store and an Internet connection to access model providers; you must configure a supported provider through jcode. No SSH server is required.

Android is not desktop Linux. The build substitutes Android's `/system/bin/sh` for bash in two upstream tool paths; this is not full Bash compatibility. The upstream desktop clipboard backend is unavailable; image clipboard and jcode-internal clipboard access are disabled (normal terminal text input remains). Git, compilers, Node, desktop tools and other agent CLIs are **not** bundled, and many jcode features may not work. Files in the private workspace are removed when the app is uninstalled. Import ZIPs only from trusted sources, and export your work regularly. The app and agent have access to private workspace files and can execute available device commands under the app's Android sandbox. AI provider accounts, network access and possible fees are separate requirements. This is not an offline model.

The intended artifact is an ARM64 debug APK for Android 8+; the Galaxy Tab A9 is ARM64. A successful compile alone does not establish that launch, model login, network access, tools, or terminal interactions work on that device. **Check the Actions run and real-device tests before relying on it.**

## Build

GitHub Actions checks out the pinned source, applies `scripts/patch-jcode-android.py`, cross-compiles jcode with Rust and NDK 27.2, and if successful builds an APK artifact named `jcode-android-arm64-debug`. The separate frontend check builds only the Android UI and PTY; it does not include jcode and its APK is not published. The Rust build currently disables the optional PDF and Bedrock features. The vendored xterm.js and fit addon licenses are in `app/src/main/assets`.
