# Configuration

`skillctl` reads `~/.skillctl/config.toml` (override with `--config <path>`).

## Full example

```toml
[paths]
catalog_dir = "~/.skillctl/catalog"
# records_dir and usage_dir default to subdirs of catalog_dir.
# records_dir = "~/.skillctl/catalog/records"
# usage_dir   = "~/.skillctl/catalog/usage"

[machine]
# Optional nickname for this machine. Used as the per-machine records filename
# and in dashboards. Defaults to socket.gethostname().
nickname = "laptop"

# Skill source roots. Add as many as you have. Order doesn't matter.
[[sources]]
status = "active"          # active | archival | reference | deprecated | runtime
root   = "~/.claude/skills"
glob   = "*/SKILL.md"

[[sources]]
status = "active"
root   = "~/.claude/commands"
glob   = "*.md"

[[sources]]
status = "archival"
root   = "~/skill-library"
glob   = "*/SKILL.md"

[classify]
# Personal keywords that mark a skill as origin="self" (vs community/vendor).
# Helps you distinguish "skills I wrote" from "skills I installed".
self_keywords = ["my-handle", "my-project"]

# If true, any skill with CJK characters in its description is tagged "self".
# Useful for solo Chinese-speaking devs.
cjk_fallback_self = false

[budget]
# Claude Code silently drops description text past this many chars when loading
# the active catalog. skillctl warns when you exceed it.
description_budget = 15000

# Optional: tag skills with strategic-goal IDs by keyword match.
[[goals]]
id       = "G1"
name     = "Content creation"
keywords = ["blog", "podcast", "video"]

[[goals]]
id       = "G2"
name     = "Internal tooling"
keywords = ["devops", "ci", "deploy"]
```

## Source statuses

| Status | Meaning |
|---|---|
| `active` | Loadable by Claude Code — what agents actually see. |
| `archival` | Collected but not enabled (e.g. a personal library). |
| `reference` | Copies kept for study, not invocation. |
| `deprecated` | Old projects you don't want to delete but shouldn't be invoked. |
| `runtime` | Live but outside Claude Code (e.g. a different agent runtime). |

When the same skill name appears under multiple sources across machines, `skillctl` keeps the one with the highest-priority status (active > archival > runtime > reference > deprecated).

## Origin

`skillctl` heuristically tags each skill with one of:

- **`self`** — matches `self_keywords` or (if enabled) `cjk_fallback_self`
- **`vendor`** — parent dir contains `CLAUDE.md` and 2+ sibling `SKILL.md` (bundled distribution)
- **`community`** — anything else under `active`
- **`deprecated`** — comes from a `deprecated` source

## Recording usage

`skillctl record <skill-name>` appends to `~/.skillctl/catalog/usage/<machine>.jsonl`.

Wire it into a Claude Code `PostToolUse` hook to populate automatically. The hook should call `skillctl record <skill-name>` whenever a skill is invoked.
