# agentmd-doctor

A zero-dependency Python linter that catches silent `AGENTS.md` / `CLAUDE.md` problems before a coding agent ignores your rules.

## The real requirement behind it

- **[cli/cli#14075](https://github.com/cli/cli/issues/14075)** – the GitHub CLI team noticed Claude Code doesn't load their `AGENTS.md`, "so our agent instructions are likely being ignored", and wanted one source of truth without two copies drifting. A commenter said they'd "maintained both files for months and found the drift frustrating".
- **[anthropics/claude-code#6235](https://github.com/anthropics/claude-code/issues/6235)** – native fallback shipped in v2.1.277, but it only reads `AGENTS.md` when there is *no* `CLAUDE.md`. The thread lists what is still unsolved: a stale `CLAUDE.md` silently hides `AGENTS.md`, nested `AGENTS.md` files only load in one mode, `AGENTS.local.md`/`AGENTS.override.md` are never read, and nothing warns you.

The native fallback fixed the "no CLAUDE.md" case; this tool covers the remaining silent failures, and can run in CI.

## Checks

| code | severity | meaning |
|---|---|---|
| `shadowed-agents-md` | error | both files exist, `CLAUDE.md` doesn't `@import` `AGENTS.md`, and they share no rules |
| `drift` | error | both exist, partly duplicated, and `AGENTS.md` has rules missing from `CLAUDE.md` |
| `broken-import` | error | an `@path` import points at a missing file |
| `import-cycle` | error | a file imports itself |
| `nested-agents-md` | warn | nested `AGENTS.md` under a `CLAUDE.md` tree; only loaded in `claude-md-and-agents-md` mode |
| `unsupported-name` | warn | `AGENTS.local.md` / `AGENTS.override.md` are not read by Claude Code |

The fix for the first two is the one the issues recommend: make `CLAUDE.md` contain just `@AGENTS.md`.

## Run

```bash
python3 agentmd_doctor.py [path]        # human output
python3 agentmd_doctor.py --json .      # machine output
python3 agentmd_doctor.py --strict .    # warnings fail too
python3 -m unittest discover -s tests   # tests
```

Exit code is 1 on any error, so it drops into CI (see `.github/workflows/ci.yml`).

## Limits

Heuristic: drift is detected by comparing normalized rule lines, not semantics. Behavior is based on the Claude Code behavior described in the issue above (v2.1.277+); verify against current docs.
