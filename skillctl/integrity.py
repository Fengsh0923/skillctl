"""Reference integrity: catch /xxx slash refs to skills that don't exist."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


_SLASH_REF_RE = re.compile(r"(?<![/\w])/([a-z一-鿿][\w一-鿿-]{2,39})\b")

# Generic noise: filesystem paths, HTML tags, URL fragments, single letters.
# Project-specific allowlist can be added via config (future).
DEFAULT_WHITELIST: set[str] = {
    # POSIX path prefixes
    "tmp", "usr", "var", "bin", "opt", "etc", "dev", "private", "home",
    "Users", "Volumes", "System", "Library", "Applications",
    "path", "to", "your", "the", "my", "some",
    # Built-in slash commands (Claude Code)
    "help", "clear", "exit", "quit", "login", "logout",
    # URL / API path fragments
    "api", "v1", "v2", "chat", "completions", "messages", "embeddings",
    "index", "view", "folder", "code", "auth", "sso", "signin", "setup",
    "servers", "workspaces", "dashboard", "perm", "perms", "skills",
    # HTML tags
    "html", "head", "body", "div", "span", "section", "nav", "title",
    "button", "table", "form", "input", "textarea", "article", "aside",
    "footer", "header", "main", "ul", "ol", "li", "img", "svg", "a",
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "br", "hr",
    # Single-letter / CLI flag fragments
    "c", "n", "r", "s", "v", "h",
}


def _strip_code_blocks(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def check_reference_integrity(
    records: list[dict], machine: str, out_path: Path
) -> int:
    """Scan each active skill on this machine for dead /xxx slash refs.

    Returns count of skills with dead refs. Writes report to out_path.
    """
    home = Path.home()
    active_names = {
        r["name"] for r in records
        if r.get("status") == "active" and r.get("machine") == machine
    }

    issues: list[tuple[str, list[str]]] = []
    for r in records:
        if r.get("status") != "active" or r.get("machine") != machine:
            continue
        src = r.get("source_path", "").replace("~", str(home), 1)
        if not src or not Path(src).exists():
            continue
        try:
            body = Path(src).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if body.startswith("---"):
            parts = body.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
        body = _strip_code_blocks(body)
        refs: set[str] = set()
        for m in _SLASH_REF_RE.finditer(body):
            ref = m.group(1)
            if ref in DEFAULT_WHITELIST:
                continue
            if re.fullmatch(r"v?\d+", ref):
                continue
            refs.add(ref)
        missing = sorted(ref for ref in refs if ref not in active_names and ref != r["name"])
        if missing:
            issues.append((r["name"], missing))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not issues:
        out_path.write_text(
            f"# Skill Reference Integrity · {machine}\n\n"
            f"_Last check: {datetime.now().isoformat(timespec='seconds')}_\n\n"
            "✅ All active skills reference only existing targets.\n",
            encoding="utf-8",
        )
        return 0

    lines = [
        f"# Skill Reference Integrity · {machine}",
        "",
        f"_Last check: {datetime.now().isoformat(timespec='seconds')}_",
        "",
        f"🔴 **{len(issues)} skill(s) reference missing targets.**",
        "",
        "| Skill | Missing references |",
        "|---|---|",
    ]
    for name, missing in sorted(issues):
        refs_str = " ".join(f"`/{r}`" for r in missing)
        lines.append(f"| `{name}` | {refs_str} |")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return len(issues)
