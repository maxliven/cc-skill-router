"""Registry generator — scan skill directories and build index.json.

Port of generate-registry.ps1 to Python, with additional support for
multiple skill directories and configurable domain/group inference.
"""

import json
import re
from pathlib import Path
from typing import Any

# ── Domain inference from skill name ──────────────────────────────────────────

DOMAIN_OVERRIDES: dict[str, str] = {
    "lit-search": "tool",
    "neat-freak": "tool",
    "notebooklm": "tool",
    "ppt-master": "tool",
    "skill-curator": "tool",
    "skill-router": "tool",
    "skill-search": "tool",
    "storage-analyzer": "tool",
    "cache-cleanup": "tool",
    "ccswitch": "tool",
    "aihot": "tool",
    "content-research-writer": "tool",
    "hv-analysis": "tool",
    "khazix-writer": "tool",
    "humanities-guard": "tool",
    "tong-jincheng-skill": "plugin",
    "zhangxuefeng-skill": "plugin",
    "using-coze-cli": "plugin",
    "dbs-troubleshoot": "runbook",
    "diagnosing-bugs": "runbook",
    "libreoffice-calc": "tool",
    "libreoffice-writer": "tool",
}

GROUP_SKILLS: dict[str, str] = {
    **{s: "coding" for s in [
        "code-review", "codebase-design", "domain-modeling",
        "improve-codebase-architecture", "tdd", "to-prd",
        "ponytail", "ponytail-audit", "ponytail-debt",
        "ponytail-gain", "ponytail-help", "ponytail-review",
        "diagnosing-bugs",
    ]},
    **{s: "content" for s in [
        "khazix-writer", "content-research-writer", "hv-analysis",
    ]},
    **{s: "persona" for s in [
        "tong-jincheng-skill", "zhangxuefeng-skill", "using-coze-cli",
    ]},
    **{s: "runbook" for s in [
        "dbs-troubleshoot", "git-guardrails-claude-code", "grill-me", "grilling",
    ]},
    **{s: "tools" for s in [
        "lit-search", "neat-freak", "notebooklm", "ppt-master",
        "skill-curator", "storage-analyzer", "cache-cleanup", "ccswitch",
        "aihot", "humanities-guard", "libreoffice-calc", "libreoffice-writer",
        "skill-router", "skill-search",
    ]},
    "s4h": "thinking",
    "dbs": "thinking",
}


def get_domain(name: str) -> str:
    """Infer domain from skill name."""
    if name in DOMAIN_OVERRIDES:
        return DOMAIN_OVERRIDES[name]
    if name.startswith("s4h-"):
        parts = name.split("-")
        if len(parts) >= 2:
            return parts[1]
    if name.startswith("dbs-"):
        return "dbs"
    if name.startswith("ponytail"):
        return "ponytail"
    if name.startswith("libreoffice"):
        return "tool"
    return "other"


def get_group(name: str, domain: str, skill_type: str) -> str:
    """Map skill to high-level group for routing."""
    if name in GROUP_SKILLS:
        return GROUP_SKILLS[name]
    if name.startswith("s4h-"):
        return "thinking"
    if name.startswith("dbs-"):
        return "thinking"
    return "infra"


def get_type(name: str) -> str:
    """Infer skill type from name."""
    if name.startswith("s4h-"):
        return "s4h"
    if name.startswith("dbs-"):
        return "dbs"
    if name.startswith("ponytail"):
        return "ponytail"
    if name.startswith("libreoffice"):
        return "tool"
    tool_names = {
        "lit-search", "neat-freak", "notebooklm", "ppt-master",
        "skill-curator", "storage-analyzer", "cache-cleanup", "ccswitch",
        "aihot", "content-research-writer", "hv-analysis", "khazix-writer",
        "humanities-guard",
    }
    if name in tool_names:
        return "tool"
    plugin_names = {"tong-jincheng-skill", "zhangxuefeng-skill", "using-coze-cli"}
    if name in plugin_names:
        return "plugin"
    return "other"


def extract_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter from SKILL.md content.

    Returns a dict with at least 'description' key.
    Handles double-quoted, single-quoted, unquoted, folded (>),
    and literal-block (|) YAML values.
    """
    result: dict[str, str] = {}
    normalized = content.replace("\r\n", "\n")

    # Match YAML frontmatter between --- delimiters
    m = re.match(r"^---\s*\n(.*?)\n---", normalized, re.DOTALL)
    if not m:
        return result

    yaml_block = m.group(1)

    desc = _extract_yaml_field(yaml_block, "description")
    if desc:
        result["description"] = desc

    sot = _extract_yaml_field(yaml_block, "source_of_truth")
    if sot:
        result["source_of_truth"] = sot

    tp = _extract_yaml_field(yaml_block, "trigger_patterns")
    if tp:
        result["trigger_patterns"] = tp

    return result


def _extract_yaml_field(yaml_block: str, field: str) -> str | None:
    """Extract a single field from a YAML block.

    Handles: double-quoted, single-quoted, unquoted (single line),
    folded (>), and literal-block (|) multi-line values.
    """
    # Double-quoted: description: "value"
    m = re.search(rf'^{field}:\s*"([^"]*)"', yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Single-quoted: description: 'value'
    m = re.search(rf"^{field}:\s*'([^']*)'", yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Folded block scalar: description: >\n  value
    m = _extract_block_scalar(yaml_block, field, ">")
    if m:
        return m

    # Literal block scalar: description: |\n  value
    m = _extract_block_scalar(yaml_block, field, "|")
    if m:
        return m

    # Unquoted single line: description: value
    m = re.search(rf"^{field}:\s*(.+?)$", yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    return None


def _extract_block_scalar(yaml_block: str, field: str, marker: str) -> str | None:
    """Extract a YAML block scalar (> or |) value.

    Matches from the field line through indented continuation lines,
    stopping at the next field (non-indented line) or end of block.
    """
    escaped_marker = re.escape(marker)
    m = re.search(
        rf"^{field}:\s*{escaped_marker}\s*\n(.*?)(?:\n\S|\Z)",
        yaml_block,
        re.MULTILINE | re.DOTALL,
    )
    if m:
        # Collapse whitespace while preserving word boundaries
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def scan_directory(skills_dir: Path) -> dict[str, dict[str, Any]]:
    """Scan a skills directory for SKILL.md files and build registry entries.

    Errors (permission, encoding) are skipped with a warning — one bad
    file shouldn't break the entire scan.
    """
    registry: dict[str, dict[str, Any]] = {}

    if not skills_dir.is_dir():
        return registry

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue

        name = skill_dir.name

        try:
            content = skill_md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            print(f"  [WARN] Skipping {name}: {e}", flush=True)
            continue

        frontmatter = extract_frontmatter(content)
        description = frontmatter.get("description", "")
        source_of_truth = frontmatter.get("source_of_truth")
        is_bridge = source_of_truth is not None

        domain = get_domain(name)
        skill_type = get_type(name)
        group = get_group(name, domain, skill_type)

        entry: dict[str, Any] = {
            "name": name,
            "description": description,
            "domain": domain,
            "group": group,
            "type": skill_type,
            "path": str(skill_md.resolve()),
            "is_bridge": is_bridge,
        }

        if source_of_truth:
            entry["source_of_truth"] = source_of_truth

        registry[name] = entry

    return registry


def generate_registry(
    skill_dirs: list[Path] | None = None,
    output_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Generate the skill registry from one or more skill directories.

    Args:
        skill_dirs: List of directories to scan. Defaults to
            ~/.claude/skills/ and ~/.codex/skills/.
        output_path: If provided, write JSON to this path.

    Returns:
        The complete registry dict.
    """
    if skill_dirs is None:
        skill_dirs = [
            Path.home() / ".claude" / "skills",
            Path.home() / ".codex" / "skills",
        ]

    registry: dict[str, dict[str, Any]] = {}
    missing_dirs: list[str] = []

    for skills_dir in skill_dirs:
        if not skills_dir.is_dir():
            missing_dirs.append(str(skills_dir))
            continue
        try:
            entries = scan_directory(skills_dir)
        except PermissionError:
            print(f"  [WARN] Permission denied: {skills_dir}", flush=True)
            continue
        registry.update(entries)

    if missing_dirs:
        print("  [INFO] Directories not found (skipped):")
        for d in missing_dirs:
            print(f"    - {d}")
        print("  Use -d to specify custom skill directories.")
        print()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return registry
