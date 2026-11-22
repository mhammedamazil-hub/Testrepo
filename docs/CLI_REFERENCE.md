# CLI_REFERENCE — Universal Game Engine

## Invocation
```
python -m universal_engine <COMMAND> [ARGS] [--json] [--help]
```
Also available as the `universal-engine` entry point once installed (`pip install -e .`).

## Global options
- `--json`  Emit machine-readable JSON output instead of human-readable text.
- `--help`  Show help for a command or the top-level CLI.
- `--version` Show the platform version.

## Command structure (designed; partially scaffolded)

### Project
```
universal-engine project create <name> [--template TEMPLATE] [--json]
universal-engine project inspect [--json]
universal-engine project validate [--json]
universal-engine project config [--get KEY | --set KEY=VALUE] [--json]
```

### Blender (BLOCKED — Blender not installed)
```
universal-engine blender launch [--headless]
universal-engine blender scene create
universal-engine blender scene inspect
universal-engine blender object create
universal-engine blender mesh generate
universal-engine blender material create
universal-engine blender render
```

### Scene
```
universal-engine scene create [--name NAME] [--json]
universal-engine scene inspect [--json]
universal-engine scene modify [--json]
universal-engine scene validate [--json]
```

### Asset
```
universal-engine asset import <file> [--json]
universal-engine asset inspect <file> [--json]
universal-engine asset optimize <file> [--json]
universal-engine asset convert <in> <out> [--json]
```

### Physics
```
universal-engine physics configure [--json]
universal-engine physics simulate [--json]
universal-engine physics test [--json]
universal-engine physics benchmark [--json]
```

### Script
```
universal-engine script create <name> [--json]
universal-engine script validate <file> [--json]
universal-engine script run <file> [--json]
```

### Game
```
universal-engine game run [--json]
universal-engine game stop [--json]
universal-engine game test [--json]
```

### Preview
```
universal-engine preview capture [--json]
universal-engine preview inspect [--json]
```

### Performance
```
universal-engine performance profile [--json]
```

### Build
```
universal-engine build [--platform linux|android|desktop|web] [--json]
```

## Output conventions
- Human-readable by default; `--json` produces a JSON object with at least: `ok` (bool), `code` (str), `data` (object or null), `error` (object or null), `warnings` (array).
- Exit codes: 0 = success, non-zero = failure (1 = general error, 2 = validation error, 3 = not implemented / unavailable, 4 = backend missing).
- Errors are machine-readable; never hide a failing operation behind a fake success.

## Status of commands
All commands listed above are PLANNED. Only `--help`, `--version`, and argument parsing are implemented in the scaffold. No command performs a real backend operation yet.
