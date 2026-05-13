"""Aggregate skill usage events from usage/*.jsonl.

Event line format (one JSON object per line):
    {"ts": "2026-05-13T10:00:00Z", "skill": "skillname"}

Hook scripts (e.g. PostToolUse) append to usage/<machine>.jsonl.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_usage(usage_dir: Path) -> dict:
    if not usage_dir.exists():
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    stats: dict = {}
    for f in sorted(usage_dir.glob("*.jsonl")):
        machine = f.stem
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            skill = rec.get("skill")
            ts_str = rec.get("ts", "")
            if not skill or not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                continue
            s = stats.setdefault(skill, {
                "count_30d": 0, "count_total": 0, "last_used": None, "machines": set(),
            })
            s["count_total"] += 1
            s["machines"].add(machine)
            if ts >= cutoff:
                s["count_30d"] += 1
            if s["last_used"] is None or ts_str > s["last_used"]:
                s["last_used"] = ts_str
    for s in stats.values():
        s["machines"] = sorted(s["machines"])
    return stats


def merge_usage(records: list[dict], usage_stats: dict) -> None:
    for r in records:
        s = usage_stats.get(r["name"])
        if s:
            r["usage_30d"] = s["count_30d"]
            r["usage_total"] = s["count_total"]
            r["last_used"] = s["last_used"]
            r["used_by_machines"] = s["machines"]
        else:
            r["usage_total"] = 0
            r["used_by_machines"] = []
