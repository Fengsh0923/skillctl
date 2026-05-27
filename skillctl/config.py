"""Config loader. TOML-based, stdlib only (Python 3.11+)."""
from __future__ import annotations

import os
import socket
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


HOME = Path.home()
DEFAULT_CONFIG_PATH = HOME / ".skillctl" / "config.toml"


@dataclass
class Source:
    status: str  # active / archival / reference / deprecated / runtime
    root: Path
    glob: str

    @classmethod
    def from_dict(cls, d: dict) -> "Source":
        return cls(
            status=d["status"],
            root=Path(os.path.expanduser(d["root"])),
            glob=d.get("glob", "*/SKILL.md"),
        )


@dataclass
class Goal:
    id: str
    name: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class Config:
    catalog_dir: Path
    records_dir: Path
    usage_dir: Path
    machine: str
    sources: list[Source]
    goals: list[Goal]
    self_keywords: list[str]
    cjk_fallback_self: bool
    description_budget: int

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or DEFAULT_CONFIG_PATH
        if path.exists():
            with path.open("rb") as f:
                data = tomllib.load(f)
        else:
            data = {}
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        paths = data.get("paths", {})
        catalog_dir = Path(os.path.expanduser(
            paths.get("catalog_dir", "~/.skillctl/catalog")
        ))
        records_dir = Path(os.path.expanduser(
            paths.get("records_dir", str(catalog_dir / "records"))
        ))
        usage_dir = Path(os.path.expanduser(
            paths.get("usage_dir", str(catalog_dir / "usage"))
        ))

        machine_cfg = data.get("machine", {})
        machine = machine_cfg.get("nickname") or socket.gethostname().split(".")[0] or "default"

        sources_raw = data.get("sources") or _default_sources()
        sources = [Source.from_dict(s) for s in sources_raw]

        goals_raw = data.get("goals", [])
        goals = [Goal(id=g["id"], name=g.get("name", g["id"]), keywords=g.get("keywords", []))
                 for g in goals_raw]

        classify = data.get("classify", {})
        self_keywords = classify.get("self_keywords", [])
        cjk_fallback_self = classify.get("cjk_fallback_self", False)

        budget = data.get("budget", {})
        description_budget = budget.get("description_budget", 15000)

        return cls(
            catalog_dir=catalog_dir,
            records_dir=records_dir,
            usage_dir=usage_dir,
            machine=machine,
            sources=sources,
            goals=goals,
            self_keywords=self_keywords,
            cjk_fallback_self=cjk_fallback_self,
            description_budget=description_budget,
        )

    def ensure_dirs(self) -> None:
        for d in (self.catalog_dir, self.records_dir, self.usage_dir):
            d.mkdir(parents=True, exist_ok=True)


def _default_sources() -> list[dict]:
    """Sensible default: scan ~/.claude/skills for SKILL.md files.

    Note: ~/.claude/commands/ holds Claude Code slash-command definitions,
    not skills — do not scan it by default (it pollutes the catalog).
    """
    return [
        {"status": "active", "root": "~/.claude/skills", "glob": "*/SKILL.md"},
    ]
