"""Minimal YAML frontmatter parser — handles SKILL.md needs without PyYAML."""
from __future__ import annotations

import re
from pathlib import Path


def parse_frontmatter(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not content.startswith("---"):
        return {}
    end_idx = content.find("\n---", 4)
    if end_idx < 0:
        return {}
    return _parse_yaml_block(content[4:end_idx])


def _parse_yaml_block(text: str) -> dict:
    """Top-level scalars + folded/literal blocks + continuation. No nesting."""
    result: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in (">", ">-", "|", "|-", ">+", "|+"):
            buf, i = [], i + 1
            while i < len(lines):
                lk = lines[i]
                if lk.strip() == "" or lk.startswith("  "):
                    buf.append(lk[2:] if lk.startswith("  ") else "")
                    i += 1
                else:
                    break
            joiner = " " if rest.startswith(">") else "\n"
            result[key] = joiner.join(s.strip() for s in buf if s.strip() or joiner == "\n").strip()
            continue
        if rest:
            if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
                rest = rest[1:-1]
            buf = [rest]
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                buf.append(lines[i].strip())
                i += 1
            result[key] = " ".join(buf)
            continue
        i += 1
        if i < len(lines) and lines[i].startswith("  "):
            buf = []
            is_list = lines[i].lstrip().startswith("- ")
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                if lines[i].strip():
                    buf.append(lines[i].strip())
                i += 1
            if buf:
                if is_list and all(b.startswith("- ") for b in buf):
                    items = []
                    for b in buf:
                        v = b[2:].strip()
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1]
                        items.append(v)
                    result[key] = items
                else:
                    result[key] = " ".join(buf)
    return result
