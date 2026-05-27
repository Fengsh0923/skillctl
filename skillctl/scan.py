"""Scan skill source roots and classify each SKILL.md."""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .frontmatter import parse_frontmatter


_SKIP_SEGMENTS = (".venv", "node_modules", "site-packages")


def is_vendor_bundle(skill_path: Path) -> bool:
    """Vendor bundle: parent has CLAUDE.md sibling AND 2+ sub-skills."""
    parent = skill_path.parent
    if not (parent / "CLAUDE.md").exists():
        return False
    return sum(1 for _ in parent.glob("*/SKILL.md")) >= 2


def is_sub_skill(skill_path: Path) -> bool:
    """True if skill_path is a sub-skill nested under a vendor bundle."""
    grand = skill_path.parent.parent
    return (grand / "SKILL.md").exists() and (grand / "CLAUDE.md").exists()


def has_cjk(text: str) -> bool:
    if not text:
        return False
    return any("一" <= ch <= "鿿" for ch in text)


def classify_origin(name: str, description: str, skill_path: Path, status: str, cfg: Config) -> str:
    if status == "deprecated":
        return "deprecated"
    if is_vendor_bundle(skill_path):
        return "vendor"
    haystack = (name or "") + " " + (description or "")
    if cfg.self_keywords and any(kw in haystack for kw in cfg.self_keywords):
        return "self"
    if cfg.cjk_fallback_self and has_cjk(description):
        return "self"
    return "community"


_TRIGGER_PATTERNS = [
    re.compile(r"触发(?:词|条件|场景)?[:：]\s*([^\n。]+)"),
    re.compile(r"[Tt]riggers?(?:\s+on)?[:：]\s*([^\n.]+)"),
    re.compile(r"[Uu]se\s+when[:：]\s*([^\n.]+)"),
]


def extract_triggers(description: str) -> list[str]:
    if not description:
        return []
    for pat in _TRIGGER_PATTERNS:
        m = pat.search(description)
        if m:
            return [p.strip().strip("'\"`") for p in re.split(r"[,，、；;/]| or | and ", m.group(1)) if p.strip()]
    return []


def triggers_from_frontmatter(fm: dict) -> list[str]:
    """Prefer explicit YAML `triggers:` list if present."""
    raw = fm.get("triggers")
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    if isinstance(raw, str) and raw.strip():
        return [p.strip() for p in re.split(r"[,，、；;]", raw) if p.strip()]
    return []


def detect_goal(description: str, cfg: Config) -> str | None:
    if not description or not cfg.goals:
        return None
    for goal in cfg.goals:
        if any(kw in description for kw in goal.keywords):
            return goal.id
    return None


def scan_all(cfg: Config) -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()
    home_str = str(Path.home())

    for src in cfg.sources:
        if not src.root.exists():
            continue
        for skill_path in sorted(src.root.glob(src.glob)):
            sp_str = str(skill_path)
            if sp_str in seen:
                continue
            seen.add(sp_str)
            if is_sub_skill(skill_path):
                continue
            if any(seg in skill_path.parts for seg in _SKIP_SEGMENTS):
                continue

            fm = parse_frontmatter(skill_path)
            name = fm.get("name") or skill_path.parent.name
            description = fm.get("description", "")
            origin = classify_origin(name, description, skill_path, src.status, cfg)

            sub_skills: list[dict] = []
            parent = skill_path.parent
            if origin == "vendor" and (parent / "CLAUDE.md").exists():
                for sub_path in sorted(parent.glob("*/SKILL.md")):
                    sub_fm = parse_frontmatter(sub_path)
                    sub_skills.append({
                        "name": sub_fm.get("name") or sub_path.parent.name,
                        "description": (sub_fm.get("description") or "")[:160],
                    })

            archived = str(fm.get("archived", "")).strip().lower() in ("true", "yes", "1")
            records.append({
                "name": name,
                "status": "inactive" if archived else src.status,
                "origin": origin,
                "goal": detect_goal(description, cfg),
                "description": (description or "")[:500],
                "triggers": triggers_from_frontmatter(fm) or extract_triggers(description),
                "source_path": sp_str.replace(home_str, "~", 1),
                "machine": cfg.machine,
                "sub_skill_count": len(sub_skills),
                "sub_skills": sub_skills,
                "usage_30d": 0,
                "last_used": None,
            })
    return records
