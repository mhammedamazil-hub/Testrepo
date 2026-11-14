# Crafting App CLI probe

runner: Linux 7.0.0-1019-azure x86_64

## photocraft — storytold/photocraft @ v0.23.1
total 134M
-rw-r--r-- 1 runner runner 134M Nov 14 07:05 photocraft-0.23.1-linux-x86_64.tar.gz
```
.
./photocraft-0.23.1-linux-x86_64
./photocraft-0.23.1-linux-x86_64/share
./photocraft-0.23.1-linux-x86_64/share/metainfo
./photocraft-0.23.1-linux-x86_64/share/zsh
./photocraft-0.23.1-linux-x86_64/share/man
./photocraft-0.23.1-linux-x86_64/share/icons
./photocraft-0.23.1-linux-x86_64/share/applications
./photocraft-0.23.1-linux-x86_64/share/mime
./photocraft-0.23.1-linux-x86_64/share/doc
./photocraft-0.23.1-linux-x86_64/share/bash-completion
./photocraft-0.23.1-linux-x86_64/share/fish
./photocraft-0.23.1-linux-x86_64/bin
./photocraft-0.23.1-linux-x86_64/bin/photocraft
./photocraft-0.23.1-linux-x86_64/bin/photocraft-cli
./photocraft-0.23.1-linux-x86_64.tar.gz

### ./photocraft-0.23.1-linux-x86_64/bin/photocraft
```
photocraft 0.23.1 (45066c482, 2026-11-12)
Opens PhotoCraft with the given files

Usage: photocraft [OPTIONS] [FILES]...

Arguments:
  [FILES]...  Files to open. On Windows and Linux they open as new tabs in the PhotoCraft already running. Put `--` before a name that starts with `-`

Options:
      --safe-gpu                        Start with the CPU renderer for this launch (after a graphics driver crash)
      --in-window-menus                 macOS: keep the menus inside the window instead of the menu bar (the variable: 0, false, no or off is off; empty is unset) [env: PHOTOCRAFT_IN_WINDOW_MENUS=]
      --new-instance                    Windows and Linux: start a separate PhotoCraft instead of opening the files in the one already running
      --present-mode <MODE>             How frames reach the display: fifo, autovsync or novsync (also immediate or mailbox). Without it, PHOTOCRAFT_PRESENT_MODE
      --frame-latency <1-3>             Frames queued for the display, 1 to 3. Without it, PHOTOCRAFT_FRAME_LATENCY
      --stroke-trace <stderr|FILE.csv>  Time each brush stroke's frames: stderr prints a summary per stroke, a CSV file path also records every frame. Without it, PHOTOCRAFT_STROKE_TRACE
      --control <PORT>                  Start the localhost JSON-lines control server on this port [env: PHOTOCRAFT_CONTROL_PORT=]
      --control-token <64-HEX>          The control token (64 hex digits) [env: PHOTOCRAFT_CONTROL_TOKEN]
      --control-token-file <PATH>       A file holding the control token, used instead of --control-token (a server creates it when missing) [env: PHOTOCRAFT_CONTROL_TOKEN_FILE=]
      --automation-read-root <DIR>      Ordered folders automation may read from; repeat for more roots (none without it) [env: PHOTOCRAFT_AUTOMATION_READ_ROOT=]
      --automation-write-root <DIR>     The folder automation may write to (none without it) [env: PHOTOCRAFT_AUTOMATION_WRITE_ROOT=]
  -h, --help                            Print help
  -V, --version                         Print version

Environment: PHOTOCRAFT_NEW_INSTANCE (anything but 0 or empty: as --new-instance), PHOTOCRAFT_CONFIG_DIR (the settings folder)
```

### ./photocraft-0.23.1-linux-x86_64/bin/photocraft-cli
```
photocraft-cli 0.23.1 (45066c482, 2026-11-12)
photocraft-cli: headless PhotoCraft

Usage: photocraft-cli <COMMAND>

Commands:
  convert   Convert between formats (.pcraft, .psd, .png, .jpg, .tif, .webp, .exr, …)
  info      Print the document as JSON (size, mode, depth, layer tree)
  run       Open a file (or start a new document), run engine commands in order, save the result
  batch     Apply an action list to every image in a directory
  droplet   Run a droplet (File › Automate › Create Droplet) on images and folders
  commands  List the engine command registry
  mcp       Run the MCP server on stdio (headless engine, or bridge to a running `photocraft --control <port>`)
  serve     Keep one headless session open and answer JSON lines on stdio, or on 127.0.0.1:<PORT>
  help      Print this message or the help of the given subcommand(s)

Options:
  -h, --help     Print help
  -V, --version  Print version
```

## gridcraft — storytold/gridcraft @ v0.19.1
total 51M
-rw-r--r-- 1 runner runner 51M Nov 14 07:05 gridcraft-0.19.1-linux-x86_64.tar.gz
```
.
./gridcraft-0.19.1-linux-x86_64.tar.gz
./gridcraft-0.19.1-linux-x86_64
./gridcraft-0.19.1-linux-x86_64/share
./gridcraft-0.19.1-linux-x86_64/share/metainfo
./gridcraft-0.19.1-linux-x86_64/share/icons
./gridcraft-0.19.1-linux-x86_64/share/applications
./gridcraft-0.19.1-linux-x86_64/share/mime
./gridcraft-0.19.1-linux-x86_64/share/doc
./gridcraft-0.19.1-linux-x86_64/bin
./gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli
./gridcraft-0.19.1-linux-x86_64/bin/gridcraft

### ./gridcraft-0.19.1-linux-x86_64/bin/gridcraft-cli
```
gridcraft-cli 0.19.1
usage:
  gridcraft-cli info <file> [--json]                      sheets, used ranges, tables, charts, names
  gridcraft-cli convert <in> <out> [--sheet NAME]         xlsx/csv/tsv/json/html/pdf by extension
  gridcraft-cli eval <formula> [--in FILE] [--sheet S] [--cell A1] [--json]
  gridcraft-cli cat <file> [--range A1:D20] [--sheet S] [--formulas] [--csv]
  gridcraft-cli check <file-or-dir>... [--json] [--tolerance 1e-9] [--max-report N]
                     cached-value calc oracle + XLSX round-trip fidelity (exit 1 on any difference)
  gridcraft-cli run [--in FILE | --sample NAME] [--cmd 'id={json}']... [--script FILE.jsonl]
                     [--out FILE] [--print RANGE] [--quiet]
                     a script line is id={json} or {"command": "id", "params": {…}};
                     blank lines and lines starting with # or // are skipped
  gridcraft-cli commands [--json] [--search X]
  gridcraft-cli functions [--json] [--search X] [--category C]
  gridcraft-cli mcp [--connect PORT] [--in FILE | --sample NAME]
  gridcraft-cli send <port> <method> [json]
  gridcraft-cli sandbox-check [--read PATH]... [--exec PATH]... [-- PROGRAM ARGS...]
                     whether this system confines programs (no program: a confined self-test)
  gridcraft-cli version
```

### ./gridcraft-0.19.1-linux-x86_64/bin/gridcraft
```
GridCraft 0.19.1
2026-11-14T07:05:27.279Z INFO  [main] gridcraft: GridCraft 0.19.1, log file /home/runner/.config/gridcraft/logs/gridcraft.log
Error: WinitEventLoop(Os(OsError { line: 777, file: "/home/runner/.cargo/git/checkouts/winit-0b02aa607dc0343f/a517b38/src/platform_impl/linux/mod.rs", error: Misc("neither WAYLAND_DISPLAY nor WAYLAND_SOCKET nor DISPLAY is set.") }))
```

## headless smoke
