#!/usr/bin/env python3
"""Apply minimal, verified Android substitutions to the pinned upstream checkout.

These are build-time patches only; the submodule stays at its upstream commit.
Android has /system/bin/sh instead of bash. This permits simple shell commands;
it does not provide bash, git, a compiler, or a full Linux distribution.
"""
from pathlib import Path

p = Path('vendor/jcode/crates/jcode-app-core/src/tool/bash.rs')
s = p.read_text()
changes = {
    'TokioCommand::new("bash")': 'TokioCommand::new(if cfg!(target_os = "android") { "/system/bin/sh" } else { "bash" })',
    'StdCommand::new("bash")': 'StdCommand::new(if cfg!(target_os = "android") { "/system/bin/sh" } else { "bash" })',
}
for old, new in changes.items():
    if s.count(old) != 1:
        raise SystemExit(f'upstream changed: expected exactly one {old}')
    s = s.replace(old, new)
p.write_text(s)
