# Tablet Agent

An Android SSH terminal for using **jcode, Claude Code, OpenCode, and other CLI tools on a computer you control** from a Galaxy Tab A9 (or other Android 8+ tablet/phone). It is a remote client, not a port of jcode or an embedded AI model: the computer runs the agent, repository, shell, and tools. Internet/account/API charges and agent permissions depend on the tool you choose.

## Get the APK

1. Push this repository to GitHub. Open **Actions → Build Android APK** and choose a successful run (or run it with **Run workflow**).
2. Download the **tablet-agent-debug-apk** artifact, unzip it, and install `app-debug.apk` on the tablet. Android will ask you to allow installs from your browser/file manager. This is a debug-signed development build, not a Play Store release. GitHub artifacts expire after 30 days; build again if necessary.
3. The APK is universal (no ABI filter), with min Android API 26. The Galaxy Tab A9 ships with a newer Android version. Real-device testing is still recommended; display scaling, keyboard behaviour and OS battery policies vary.

## Connect

1. Install and configure an SSH server, your preferred agent(s), and any required authentication on a trusted Linux/macOS development computer. Keep the computer running and reachable from the tablet. Use a private LAN or trusted VPN; avoid exposing SSH directly to the public internet. Use a firewall and a strong SSH key.
2. For continuity install `tmux` on the host and start `tmux new -As coding` after connecting. A dropped connection then need not end the agent process. Reconnect and run that command again to reattach. The app itself does not keep sessions alive in the background.
3. Enter host, port and username. Select a private key with the document picker and optionally provide its passphrase, or enter an SSH password. No credentials are saved by the app. Password and passphrase fields are cleared when connecting; the selected key remains in memory until cleared or the activity is destroyed. Keyboard-interactive, agent forwarding, FIDO/hardware keys and SSH config files are not supported.
4. On first connection compare the displayed SHA256 fingerprint **and key type** using a trusted out-of-band channel, e.g. on the server run `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256` (use the corresponding host key file for the displayed type). Accept only if it matches. The app remembers the key for that host and port, and rejects a changed key. If you intentionally replace a server key, use **Forget host keys**, then verify again. This clears all remembered keys.
5. In the shell navigate to your project, then run `jcode`, `claude`, or `opencode`. The buttons send those commands to the **current** terminal after confirmation; use them only when the shell is ready. The shortcut row provides Esc, Tab, Ctrl-C and arrow keys. Tap Keyboard to bring up the soft keyboard.

SSH may require account and key setup on the server. There is no automatic jcode installation, no bundled agents, no file browser or direct API chat, and no automatic reconnect. Terminal compatibility is best-effort; some complex TUIs and mobile input methods may behave differently from a desktop terminal. Only connect to hosts and run agents you trust: agents can read and modify files and execute commands on that host.

## Research and upstream

The initial reference was [1jehuang/jcode](https://github.com/1jehuang/jcode), cloned and inspected at commit `bc06755d155c2719b4cc7ac75fb0cbfeaaa9d209` (MIT). It is a Rust terminal coding agent, not an Android app. There is another unrelated project called jcode; this project assumes the 1jehuang one. No upstream jcode code or binary is bundled; install it on the host following its documentation. The terminal uses [xterm.js 5.5.0](https://github.com/xtermjs/xterm.js) and its fit addon 0.10.0 (their MIT licenses are included in the assets), and [mwiede/jsch 0.2.21](https://github.com/mwiede/jsch) for SSH.

## Development

JDK 17, Android SDK platform 35 and Gradle 8.9 are required. Run `gradle testDebugUnitTest assembleDebug`. CI installs these prerequisites and uploads the APK. The JavaScript terminal assets are vendored; no external network requests are made by the terminal page. The SSH connection is end-to-end to the host and the app has no relay or telemetry.
