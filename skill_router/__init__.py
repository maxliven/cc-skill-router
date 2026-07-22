"""cc-skill-router — Semantic skill router for Claude Code.

Scans skill directories, builds a searchable registry, and provides
bilingual (Chinese/English) fuzzy search to route user requests to
the best matching skill.
"""

from __future__ import annotations

__version__ = "0.2.0"

from dataclasses import dataclass
from pathlib import Path

from .registry import DEFAULT_REGISTRY_PATH, SkillEntry, generate_registry, load_registry
from .search import search as _search


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """A single skill match returned by the router.

    Attributes:
        name: Skill identifier (same as skill_id).
        description: Short description from SKILL.md frontmatter.
        score: Match score from 0.0 to 10.0.
        domain: Inferred skill domain.
        group: High-level routing group.
        type: Skill type (s4h, dbs, ponytail, tool, plugin, other).
        path: Absolute path to the skill's SKILL.md file.
        is_bridge: Whether the skill declares a source_of_truth.
        source_of_truth: Optional path to the skill's canonical source.
    """

    name: str
    description: str
    score: float
    domain: str
    group: str
    type: str
    path: str
    is_bridge: bool
    source_of_truth: str | None = None

    @property
    def skill_id(self) -> str:
        """Alias for name."""
        return self.name


class SkillRouter:
    """High-level router for Claude Code skills.

    Loads a skill registry (generating one if needed) and exposes
    ``search`` / ``route`` methods for programmatic use.
    """

    def __init__(self, registry_path: Path | str | None = None) -> None:
        """Initialize the router.

        Args:
            registry_path: Path to the registry JSON. Defaults to
                ``~/.skill-router/index.json``.
        """
        self.registry_path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
        self._registry: dict[str, SkillEntry] | None = None

    @property
    def registry(self) -> dict[str, SkillEntry]:
        """Lazy-load the registry."""
        if self._registry is None:
            self._registry = self._load()
        return self._registry

    def _load(self) -> dict[str, SkillEntry]:
        """Load the registry from disk, or return an empty dict."""
        try:
            return load_registry(self.registry_path)
        except (FileNotFoundError, ValueError):
            return {}

    def build(
        self,
        skill_dirs: list[str | Path] | None = None,
        *,
        output_path: Path | str | None = None,
    ) -> SkillRouter:
        """Generate (or regenerate) the registry and reload it.

        Args:
            skill_dirs: Directories to scan. Defaults to
                ``~/.claude/skills`` and ``~/.codex/skills``.
            output_path: Where to write the registry. Defaults to
                ``self.registry_path``.

        Returns:
            Self for chaining.
        """
        dirs = [Path(d) for d in skill_dirs] if skill_dirs else None
        out = Path(output_path) if output_path else self.registry_path
        self._registry = generate_registry(skill_dirs=dirs, output_path=out)
        self.registry_path = out
        return self

    def search(
        self,
        query: str,
        *,
        n: int = 5,
        domain: str = "",
        group: str = "",
        skill_type: str = "",
    ) -> list[SkillMatch]:
        """Search the registry for matching skills.

        Args:
            query: Chinese or English query.
            n: Maximum number of results.
            domain: Optional domain filter.
            group: Optional group filter.
            skill_type: Optional type filter.

        Returns:
            List of matching skills, sorted by score descending.
        """
        raw = _search(
            query=query,
            registry=self.registry,
            top=n,
            domain=domain,
            group=group,
            skill_type=skill_type,
        )
        return [SkillMatch(**entry) for entry in raw]

    def route(
        self,
        query: str,
        *,
        domain: str = "",
        group: str = "",
        skill_type: str = "",
        threshold: float = 0.0,
    ) -> SkillMatch | None:
        """Route a request to the single best matching skill.

        Args:
            query: User request.
            domain: Optional domain filter.
            group: Optional group filter.
            skill_type: Optional type filter.
            threshold: Minimum score to return a match.

        Returns:
            The best matching skill, or ``None`` if no match exceeds
            the threshold.
        """
        matches = self.search(
            query=query,
            n=1,
            domain=domain,
            group=group,
            skill_type=skill_type,
        )
        if not matches:
            return None
        best = matches[0]
        return best if best.score >= threshold else None


__all__ = [
    "__version__",
    "SkillMatch",
    "SkillRouter",
    "DEFAULT_REGISTRY_PATH",
    "generate_registry",
]
