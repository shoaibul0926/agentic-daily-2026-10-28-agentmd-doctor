#!/usr/bin/env python3
"""agentmd-doctor: find AGENTS.md / CLAUDE.md shadowing, drift and broken imports."""
import argparse, json, os, re, sys

SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
IMPORT_RE = re.compile(r"(?<![\w`])@([\w./~-]+\.\w+|[\w./-]*/[\w./-]+)")
UNSUPPORTED = {"AGENTS.local.md", "AGENTS.override.md"}


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def imports(path):
    base = os.path.dirname(path)
    out = []
    for m in IMPORT_RE.finditer(strip_code(read(path))):
        t = m.group(1)
        if t.startswith("~"):
            continue
        out.append(os.path.normpath(os.path.join(base, t)))
    return out


def resolve_imports(path, seen=None, issues=None):
    """Return set of files transitively imported by path; record broken imports/cycles."""
    seen = seen if seen is not None else set()
    for t in imports(path):
        if not os.path.isfile(t):
            if issues is not None:
                issues.append(("error", "broken-import", path, f"imports missing file {t}"))
            continue
        if t in seen:
            if issues is not None and t == path:
                issues.append(("error", "import-cycle", path, "imports itself"))
            continue
        seen.add(t)
        resolve_imports(t, seen, issues)
    return seen


def norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def lines_set(path):
    return {norm(l) for l in read(path).splitlines() if len(norm(l)) > 20 and not l.lstrip().startswith("#")}


def scan(root):
    root = os.path.abspath(root)
    issues = []
    dirs = []
    for d, sub, files in os.walk(root):
        sub[:] = [s for s in sub if s not in SKIP]
        dirs.append((d, set(files)))
    for d, files in sorted(dirs):
        rel = os.path.relpath(d, root)
        loc = lambda f: os.path.normpath(os.path.join(rel, f))
        for f in files & UNSUPPORTED:
            issues.append(("warn", "unsupported-name", loc(f),
                           "Claude Code does not read this filename; rules in it are ignored"))
        has_a, has_c = "AGENTS.md" in files, "CLAUDE.md" in files
        if has_c:
            resolve_imports(os.path.join(d, "CLAUDE.md"), issues=(iss := []))
            issues += [(s, c, os.path.relpath(p, root), m) for s, c, p, m in iss]
        if has_a:
            resolve_imports(os.path.join(d, "AGENTS.md"), issues=(iss := []))
            issues += [(s, c, os.path.relpath(p, root), m) for s, c, p, m in iss]
        if has_a and has_c:
            a, c = os.path.join(d, "AGENTS.md"), os.path.join(d, "CLAUDE.md")
            if a in resolve_imports(c):
                continue  # single source of truth via @AGENTS.md
            la, lc = lines_set(a), lines_set(c)
            only_a = len(la - lc)
            shared = len(la & lc)
            if shared == 0:
                issues.append(("error", "shadowed-agents-md", loc("AGENTS.md"),
                               "CLAUDE.md exists without importing @AGENTS.md; in Claude Code's default mode "
                               "(claude-md-or-agents-md) AGENTS.md is silently skipped, Codex-style agents skip CLAUDE.md"))
            else:
                issues.append(("error", "drift", loc("AGENTS.md"),
                               f"{only_a} rule line(s) in AGENTS.md absent from CLAUDE.md ({shared} shared); "
                               "replace the duplicate with `@AGENTS.md` in CLAUDE.md"))
        elif has_a and rel != ".":
            parent = d
            while parent != root:
                parent = os.path.dirname(parent)
                if "CLAUDE.md" in os.listdir(parent) and "AGENTS.md" not in os.listdir(parent):
                    break
            else:
                parent = None
            if parent is not None:
                issues.append(("warn", "nested-agents-md", loc("AGENTS.md"),
                               "nested AGENTS.md is only loaded by Claude Code in claude-md-and-agents-md mode "
                               "(or via a SessionStart hook) when an ancestor has CLAUDE.md"))
    return issues


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures")
    a = p.parse_args(argv)
    issues = scan(a.path)
    if a.json:
        print(json.dumps([dict(severity=s, code=c, file=f, message=m) for s, c, f, m in issues], indent=2))
    else:
        for s, c, f, m in issues:
            print(f"{s.upper():5} {c:18} {f}: {m}")
        if not issues:
            print("OK: no instruction-file problems found")
    bad = any(s == "error" for s, *_ in issues) or (a.strict and issues)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
