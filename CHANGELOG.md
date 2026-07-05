# Changelog

All notable changes to cc-skill-router will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- CI badge, Mermaid architecture diagram, and Python API section in README
- Ecosystem footer linking to cn-llm-bridge

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
