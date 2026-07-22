"""Tests for the registry generator and frontmatter parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_router.registry import (
    SkillEntry,
    extract_frontmatter,
    generate_registry,
    get_domain,
    get_group,
    get_type,
    load_registry,
    scan_directory,
)


class TestExtractFrontmatter:
    def test_plain_scalar(self):
        content = "---\ndescription: A short description\n---\n# Body"
        fm = extract_frontmatter(content)
        assert fm["description"] == "A short description"

    def test_double_quoted_scalar(self):
        content = '---\ndescription: "A short description"\n---\n'
        fm = extract_frontmatter(content)
        assert fm["description"] == "A short description"

    def test_single_quoted_scalar(self):
        content = "---\ndescription: 'A short description'\n---\n"
        fm = extract_frontmatter(content)
        assert fm["description"] == "A short description"

    def test_folded_block(self):
        content = "---\ndescription: >\n  A multi-line\n  folded description\n---\n"
        fm = extract_frontmatter(content)
        assert fm["description"] == "A multi-line folded description"

    def test_literal_block(self):
        content = "---\ndescription: |\n  Line one\n  Line two\n---\n"
        fm = extract_frontmatter(content)
        assert fm["description"] == "Line one\nLine two"

    def test_source_of_truth(self):
        content = "---\nsource_of_truth: /path/to/file.md\n---\n"
        fm = extract_frontmatter(content)
        assert fm["source_of_truth"] == "/path/to/file.md"

    def test_no_frontmatter(self):
        assert extract_frontmatter("# Just markdown") == {}

    def test_comments_ignored(self):
        content = "---\n# A comment\ndescription: value\n---\n"
        fm = extract_frontmatter(content)
        assert fm["description"] == "value"


class TestTaxonomyHelpers:
    def test_get_domain_s4h_prefix(self):
        assert get_domain("s4h-creativity-brainstorm") == "creativity"

    def test_get_domain_dbs_prefix(self):
        assert get_domain("dbs-diagnosis") == "dbs"

    def test_get_domain_ponytail_prefix(self):
        assert get_domain("ponytail-review") == "ponytail"

    def test_get_domain_override(self):
        assert get_domain("lit-search") == "tool"

    def test_get_domain_fallback(self):
        assert get_domain("my-custom-skill") == "other"

    def test_get_group_s4h(self):
        assert get_group("s4h-logic-check") == "thinking"

    def test_get_group_named(self):
        assert get_group("code-review") == "coding"

    def test_get_group_by_type(self):
        assert get_group("lit-search", skill_type="tool") == "tools"

    def test_get_type_s4h(self):
        assert get_type("s4h-logic-check") == "s4h"

    def test_get_type_tool(self):
        assert get_type("lit-search") == "tool"

    def test_get_type_plugin(self):
        assert get_type("zhangxuefeng-skill") == "plugin"


class TestSkillEntry:
    def test_to_dict_roundtrip(self):
        entry = SkillEntry(
            name="code-review",
            description="Review code",
            domain="coding",
            group="coding",
            type="tool",
            path="/tmp/skills/code-review/SKILL.md",
            is_bridge=True,
            source_of_truth="/path/to/skill.md",
        )
        data = entry.to_dict()
        assert data["name"] == "code-review"
        assert data["is_bridge"] is True
        assert data["source_of_truth"] == "/path/to/skill.md"

    def test_from_dict_validates_required_fields(self):
        with pytest.raises(ValueError):
            SkillEntry.from_dict({"name": "incomplete"})


class TestScanDirectory:
    def test_empty_directory(self, tmp_path: Path):
        assert scan_directory(tmp_path) == {}

    def test_skips_entries_without_skill_md(self, tmp_path: Path):
        (tmp_path / "empty-skill").mkdir()
        assert scan_directory(tmp_path) == {}

    def test_parses_skill_md(self, tmp_path: Path):
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Review code for issues\n---\n# Code Review\n",
            encoding="utf-8",
        )
        registry = scan_directory(tmp_path)
        assert "code-review" in registry
        assert registry["code-review"].description == "Review code for issues"


class TestGenerateRegistry:
    def test_generates_registry_for_single_directory(self, tmp_path: Path):
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Review code\n---\n", encoding="utf-8"
        )
        registry = generate_registry(skill_dirs=[tmp_path])
        assert "code-review" in registry

    def test_writes_json_output(self, tmp_path: Path):
        skill_dir = tmp_path / "code-review"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: Review code\n---\n", encoding="utf-8"
        )
        output = tmp_path / "index.json"
        generate_registry(skill_dirs=[tmp_path], output_path=output)
        data = json.loads(output.read_text(encoding="utf-8"))
        assert "code-review" in data

    def test_missing_directories_are_skipped(self, tmp_path: Path, capsys):
        missing = tmp_path / "does-not-exist"
        registry = generate_registry(skill_dirs=[missing])
        assert registry == {}


class TestLoadRegistry:
    def test_loads_valid_registry(self, tmp_path: Path):
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
        path = tmp_path / "index.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        registry = load_registry(path)
        assert "code-review" in registry
        assert registry["code-review"].description == "Review code"

    def test_raises_on_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path / "missing.json")

    def test_raises_on_corrupted_json(self, tmp_path: Path):
        path = tmp_path / "index.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError):
            load_registry(path)

    def test_raises_on_invalid_entry(self, tmp_path: Path):
        path = tmp_path / "index.json"
        path.write_text(json.dumps({"bad": {"name": "bad"}}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_registry(path)
