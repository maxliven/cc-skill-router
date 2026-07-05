"""Smoke tests for the search engine."""

import pytest

from skill_router.search import _tokenize, search


class TestTokenize:
    def test_english_words(self):
        tokens = _tokenize("debug code review")
        assert "debug" in tokens
        assert "code" in tokens
        assert "review" in tokens

    def test_chinese_bigrams(self):
        tokens = _tokenize("逻辑检查")
        # Should include bigrams like "逻辑", "辑检", "检查"
        assert any("逻辑" in t for t in tokens)

    def test_chinese_keyword_translation(self):
        tokens = _tokenize("头脑风暴")
        # "头脑风暴" should translate to ["brainstorm", "creativity"]
        assert "brainstorm" in tokens
        assert "creativity" in tokens

    def test_mixed_query(self):
        tokens = _tokenize("debug 逻辑错误")
        assert "debug" in tokens
        assert "logic" in tokens  # translated from 逻辑


class TestSearch:
    @pytest.fixture
    def sample_registry(self):
        return {
            "code-review": {
                "name": "code-review",
                "description": "Review code for bugs and style issues",
                "domain": "coding",
                "group": "coding",
                "type": "tool",
                "path": "/tmp/skills/code-review/SKILL.md",
                "is_bridge": False,
            },
            "s4h-logic-check": {
                "name": "s4h-logic-check",
                "description": "Check argument logic and reasoning validity",
                "domain": "logic",
                "group": "thinking",
                "type": "s4h",
                "path": "/tmp/skills/s4h-logic-check/SKILL.md",
                "is_bridge": False,
            },
            "ppt-master": {
                "name": "ppt-master",
                "description": "Create beautiful presentations",
                "domain": "tool",
                "group": "tools",
                "type": "tool",
                "path": "/tmp/skills/ppt-master/SKILL.md",
                "is_bridge": False,
            },
        }

    def test_exact_name_match(self, sample_registry):
        results = search("code-review", sample_registry)
        assert len(results) >= 1
        assert results[0]["name"] == "code-review"
        assert results[0]["score"] >= 3.0

    def test_description_match(self, sample_registry):
        results = search("beautiful presentations", sample_registry)
        assert len(results) >= 1
        assert results[0]["name"] == "ppt-master"

    def test_domain_filter(self, sample_registry):
        results = search("check", sample_registry, domain="logic")
        assert len(results) == 1
        assert results[0]["name"] == "s4h-logic-check"

    def test_group_filter(self, sample_registry):
        results = search("review", sample_registry, group="coding")
        assert len(results) == 1
        assert results[0]["name"] == "code-review"

    def test_no_match(self, sample_registry):
        results = search("xyzzy_nonexistent_12345", sample_registry)
        assert len(results) == 0

    def test_top_limit(self, sample_registry):
        results = search("a", sample_registry, top=2)
        assert len(results) <= 2

    def test_chinese_search(self, sample_registry):
        # "逻辑" → ["logic", "reasoning"]
        results = search("逻辑", sample_registry)
        assert len(results) >= 1
        assert results[0]["name"] == "s4h-logic-check"
