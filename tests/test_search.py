"""Tests for the search engine."""

from __future__ import annotations

import pytest

from skill_router.registry import SkillEntry
from skill_router.search import _tokenize, search


def _entry(
    name: str,
    description: str,
    domain: str,
    group: str,
    skill_type: str,
    is_bridge: bool = False,
) -> SkillEntry:
    return SkillEntry(
        name=name,
        description=description,
        domain=domain,
        group=group,
        type=skill_type,
        path=f"/tmp/skills/{name}/SKILL.md",
        is_bridge=is_bridge,
    )


class TestTokenize:
    def test_english_words(self):
        tokens = _tokenize("debug code review")
        assert "debug" in tokens
        assert "code" in tokens
        assert "review" in tokens

    def test_english_strips_punctuation(self):
        tokens = _tokenize("review, code.")
        assert "review" in tokens
        assert "code" in tokens
        assert "," not in tokens
        assert "." not in tokens

    def test_chinese_bigrams(self):
        tokens = _tokenize("逻辑检查")
        assert any("逻辑" in t for t in tokens)

    def test_chinese_keyword_translation(self):
        tokens = _tokenize("头脑风暴")
        assert "brainstorm" in tokens
        assert "creativity" in tokens

    def test_mixed_query(self):
        tokens = _tokenize("debug 逻辑错误")
        assert "debug" in tokens
        assert "logic" in tokens  # translated from 逻辑

    def test_empty_query(self):
        assert _tokenize("") == []
        assert _tokenize("   ") == []

    def test_deduplication(self):
        tokens = _tokenize("逻辑 逻辑")
        assert tokens.count("logic") == 1


class TestSearch:
    @pytest.fixture
    def sample_registry(self):
        return {
            "code-review": _entry(
                "code-review",
                "Review code for bugs and style issues",
                "coding",
                "coding",
                "tool",
            ),
            "s4h-logic-check": _entry(
                "s4h-logic-check",
                "Check argument logic and reasoning validity",
                "logic",
                "thinking",
                "s4h",
            ),
            "ppt-master": _entry(
                "ppt-master",
                "Create beautiful presentations",
                "tool",
                "tools",
                "tool",
            ),
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

    def test_top_zero_returns_empty(self, sample_registry):
        results = search("code-review", sample_registry, top=0)
        assert results == []

    def test_negative_top_raises(self, sample_registry):
        with pytest.raises(ValueError):
            search("code-review", sample_registry, top=-1)

    def test_chinese_search(self, sample_registry):
        # "逻辑" → ["logic", "reasoning"]
        results = search("逻辑", sample_registry)
        assert len(results) >= 1
        assert results[0]["name"] == "s4h-logic-check"

    def test_filter_is_case_insensitive(self, sample_registry):
        results = search("review", sample_registry, group="CODING")
        assert len(results) == 1
        assert results[0]["name"] == "code-review"

    def test_results_sorted_by_score(self, sample_registry):
        results = search("code review", sample_registry)
        assert results[0]["score"] >= results[-1]["score"]
