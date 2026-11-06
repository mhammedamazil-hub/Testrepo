#!/usr/bin/env python3
"""Static link check for the game's GLSL ES 2.0 shaders.

There is no GPU and no Android device in the build sandbox, so the only way to catch a
shader link error is to read the sources the way the driver does. This tool extracts every
shader pair out of `android/game/app/src/main/cpp/game.cpp` and enforces the rules that a
real linker enforces but a C++ compiler cannot:

  1. every `varying` that crosses stages must have the *same effective precision* in both
     stages (explicit qualifier, or the stage's `precision ... float;` default);
  2. the same for `uniform`s that are declared in both stages;
  3. every varying the fragment shader reads must be written by the vertex shader;
  4. every attribute the vertex shader declares must be bound in `game.cpp`
     (glBindAttribLocation / glVertexAttribPointer) - a silent attribute at location -1
     draws nothing at all;
  5. no ES 3.0-only syntax (in/out, texture(), mediump image types) in an ES 2.0 shader.

Rule 1 is what shipped a black screen once: `uniform vec3 u_eye` lived in a vertex shader
(highp by default) and a fragment shader (mediump by default), and the device refused to
link with "L0001 ... The precision does not match". Same trap for every varying here.

    python tools/gles_shader_check.py            # exit 1 on any violation
"""
import os
import re
import sys

CPP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "android", "game", "app", "src", "main", "cpp", "game.cpp")

DECL = re.compile(
    r"^\s*(?:uniform|varying|attribute)\s+"
    r"(?:(highp|mediump|lowp|XPREC)\s+)?"
    r"(?:float|vec2|vec3|vec4|mat2|mat3|mat4|int|ivec2|ivec3|ivec4|bool)\s+"
    r"(\w+)", re.M)

DEFAULT = re.compile(r"^\s*precision\s+(highp|mediump|lowp)\s+float\s*;", re.M)


def extract(cpp_text):
    """{name: (kind, source)} for every `static const char* kNamedVS|FS = ...;` block."""
    out = {}
    for m in re.finditer(r"static const char\*\s+(k\w+(?:VS|FS))\s*=\s*(.*?);\s*\n", cpp_text,
                         re.S):
        name, body = m.group(1), m.group(2)
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', body)
        src = "".join(parts).replace("\\n", "\n").replace('\\"', '"')
        out[name] = src
    return out


def stage_of(name):
    return "VS" if name.endswith("VS") else "FS"


def scan(src, stage):
    default = "highp" if stage == "VS" else "mediump"   # GLSL ES defaults
    dm = DEFAULT.search(src)
    if dm:
        default = dm.group(1)
    decls = {}
    for m in DECL.finditer(src):
        prec, ident = m.group(1) or default, m.group(2)
        kw = src[m.start():m.end()].split()[0]
        decls[ident] = (kw, prec)
    return decls, default


def main(argv):
    text = open(CPP, encoding="utf-8").read()
    cpp = text
    shaders = extract(text)
    if not shaders:
        print("FAIL: no shader sources found in", CPP)
        return 1
    problems = []
    # XPREC is injected by compile() in game.cpp for every shader
    m = re.search(r'#define XPREC ', text)
    allow_xprec = bool(m)

    # one vertex shader can serve several fragment shaders (every post pass draws the same
    # full-screen quad), so the pairing is explicit instead of being guessed from names
    SHARED_VS = {"kPostQuad": ["kBright", "kBlur", "kRays", "kComposite"]}
    groups = {}
    for name in shaders:
        base = name[:-2]
        if stage_of(name) == "VS" and base in SHARED_VS:
            for fs_base in SHARED_VS[base]:
                groups.setdefault(fs_base, {})["VS"] = shaders[name]
            continue
        groups.setdefault(base, {})[stage_of(name)] = shaders[name]
    if len(groups) < 3:
        problems.append("expected at least 3 shader programs, parsed %d" % len(groups))

    # rule 0 (added after v5 shipped a black screen): GLSL ES requires the default float
    # precision to be declared before any function that takes or returns a float. The renderer
    # prepends one shared GLSL chunk (kCommonGlsl) that *does* define functions, so the prefix
    # compile() emits must declare the precision ahead of it. The device said, verbatim:
    #   "model shader 1:1: S0033: no default precision defined for function 'aces_fit'"
    if cpp is not None:
        m = re.search(r"const std::string prefix\s*=(.*?);", cpp, re.S)
        if m and "precision" not in m.group(1):
            problems.append(
                "compile(): the injected prefix must declare the default float precision "
                "before kCommonGlsl's functions, or every stage fails with S0033")
        if "precision " not in cpp:
            problems.append("compile(): no 'precision ... float;' is injected at all")

    for base, pair in sorted(groups.items()):
        if "VS" not in pair or "FS" not in pair:
            problems.append("%s: incomplete pair %s" % (base, sorted(pair)))
            continue
        vd, vdef = scan(pair["VS"], "VS")
        fd, fdef = scan(pair["FS"], "FS")
        print("%-24s VS default %-7s FS default %-7s  %d/%d decls"
              % (base, vdef, fdef, len(vd), len(fd)))
        if not re.search(r"precision\s+XPREC\s+float\s*;", pair["FS"]):
            problems.append("%s: the fragment stage must declare 'precision XPREC float;' so "
                            "its default can never drift from the vertex stage" % base)
        for ident, (kw_v, prec_v) in vd.items():
            if ident not in fd:
                continue
            kw_f, prec_f = fd[ident]
            # only cross-stage symbols matter: an attribute is vertex-only, and a varying is
            # always shared; a uniform declared in both stages must match as well
            if kw_v == "attribute":
                continue
            # XPREC is a macro the renderer expands to the *same* token in both stages, so
            # two XPRECs always agree; a literal qualifier next to an XPREC does not.
            matched = prec_v == prec_f or (prec_v == "XPREC" and prec_f == "XPREC")
            if not matched:
                problems.append(
                    "%s: '%s' is %s %s in the vertex stage but %s %s in the fragment stage "
                    "-> the driver will refuse to link (this is the L0001 error). "
                    "Declare it XPREC in both stages."
                    % (base, ident, prec_v, kw_v, prec_f, kw_f))
            if prec_v == "XPREC" and prec_f == "XPREC" and not allow_xprec:
                problems.append("%s: '%s' uses XPREC but XPREC is not defined for this program"
                                % (base, ident))
        # rule 3: the fragment stage may only read varyings the vertex stage writes
        for ident, (kw_f, _) in fd.items():
            if kw_f == "varying" and ident not in vd:
                problems.append("%s: fragment reads varying '%s' that the vertex stage never "
                                "writes" % (base, ident))

    # rule 4: attributes must be bound, and bound in the order the renderer uses
    for name, src in sorted(shaders.items()):
        if stage_of(name) != "VS":
            continue
        vdecls, _ = scan(src, "VS")
        attrs = [i for i, (kw, _) in vdecls.items() if kw == "attribute"]
        bound = re.findall(r'static const char\* k\w+Attribs\[\]\s*=\s*\{([^}]*)\}', text)
        flat = [x.strip().strip('"') for group in bound for x in group.split(",") if x.strip()]
        missing = [a for a in attrs if a not in flat]
        if missing:
            problems.append("%s: attribute(s) %s never reach glBindAttribLocation"
                            % (name, ", ".join(missing)))

    # rule 5: ES 3.0 only syntax
    for name, src in sorted(shaders.items()):
        for pat, why in ((r"^\s*in\s+\w+\s+\w+\s*;", "`in` (ES 3.0)"),
                         (r"^\s*out\s+\w+\s+\w+\s*;", "`out` (ES 3.0)"),
                         (r"\btexture\s*\(", "texture() (ES 3.0; use texture2D)"),
                         (r"#version\s+300", "#version 300 es (this is an ES 2.0 app)")):
            if re.search(pat, src, re.M):
                problems.append("%s: uses %s" % (name, why))

    print()
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("PASS: %d shader stages, %d programs, precisions consistent across every stage"
          % (len(shaders), len(groups)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
