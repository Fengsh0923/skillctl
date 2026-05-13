"""End-to-end smoke test using a temp config + fixture skills."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_skill(root: Path, name: str, description: str) -> None:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n# {name}\n",
        encoding="utf-8",
    )


def test_rebuild_emits_outputs(tmp_path: Path):
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    _write_skill(skills_root, "alpha", "Does alpha things. Triggers: alpha")
    _write_skill(skills_root, "beta", "Does beta things.")

    catalog_dir = tmp_path / "catalog"
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        f"""
[paths]
catalog_dir = "{catalog_dir}"

[machine]
nickname = "test-host"

[[sources]]
status = "active"
root = "{skills_root}"
glob = "*/SKILL.md"
""",
        encoding="utf-8",
    )

    r = subprocess.run(
        [sys.executable, "-m", "skillctl.cli", "--config", str(cfg_path), "rebuild"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    active = catalog_dir / "catalog_active.jsonl"
    assert active.exists()
    names = {json.loads(line)["name"] for line in active.read_text().splitlines()}
    assert names == {"alpha", "beta"}

    assert (catalog_dir / "catalog.md").exists()
    assert (catalog_dir / "catalog.html").exists()
    assert (catalog_dir / "records" / "test-host.jsonl").exists()


def test_record_appends_event(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        f"""
[paths]
catalog_dir = "{tmp_path / 'catalog'}"
[machine]
nickname = "test-host"
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "-m", "skillctl.cli", "--config", str(cfg_path),
         "record", "alpha", "--quiet"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr

    usage_file = tmp_path / "catalog" / "usage" / "test-host.jsonl"
    assert usage_file.exists()
    event = json.loads(usage_file.read_text().strip())
    assert event["skill"] == "alpha"
