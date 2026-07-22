"""Registry generator — scan skill directories and build index.json.

Port of generate-registry.ps1 to Python, with additional support for
multiple skill directories and configurable domain/group inference.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Default paths ─────────────────────────────────────────────────────────────

DEFAULT_REGISTRY_DIR = Path.home() / ".skill-router"
DEFAULT_REGISTRY_PATH = DEFAULT_REGISTRY_DIR / "index.json"

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
    "content-research-write": "tool",
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
    **{
        s: "coding"
        for s in [
            "code-review",
            "codebase-design",
            "domain-modeling",
            "improve-codebase-architecture",
            "tdd",
            "to-prd",
            "ponytail",
            "ponytail-audit",
            "ponytail-debt",
            "ponytail-gain",
            "ponytail-help",
            "ponytail-review",
            "diagnosing-bugs",
        ]
    },
    **{
        s: "content"
        for s in [
            "khazix-writer",
            "content-research-writer",
            "hv-analysis",
        ]
    },
    **{
        s: "persona"
        for s in [
            "tong-jincheng-skill",
            "zhangxuefeng-skill",
            "using-coze-cli",
        ]
    },
    **{
        s: "runbook"
        for s in [
            "dbs-troubleshoot",
            "git-guardrails-claude-code",
            "grill-me",
            "grilling",
        ]
    },
    **{
        s: "tools"
        for s in [
            "lit-search",
            "neat-freak",
            "notebooklm",
            "ppt-master",
            "skill-curator",
            "storage-analyzer",
            "cache-cleanup",
            "ccswitch",
            "aihot",
            "humanities-guard",
            "libreoffice-calc",
            "libreoffice-writer",
            "skill-router",
            "skill-search",
        ]
    },
    "s4h": "thinking",
    "dbs": "thinking",
}

# ── Data model ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """A single skill registry entry.

    Attributes match the JSON schema written to ``index.json``.
    """

    name: str
    description: str
    domain: str
    group: str
    type: str
    path: str
    is_bridge: bool
    source_of_truth: str | None = None
    trigger_patterns: str | None = None
    score: float = field(default=0.0, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to the registry JSON format."""
        data: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "group": self.group,
            "type": self.type,
            "path": self.path,
            "is_bridge": self.is_bridge,
        }
        if self.source_of_truth is not None:
            data["source_of_truth"] = self.source_of_truth
        if self.trigger_patterns is not None:
            data["trigger_patterns"] = self.trigger_patterns
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillEntry:
        """Deserialize from a registry dict, validating required fields."""
        required = {"name", "description", "domain", "group", "type", "path"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"Registry entry missing required fields: {sorted(missing)}")

        return cls(
            name=str(data["name"]),
            description=str(data.get("description", "")),
            domain=str(data.get("domain", "other")),
            group=str(data.get("group", "infra")),
            type=str(data.get("type", "other")),
            path=str(data["path"]),
            is_bridge=bool(data.get("is_bridge", False)),
            source_of_truth=_optional_str(data.get("source_of_truth")),
            trigger_patterns=_optional_str(data.get("trigger_patterns")),
        )


def _optional_str(value: Any) -> str | None:
    """Coerce a value to str or None if absent/empty."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


# ── Taxonomy helpers ──────────────────────────────────────────────────────────


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


def get_group(name: str, *, skill_type: str = "") -> str:
    """Map skill to high-level group for routing."""
    if name in GROUP_SKILLS:
        return GROUP_SKILLS[name]
    if name.startswith("s4h-"):
        return "thinking"
    if name.startswith("dbs-"):
        return "thinking"
    if skill_type == "tool":
        return "tools"
    if skill_type == "plugin":
        return "persona"
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
        "lit-search",
        "neat-freak",
        "notebooklm",
        "ppt-master",
        "skill-curator",
        "storage-analyzer",
        "cache-cleanup",
        "ccswitch",
        "aihot",
        "content-research-writer",
        "hv-analysis",
        "khazix-writer",
        "humanities-guard",
    }
    if name in tool_names:
        return "tool"
    plugin_names = {"tong-jincheng-skill", "zhangxuefeng-skill", "using-coze-cli"}
    if name in plugin_names:
        return "plugin"
    return "other"


# ── Frontmatter parsing ───────────────────────────────────────────────────────

# Match a frontmatter field line: key: value or key: block-scalar-marker
_FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


class FrontmatterParseError(ValueError):
    """Raised when frontmatter cannot be parsed."""


_FRONTMATTER_FIELDS = {"description", "source_of_truth", "trigger_patterns"}


def extract_frontmatter(content: str) -> dict[str, str]:
    """Extract selected YAML frontmatter fields from SKILL.md content.

    Parses a *minimal* YAML subset: plain scalars, double/single quoted
    scalars, folded blocks (``>``), and literal blocks (``|``).  Comments
    and unknown fields are ignored.  The parser is intentionally
    zero-dependency so the package remains dependency-free.
    """
    result: dict[str, str] = {}
    if not content.startswith("---"):
        return result

    # Split on the closing '---' delimiter.  Only the first frontmatter
    # block is considered.
    parts = re.split(r"\n---\s*\n", content, maxsplit=1)
    if len(parts) < 2:
        return result

    fm = parts[0][3:].strip()
    if not fm:
        return result

    lines = fm.splitlines()
    idx = 0
    while idx < len(lines):
        raw = lines[idx]
        stripped = raw.strip()

        # Skip blanks and YAML comments.
        if not stripped or stripped.startswith("#"):
            idx += 1
            continue

        match = _FIELD_RE.match(raw)
        if not match:
            idx += 1
            continue

        key, rest = match.groups()
        if key not in _FRONTMATTER_FIELDS:
            idx += 1
            continue

        if rest in (">", "|"):
            idx, value = _consume_block_scalar(lines, idx + 1, preserve_newlines=(rest == "|"))
        elif rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            value = rest[1:-1]
            idx += 1
        elif rest.startswith("'") and rest.endswith("'") and len(rest) >= 2:
            value = rest[1:-1]
            idx += 1
        else:
            value = rest
            idx += 1

        if value:
            result[key] = value

    return result


def _consume_block_scalar(
    lines: list[str], start: int, *, preserve_newlines: bool
) -> tuple[int, str]:
    """Consume indented continuation lines for a YAML block scalar.

    Returns the next line index and the scalar value.
    """
    block: list[str] = []
    idx = start
    while idx < len(lines):
        line = lines[idx]
        if line and not line[0].isspace():
            break
        block.append(line)
        idx += 1

    if not block:
        return idx, ""

    # Determine the base indentation from the first non-empty line and
    # strip it from every line.
    nonempty = [line for line in block if line.strip()]
    base_indent = min(len(line) - len(line.lstrip()) for line in nonempty) if nonempty else 0
    stripped = [line[base_indent:] if line.strip() else line for line in block]

    if preserve_newlines:
        value = "\n".join(line.rstrip() for line in stripped)
    else:
        value = " ".join(line.strip() for line in stripped if line.strip())

    return idx, value.strip()


# ── Directory scanning ────────────────────────────────────────────────────────


def scan_directory(skills_dir: Path) -> dict[str, SkillEntry]:
    """Scan a skills directory for SKILL.md files and build registry entries.

    Errors (permission, encoding) are skipped with a warning — one bad
    file shouldn't break the entire scan.
    """
    registry: dict[str, SkillEntry] = {}

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

        try:
            frontmatter = extract_frontmatter(content)
        except FrontmatterParseError as e:
            print(f"  [WARN] Could not parse frontmatter for {name}: {e}", flush=True)
            frontmatter = {}

        description = frontmatter.get("description", "")
        source_of_truth = frontmatter.get("source_of_truth")
        trigger_patterns = frontmatter.get("trigger_patterns")
        is_bridge = source_of_truth is not None

        domain = get_domain(name)
        skill_type = get_type(name)
        group = get_group(name, skill_type=skill_type)

        registry[name] = SkillEntry(
            name=name,
            description=description,
            domain=domain,
            group=group,
            type=skill_type,
            path=str(skill_md.resolve()),
            is_bridge=is_bridge,
            source_of_truth=source_of_truth,
            trigger_patterns=trigger_patterns,
        )

    return registry


# ── Registry generation ───────────────────────────────────────────────────────


def generate_registry(
    skill_dirs: list[Path] | None = None,
    output_path: Path | None = None,
) -> dict[str, SkillEntry]:
    """Generate the skill registry from one or more skill directories.

    Args:
        skill_dirs: List of directories to scan. Defaults to
            ~/.claude/skills/ and ~/.codex/skills/.
        output_path: If provided, write JSON to this path.

    Returns:
        The complete registry dict mapping skill name to ``SkillEntry``.
    """
    if skill_dirs is None:
        skill_dirs = [
            Path.home() / ".claude" / "skills",
            Path.home() / ".codex" / "skills",
        ]

    registry: dict[str, SkillEntry] = {}
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
            json.dumps(
                {name: entry.to_dict() for name, entry in registry.items()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    return registry


def load_registry(path: Path) -> dict[str, SkillEntry]:
    """Load and validate a registry JSON file.

    Raises:
        FileNotFoundError: If the registry file does not exist.
        ValueError: If the file is corrupted or has an invalid format.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Registry not found: {path}")

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Registry file is corrupted: {path}\n  {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Invalid registry format in: {path}")

    registry: dict[str, SkillEntry] = {}
    for name, entry_data in data.items():
        if not isinstance(entry_data, dict):
            raise ValueError(f"Invalid entry for skill '{name}' in {path}")
        try:
            registry[name] = SkillEntry.from_dict(entry_data)
        except ValueError as e:
            raise ValueError(f"Invalid entry for skill '{name}' in {path}: {e}") from e

    return registry
