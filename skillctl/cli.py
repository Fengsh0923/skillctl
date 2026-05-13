"""skillctl CLI."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .config import Config, DEFAULT_CONFIG_PATH
from .integrity import check_reference_integrity
from .records import detect_drift, load_all_machine_records, write_machine_records
from .report import write_html, write_jsonl, write_md
from .scan import scan_all
from .usage import load_usage, merge_usage


def cmd_rebuild(cfg: Config, args: argparse.Namespace) -> int:
    cfg.ensure_dirs()
    print(f"skillctl rebuild · machine={cfg.machine} · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Catalog dir: {cfg.catalog_dir}")
    print()

    print("Scanning sources...")
    records = scan_all(cfg)
    print(f"  this machine ({cfg.machine}): {len(records)} skills")

    print("Loading usage stats...")
    usage_stats = load_usage(cfg.usage_dir)
    merge_usage(records, usage_stats)
    print(f"  loaded usage for {len(usage_stats)} unique skills")

    print(f"Persisting {cfg.machine}'s records...")
    rp = write_machine_records(records, cfg.records_dir, cfg.machine)
    print(f"  → {rp}")

    print("Merging across machines...")
    all_records = load_all_machine_records(cfg.records_dir)
    merge_usage(all_records, usage_stats)
    counts: dict = {}
    for r in all_records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    for st in ("active", "archival", "reference", "deprecated", "runtime"):
        if st in counts:
            print(f"  {st:11s}: {counts[st]}")
    print(f"  {'TOTAL':11s}: {len(all_records)}")

    print("Writing outputs...")
    jc = write_jsonl(all_records, cfg.catalog_dir, cfg.description_budget)
    print(f"  → catalog.jsonl ({jc['total']}) / catalog_active.jsonl ({jc['active']}) / catalog_inactive.jsonl ({jc['inactive']})")
    if jc["description_over_budget"]:
        print(f"  ⚠ description budget exceeded by {jc['description_over_budget']} chars (limit {cfg.description_budget})")
    md_p = write_md(all_records, cfg.catalog_dir, cfg.machine)
    print(f"  → {md_p}")
    html_p = write_html(all_records, cfg.catalog_dir, cfg.machine)
    print(f"  → {html_p}")

    ri = check_reference_integrity(records, cfg.machine, cfg.catalog_dir / "reference_issues.md")
    if ri:
        print(f"  → reference_issues.md (🔴 {ri} skills with dead refs)")
    else:
        print("  → reference_issues.md (clean)")
    print("\nDone.")
    return 0


def cmd_check(cfg: Config, args: argparse.Namespace) -> int:
    """Health check: drift across machines + reference integrity."""
    cfg.ensure_dirs()
    exit_code = 0

    drifts = detect_drift(cfg.records_dir)
    if drifts:
        print(f"🔴 Cross-machine drift: {len(drifts)} active skills not present on all machines")
        for d in drifts[:20]:
            print(f"  - {d['name']}: on {d['present_on']}, missing from {d['missing_from']}")
        if len(drifts) > 20:
            print(f"  ... and {len(drifts) - 20} more")
        exit_code = 1
    else:
        print("✅ No cross-machine drift detected.")

    records = scan_all(cfg)
    ri = check_reference_integrity(records, cfg.machine, cfg.catalog_dir / "reference_issues.md")
    if ri:
        print(f"🔴 {ri} skills reference missing slash targets (see reference_issues.md)")
        exit_code = 1
    else:
        print("✅ All slash refs resolve.")

    return exit_code


def cmd_usage(cfg: Config, args: argparse.Namespace) -> int:
    cfg.ensure_dirs()
    stats = load_usage(cfg.usage_dir)
    if not stats:
        print("No usage data. Append events to usage/<machine>.jsonl to populate.")
        print(f"  Path: {cfg.usage_dir}")
        return 0
    items = sorted(stats.items(), key=lambda kv: -kv[1]["count_30d"])
    n = args.top or 20
    print(f"Top {n} skills by 30-day calls ({len(stats)} total):\n")
    print(f"{'skill':<40} {'30d':>6} {'total':>8}  machines")
    for name, s in items[:n]:
        m = ",".join(s["machines"])
        print(f"{name:<40} {s['count_30d']:>6} {s['count_total']:>8}  {m}")
    return 0


def cmd_record(cfg: Config, args: argparse.Namespace) -> int:
    """Append a usage event. Intended for hooks."""
    cfg.ensure_dirs()
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    event = {"ts": ts, "skill": args.skill}
    p = cfg.usage_dir / f"{cfg.machine}.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    if not args.quiet:
        print(f"recorded: {args.skill} @ {ts} → {p}")
    return 0


def cmd_init(cfg: Config, args: argparse.Namespace) -> int:
    """Write a starter config to ~/.skillctl/config.toml."""
    if DEFAULT_CONFIG_PATH.exists() and not args.force:
        print(f"Config already exists: {DEFAULT_CONFIG_PATH}")
        print("Use --force to overwrite.")
        return 1
    DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    starter = STARTER_CONFIG
    DEFAULT_CONFIG_PATH.write_text(starter, encoding="utf-8")
    print(f"Wrote starter config: {DEFAULT_CONFIG_PATH}")
    print("Edit it, then run: skillctl rebuild")
    return 0


STARTER_CONFIG = """# skillctl configuration. See https://github.com/frankshen/skillctl#config

[paths]
catalog_dir = "~/.skillctl/catalog"
# records_dir, usage_dir default to subdirs of catalog_dir.

[machine]
# Optional nickname for this machine. Defaults to hostname.
# nickname = "laptop"

# Where to scan for SKILL.md files. Add as many as you need.
[[sources]]
status = "active"
root = "~/.claude/skills"
glob = "*/SKILL.md"

[[sources]]
status = "active"
root = "~/.claude/commands"
glob = "*.md"

# Example: a folder of skills you've collected but not enabled yet.
# [[sources]]
# status = "archival"
# root = "~/skill-library"
# glob = "*/SKILL.md"

[classify]
# Personal keywords that mark a skill as origin="self" (vs community/vendor).
self_keywords = []
# Treat skills with Chinese descriptions as 'self' (heuristic for solo CN devs).
cjk_fallback_self = false

[budget]
# Claude Code silently truncates description text past this many characters
# when loading the active catalog. skillctl warns when you exceed it.
description_budget = 15000

# Optional: tag skills with strategic goal IDs by keyword match.
# [[goals]]
# id = "G1"
# name = "Content creation"
# keywords = ["blog", "podcast", "video"]
"""


def main() -> int:
    parser = argparse.ArgumentParser(prog="skillctl", description="Meta-layer for Claude Code skills.")
    parser.add_argument("--config", type=Path, help=f"Path to config (default: {DEFAULT_CONFIG_PATH})")
    parser.add_argument("--version", action="version", version=f"skillctl {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("rebuild", help="Scan sources and rebuild catalog outputs.")
    sub.add_parser("check", help="Run health checks (drift, reference integrity).")

    p_usage = sub.add_parser("usage", help="Show usage leaderboard.")
    p_usage.add_argument("--top", type=int, default=20)

    p_record = sub.add_parser("record", help="Append a usage event (for hooks).")
    p_record.add_argument("skill", help="Skill name that was invoked.")
    p_record.add_argument("--quiet", action="store_true")

    p_init = sub.add_parser("init", help="Write a starter config to ~/.skillctl/config.toml.")
    p_init.add_argument("--force", action="store_true")

    args = parser.parse_args()

    if args.command == "init":
        # init doesn't need a loaded config
        return cmd_init(Config._from_dict({}), args)

    try:
        cfg = Config.load(args.config)
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        return 2

    dispatch = {
        "rebuild": cmd_rebuild,
        "check": cmd_check,
        "usage": cmd_usage,
        "record": cmd_record,
    }
    return dispatch[args.command](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
