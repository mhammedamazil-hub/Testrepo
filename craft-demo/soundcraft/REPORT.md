# soundcraft v0.20.1 headless CLI
```
--- soundcraft-0.20.1-linux-x86_64.tar.gz ---
soundcraft-0.20.1-linux-x86_64/
soundcraft-0.20.1-linux-x86_64/share/
soundcraft-0.20.1-linux-x86_64/share/icons/
soundcraft-0.20.1-linux-x86_64/share/icons/hicolor/
soundcraft-0.20.1-linux-x86_64/share/icons/hicolor/48x48/
soundcraft-0.20.1-linux-x86_64/share/icons/hicolor/48x48/apps/
./soundcraft-0.20.1-linux-x86_64/bin/soundcraft
./soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli

### ./soundcraft-0.20.1-linux-x86_64/bin/soundcraft --version
soundcraft 0.20.1 (linux x86_64)
[exit 0]
### ./soundcraft-0.20.1-linux-x86_64/bin/soundcraft --help (trimmed)
Opens SoundCraft with the given files

Usage: soundcraft [OPTIONS] [FILES]...

Arguments:
  [FILES]...  Sessions, audio and MIDI files to open. Put `--` before a name that starts with `-`

Options:
      --demo            Start with the demo session [alias: --sample]
      --no-audio        Don't open an audio device
      --control <PORT>  Start the localhost JSON-lines control server on this port (0 picks a free port and prints it) [env: SOUNDCRAFT_CONTROL_PORT=]
  -h, --help            Print help
  -V, --version         Print version

Environment:
  SOUNDCRAFT_CONTROL_PORT     The --control fallback: a port or host:port, ignored for another host
  SOUNDCRAFT_CONFIG_DIR       The settings folder (ui.json, Autosave, Presets, logs); empty: none (unlike the others, where empty counts as unset)
  SOUNDCRAFT_NO_PREFS         1 doesn't read or write preferences and logs to stderr only; 0 or unset is off
  SOUNDCRAFT_NO_SYSTEM_FONTS  1 uses the built-in fonts only; 0 or unset is off
  SOUNDCRAFT_WAYLAND          Linux: 1 keeps the native Wayland backend instead of XWayland; 0 or unset is off
  RUST_LOG                    Log filter, env_logger style: debug, warn,soundcraft_mix=trace
  The on/off variables take 1/on/true/yes or 0/off/false/no, in any case; any other value is

### ./soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli --version
soundcraft-cli 0.20.1 (linux x86_64)
[exit 0]
### ./soundcraft-0.20.1-linux-x86_64/bin/soundcraft-cli --help (trimmed)
soundcraft-cli: SoundCraft without a window

Usage: soundcraft-cli <COMMAND>

Commands:
  info      Print an audio file's format as JSON, or a .scraft session's summary
  convert   Convert an audio file: resample, change the bit depth, normalize
  run       Run engine commands on a new, demo or saved session
  script    Run a file of engine commands, one `ID JSON` per line
  commands  List the engine commands
  describe  Print one engine command's details as JSON
  app       Call a running app's control channel
  mcp       Serve MCP on stdin and stdout
  parity    Print the parity report (markdown)
  plugins   List the built-in plugins
  help      Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```
