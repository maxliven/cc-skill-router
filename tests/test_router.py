"""Tests for the high-level SkillRouter API."""

from __future__ import annotations

import json
from pathlib import Path

from skill_router import SkillRouter


class TestSkillRouter:
    def test_load_empty_registry(self, tmp_path: Path):
        router = SkillRouter(registry_path=tmp_path / "missing.json")
        assert router.registry == {}

    def test_load_valid_registry(self, tmp_path: Path):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code for issues",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        path = tmp_path / "index.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        router = SkillRouter(registry_path=path)
        assert "code-review" in router.registry

    def test_search_returns_matches(self, tmp_path: Path):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code for issues",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        path = tmp_path / "index.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        router = SkillRouter(registry_path=path)
        matches = router.search("review")
        assert len(matches) == 1
        assert matches[0].skill_id == "code-review"
        assert matches[0].score > 0

    def test_route_returns_best_match(self, tmp_path: Path):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code for issues",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        path = tmp_path / "index.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        router = SkillRouter(registry_path=path)
        best = router.route("review code")
        assert best is not None
        assert best.skill_id == "code-review"

    def test_route_with_threshold_filters_low_scores(self, tmp_path: Path):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code for issues",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        path = tmp_path / "index.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        router = SkillRouter(registry_path=path)
        assert router.route("completely unrelated", threshold=100.0) is None

    def test_build_generates_registry(self, tmp_path: Path):
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Review code\n---\n", encoding="utf-8"
        )
        output = tmp_path / "index.json"
        router = SkillRouter(registry_path=output)
        router.build(skill_dirs=[tmp_path])
        assert "code-review" in router.registry
        assert output.is_file()

    def test_route_no_match(self, tmp_path: Path):
        path = tmp_path / "index.json"
        path.write_text("{}", encoding="utf-8")
        router = SkillRouter(registry_path=path)
        assert router.route("anything") is None
