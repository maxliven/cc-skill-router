"""Tests for the CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_router.cli import main


class TestCLI:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        captured = capsys.readouterr()
        assert "skill-router" in captured.out

    def test_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Available commands" in captured.out

    def test_init(self, tmp_path: Path, capsys):
        target = tmp_path / "skills" / "skill-router"
        main(["init", str(target)])
        assert (target / "SKILL.md").is_file()

    def test_scan(self, tmp_path: Path, capsys):
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Review code\n---\n", encoding="utf-8"
        )
        output = tmp_path / "index.json"
        main(["scan", "-d", str(tmp_path), "-o", str(output)])
        assert output.is_file()

    def test_search(self, tmp_path: Path, capsys):
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
        registry = tmp_path / "index.json"
        registry.write_text(json.dumps(data), encoding="utf-8")
        main(["search", "review", "-r", str(registry), "-f", "json"])
        captured = capsys.readouterr()
        assert "code-review" in captured.out

    def test_search_missing_registry(self, tmp_path: Path, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["search", "review", "-r", str(tmp_path / "missing.json")])
        assert exc.value.code == 1

    def test_list(self, tmp_path: Path, capsys):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        registry = tmp_path / "index.json"
        registry.write_text(json.dumps(data), encoding="utf-8")
        main(["list", "-r", str(registry)])
        captured = capsys.readouterr()
        assert "code-review" in captured.out

    def test_list_filter_no_match(self, tmp_path: Path, capsys):
        data = {
            "code-review": {
                "name": "code-review",
                "description": "Review code",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            }
        }
        registry = tmp_path / "index.json"
        registry.write_text(json.dumps(data), encoding="utf-8")
        main(["list", "-r", str(registry), "-g", "thinking"])
        captured = capsys.readouterr()
        assert "No skills match" in captured.out
