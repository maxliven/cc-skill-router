# Changelog

All notable changes to cc-skill-router will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-07-22

### Added
- Public Python API: `SkillRouter` and `SkillMatch` classes in `skill_router.__init__`.
- `SkillEntry` dataclass with schema validation in `registry.py`.
- `load_registry()` function for typed, validated registry loading.
- Comprehensive test suite: `test_search.py`, `test_registry.py`, `test_cli.py`, `test_router.py`.
- `py.typed` marker for PEP 561 type information.
- Python 3.13 support.
- MyPy configuration in `pyproject.toml`.

### Changed
- **BREAKING**: `search()` now accepts `dict[str, SkillEntry]` instead of raw dicts.
- Refactored frontmatter parser to be more robust while remaining zero-dependency.
- Pre-computed Chinese keyword ordering for better search performance.
- Improved CJK bigram extraction: only pairs of CJK characters are included.
- English tokenization now strips punctuation.
- Filters (domain/group/type) are now case-insensitive.
- CLI argument parsing refactored with shared helper functions.
- Moved bundled `skills/skill-router/SKILL.md` into `skill_router/skills/` so it is included in wheels.

### Fixed
- `skill-router init` now works from packaged wheels via `importlib.resources`.
- `_load_registry` no longer returns unvalidated raw dicts; schema validation prevents `KeyError` at runtime.
- `search()` now validates that `top` is non-negative.
- `cmd_list` now prints a friendly message when filters match no skills.

## [Unreleased]

*No unreleased changes yet.*

## [0.1.1] - 2026-07-03

### Fixed
- CI workflow: use `uv sync` instead of bare `uv pip install`
- Various UX improvements

## [0.1.0] - 2026-06-30

### Added
- 3-stage semantic routing: direct match → domain filter → full search
- Bilingual search engine with CJK bigram fuzzy matching
- 100+ Chinese→English keyword mapping table
- CLI: `search`, `list`, `scan`, `init` commands
- Zero-dependency design (stdlib only)
- Skill registry with JSON persistence
- 7 skill domain groups (thinking, coding, tools, content, persona, runbook, infra)
