# skillctl

> Meta-layer for Claude Code skills: catalog, health check, cross-machine sync, usage stats.

When your `~/.claude/skills/` has 5 skills, you remember what each does.
When it has 50, you don't.
When it has 100 across two machines, you have no idea what's installed, what's actually being used, or whether your laptop and desktop are in sync.

`skillctl` builds the missing meta layer:

- **Catalog** — scan all skill source roots, emit JSONL + Markdown + searchable HTML dashboard
- **Health** — flag dead `/slash` references, detect cross-machine drift
- **Usage** — aggregate skill invocation events; surface top-used and never-used
- **Budget** — warn when `description` text exceeds Claude Code's silent truncation limit

Zero runtime dependencies. Single binary. Python 3.11+.

## Install

```bash
pip install skillctl   # not on PyPI yet — clone the repo and `pip install -e .`
```

## Quick start

```bash
skillctl init           # writes ~/.skillctl/config.toml with sensible defaults
skillctl rebuild        # scan + emit catalog outputs
skillctl check          # health check (drift + dead refs)
skillctl usage --top 10 # leaderboard
```

Open `~/.skillctl/catalog/catalog.html` in a browser.

## What it does

### `rebuild` — scan and emit

Walks every `[[sources]]` root in your config and produces:

| Output | Purpose |
|---|---|
| `catalog.jsonl` | Full record per skill (status, origin, triggers, path, usage). |
| `catalog_active.jsonl` | Only `status="active"` — what's actually loadable. |
| `catalog_inactive.jsonl` | Archival / reference / deprecated. |
| `catalog.md` | Human-readable inventory. |
| `catalog.html` | Searchable dashboard with charts. |
| `reference_issues.md` | Skills that reference `/xxx` slashes which don't exist. |
| `records/<machine>.jsonl` | This machine's snapshot, for cross-machine merge. |

### `check` — health

- **Cross-machine drift**: skill `foo` is active on `laptop` but missing on `desktop`. Listed by machine pair.
- **Dead references**: skill `bar`'s SKILL.md mentions `/baz` but `/baz` isn't installed anywhere.

Exits non-zero if issues found — wire into CI or pre-commit.

### `usage` — leaderboard

Reads usage events from `~/.skillctl/catalog/usage/<machine>.jsonl`. Each event is one line:

```json
{"ts": "2026-05-13T10:00:00Z", "skill": "skillname"}
```

You append events however you like. Easiest: have your Claude Code `PostToolUse` hook call `skillctl record <skill-name>`.

After events accumulate, `skillctl usage` shows top-N skills by 30-day calls — telling you which skills earn their keep and which 6-month-old `.skills/foo/` is dead weight.

## Configuration

`~/.skillctl/config.toml`. Run `skillctl init` to scaffold one. See [docs/CONFIG.md](docs/CONFIG.md) for every option.

Minimal example:

```toml
[[sources]]
status = "active"
root = "~/.claude/skills"
glob = "*/SKILL.md"

[[sources]]
status = "active"
root = "~/.claude/commands"
glob = "*.md"
```

## Why this exists

I was running Claude Code on two Macs with shared skills via cloud sync.
After 9 months I had 67 active skills and 113 inactive ones, with no way to tell:

- which skills I actually invoke vs. which sit there from 6 months ago
- whether laptop and desktop were in sync (spoiler: they weren't)
- which skills' descriptions were so long they got silently truncated by Claude Code
- which skills referenced other skills that I'd since renamed or deleted

So I built this for myself. Open-sourced because the gap is generic, not personal.

## Status

v0.1 — works for me daily. APIs and config schema may change before v1.

## License

MIT
