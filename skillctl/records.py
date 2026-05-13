"""Per-machine records persistence + cross-machine merge."""
from __future__ import annotations

import json
from pathlib import Path


STATUS_RANK = {"active": 0, "archival": 1, "runtime": 2, "reference": 3, "deprecated": 4}


def write_machine_records(records: list[dict], records_dir: Path, machine: str) -> Path:
    records_dir.mkdir(parents=True, exist_ok=True)
    p = records_dir / f"{machine}.jsonl"
    with p.open("w", encoding="utf-8") as f:
        for rec in records:
            slim = dict(rec)
            slim["sub_skills"] = None
            f.write(json.dumps(slim, ensure_ascii=False, separators=(",", ":")) + "\n")
    return p


def load_all_machine_records(records_dir: Path) -> list[dict]:
    """Merge by name, prefer higher-priority status, track machines."""
    if not records_dir.exists():
        return []
    by_name: dict = {}
    for f in sorted(records_dir.glob("*.jsonl")):
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
            name = rec.get("name")
            if not name:
                continue
            m = rec.get("machine")
            existing = by_name.get(name)
            if existing is None:
                rec["machines"] = [m] if m else []
                by_name[name] = rec
            else:
                machines = existing.setdefault("machines", [])
                if m and m not in machines:
                    machines.append(m)
                new_rank = STATUS_RANK.get(rec.get("status"), 99)
                old_rank = STATUS_RANK.get(existing.get("status"), 99)
                if new_rank < old_rank:
                    rec["machines"] = machines
                    by_name[name] = rec
    return sorted(by_name.values(), key=lambda r: r.get("name", ""))


def detect_drift(records_dir: Path) -> list[dict]:
    """Detect skills present on some machines but not others.

    Returns list of {name, present_on, missing_from}.
    """
    if not records_dir.exists():
        return []
    machine_skills: dict[str, set] = {}
    for f in sorted(records_dir.glob("*.jsonl")):
        machine = f.stem
        names: set = set()
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
            if rec.get("status") == "active" and rec.get("name"):
                names.add(rec["name"])
        machine_skills[machine] = names

    if len(machine_skills) < 2:
        return []

    all_machines = set(machine_skills.keys())
    all_skills: set = set()
    for names in machine_skills.values():
        all_skills |= names

    drifts = []
    for name in sorted(all_skills):
        present_on = sorted(m for m, names in machine_skills.items() if name in names)
        missing_from = sorted(all_machines - set(present_on))
        if missing_from:
            drifts.append({
                "name": name,
                "present_on": present_on,
                "missing_from": missing_from,
            })
    return drifts
