"""Registry generator — scan skill directories and build index.json.

Port of generate-registry.ps1 to Python, with additional support for
multiple skill directories and configurable domain/group inference.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

# ── Domain inference from skill name ──────────────────────────────────────────

# Skill names that map to specific domains
DOMAIN_OVERRIDES: dict[str, str] = {
    # Tool skills
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
    # Plugin skills
    "tong-jincheng-skill": "plugin",
    "zhangxuefeng-skill": "plugin",
    "using-coze-cli": "plugin",
    # Runbook skills
    "dbs-troubleshoot": "runbook",
    "diagnosing-bugs": "runbook",
    # LibreOffice
    "libreoffice-calc": "tool",
    "libreoffice-writer": "tool",
}

# Skills that map to specific groups (7 groups for routing)
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
            return parts[1]  # s4h-creativity-* → creativity

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

    # All s4h-* sub-skills are thinking
    if name.startswith("s4h-"):
        return "thinking"

    # All dbs-* sub-skills are thinking
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
        "humanities-guard", "content-research-loop", "deep-research-loop",
        "knowledge-maintenance-loop", "lit-watchdog-loop", "method-loop",
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
    Handles double-quoted, single-quoted, unquoted, and folded (>)
    YAML values.
    """
    result: dict[str, str] = {}

    # Normalize line endings
    normalized = content.replace("\r\n", "\n")

    # Match YAML frontmatter between --- delimiters
    m = re.match(r"^---\s*\n(.*?)\n---", normalized, re.DOTALL)
    if not m:
        return result

    yaml_block = m.group(1)

    # Extract description (supports multiple YAML quote styles)
    desc = _extract_yaml_field(yaml_block, "description")
    if desc:
        result["description"] = desc

    # Check for source_of_truth (bridge mode)
    sot = _extract_yaml_field(yaml_block, "source_of_truth")
    if sot:
        result["source_of_truth"] = sot

    # Check for trigger_patterns
    tp = _extract_yaml_field(yaml_block, "trigger_patterns")
    if tp:
        result["trigger_patterns"] = tp

    return result


def _extract_yaml_field(yaml_block: str, field: str) -> str | None:
    """Extract a single field from a YAML block.

    Handles: double-quoted, single-quoted, unquoted (single line),
    and folded (>) multi-line values.
    """
    # Double-quoted: description: "value"
    m = re.search(rf'^{field}:\s*"([^"]*)"', yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Single-quoted: description: 'value'
    m = re.search(rf"^{field}:\s*'([^']*)'", yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Folded: description: >\n  value\n  more
    m = re.search(rf"^{field}:\s*>\s*\n(.*?)(?:\n\S|\Z)", yaml_block, re.MULTILINE | re.DOTALL)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()

    # Unquoted single line: description: value
    m = re.search(rf"^{field}:\s*(.+?)$", yaml_block, re.MULTILINE)
    if m:
        return m.group(1).strip()

    return None


def scan_directory(skills_dir: Path) -> dict[str, dict[str, Any]]:
    """Scan a skills directory for SKILL.md files and build registry entries.

    Args:
        skills_dir: Path to the skills directory (e.g., ~/.claude/skills/)

    Returns:
        Dict mapping skill name → registry entry.
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
        content = skill_md.read_text(encoding="utf-8")
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
    for skills_dir in skill_dirs:
        entries = scan_directory(skills_dir)
        registry.update(entries)  # later dirs override earlier ones

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return registry
