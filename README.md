# cc-skill-router

**Semantic skill router for Claude Code.** Scans your skill directories, builds a searchable registry, and provides bilingual (Chinese/English) fuzzy search to route user requests to the best matching skill — so you don't have to remember 200+ skill names.

## The Problem

You've built a library of Claude Code skills. Maybe 50, maybe 200. Each one does something specific. But when a user says "帮我检查一下这段逻辑有没有漏洞," which skill handles that? `s4h-logic-check`? `s4h-logic-consistency-check`? `s4h-ethics-check`?

Scanning a giant skill list by hand is slow. Grep only gets you so far — it can't understand that "润色" means `s4h-writing-line-editing`, or that "头脑风暴" should route to `s4h-creativity-brainstorm`.

**cc-skill-router** solves this with a 3-stage semantic routing strategy:
1. **Direct match** — ~25 memorized high-frequency skills, instant routing
2. **Domain-filtered search** — narrow by group (thinking/coding/tools/…), then fuzzy match
3. **Full-registry search** — bilingual semantic search across all skills

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                   User Request                        │
│         "帮我检查这段论证有没有逻辑漏洞"                 │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 1: High-Frequency Direct Match                │
│  "论证" + "逻辑" + "检查" → s4h-logic-check ✓        │
│  (Matched from memorized ~25 high-frequency skills)  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 2: Domain-Filtered Search (fallback)          │
│  skill-router search "论证 逻辑 检查" -g thinking     │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│  Stage 3: Full-Registry Search (fallback)            │
│  skill-router search "论证 逻辑 检查" -n 5            │
└─────────────────────────────────────────────────────┘
```

## Installation

### 1. Install the CLI tool

```bash
pip install git+https://github.com/maxliven/cc-skill-router.git
```

Or with uv:

```bash
uv pip install git+https://github.com/maxliven/cc-skill-router.git
```

Requires Python ≥ 3.10. **Zero dependencies** beyond the standard library.

### 2. Install the Claude Code skill

Copy the skill definition into your Claude Code skills directory:

```bash
# From the repo
cp -r skills/skill-router ~/.claude/skills/skill-router
```

### 3. Generate your registry

```bash
skill-router scan
```

This scans `~/.claude/skills/` and `~/.codex/skills/`, extracts frontmatter from every `SKILL.md`, and builds `~/.ai-shared/skills/.registry/index.json`.

### 4. Configure CLAUDE.md (optional but recommended)

Add the routing strategy to your `CLAUDE.md` so Claude Code automatically uses the router:

```markdown
## Skill Routing

When a user request might map to an existing skill:
1. Match against memorized high-frequency skills first
2. If no match, run: `skill-router search "<user query>" -g <group> -n 5`
3. Score ≥ 6 → use the skill; 3-5 → read SKILL.md to confirm; <3 → no match
```

## Usage

### CLI Commands

```bash
# Generate/re-generate the registry
skill-router scan
skill-router scan -d ~/.claude/skills -o ./my-registry.json
skill-router scan -v              # Verbose: show group breakdown

# Search for skills
skill-router search "逻辑检查"
skill-router search "brainstorm creative ideas" -n 10
skill-router search "润色文章" -g thinking
skill-router search "debug" -g coding -f json

# List all skills
skill-router list
skill-router list -g tools
skill-router list -d ethics -f json
```

### Search Examples

```bash
$ skill-router search "论证逻辑检查"

┌─ Skill Search (5 matches) ────────────────────────────────────┐
│                                                                │
│ [1] s4h-logic-check (logic)                                    │
│    Score: 8.5/10    Type: s4h                                  │
│    Check argument logic consistency, reasoning validity, ...   │
│                                                                │
│ [2] s4h-logic-consistency-check (logic)                        │
│    Score: 7.2/10    Type: s4h                                  │
│    Deep consistency audit across claims, assumptions, and ...  │
│                                                                │
│ [3] s4h-logic-argument-validation (logic)                      │
│    Score: 6.8/10    Type: s4h                                  │
│    Validate argument structure: premises, warrants, conclu...  │
└────────────────────────────────────────────────────────────────┘
```

```bash
$ skill-router search "头脑风暴" -f json
```

```json
[
  {
    "name": "s4h-creativity-brainstorm",
    "description": "Run an orchestrated multi-method creative thinking sprint...",
    "domain": "creativity",
    "group": "thinking",
    "type": "s4h",
    "score": 9.2
  }
]
```

## How the Search Works

The search engine uses a **bilingual tokenization + weighted scoring** approach:

### Tokenization
1. **English words** — extracted directly from the query
2. **CJK bigrams** — consecutive CJK character pairs for fuzzy Chinese matching
3. **CJK singles** — individual CJK characters as low-weight fallback signals
4. **Chinese→English translation** — longest-match-first against a 100+ entry keyword map (e.g., "头脑风暴" → ["brainstorm", "creativity"])

### Scoring
| Match location | Weight (multi-char) | Weight (single-char) |
|---------------|--------------------|--------------------|
| Skill **name** | 3.0 | 1.5 |
| Skill **domain** | 2.0 | 1.0 |
| **Description** / type | 1.5 | 0.3 |

Scores are capped at 10.0. Results sorted descending, top N returned.

## Registry Format

The registry is a JSON file mapping skill names to metadata:

```json
{
  "s4h-creativity-brainstorm": {
    "name": "s4h-creativity-brainstorm",
    "description": "Run an orchestrated multi-method creative thinking sprint...",
    "domain": "creativity",
    "group": "thinking",
    "type": "s4h",
    "path": "/home/user/.claude/skills/s4h-creativity-brainstorm/SKILL.md",
    "is_bridge": false
  }
}
```

Each SKILL.md should have YAML frontmatter with at least a `description` field:

```markdown
---
name: my-skill
description: "What this skill does and when to use it."
---
```

## Skill Groups

The router uses 7 high-level groups for domain filtering:

| Group | Description | Examples |
|-------|-------------|---------|
| `thinking` | Analysis, creativity, logic, decision, ethics, strategy, writing, systems | s4h-*, dbs-* |
| `coding` | Code review, debugging, refactoring, architecture | ponytail, code-review |
| `tools` | External tools and utilities | lit-search, ppt-master, notebooklm |
| `content` | Content creation and research | khazix-writer, content-research-writer |
| `persona` | Role-play and style simulation | zhangxuefeng-skill |
| `runbook` | Troubleshooting and incident response | dbs-troubleshoot, diagnosing-bugs |
| `infra` | System maintenance and configuration | cache-cleanup, storage-analyzer |

## Customization

### Custom skill directories

```bash
skill-router scan -d /path/to/my/skills /another/path -o ./index.json
```

### Custom domain/group mapping

Edit `skill_router/registry.py` — the `DOMAIN_OVERRIDES` and `GROUP_SKILLS` dicts are designed to be modified. Or better: define your skills with descriptive names and let the inference rules handle it:

- `s4h-<domain>-*` → domain = `<domain>`, group = `thinking`
- `dbs-*` → domain = `dbs`, group = `thinking`
- `ponytail*` → domain = `ponytail`, group = `coding`

### Custom keyword map

Edit `skill_router/search.py` — the `CN_KEYWORD_MAP` dict. Add your domain-specific Chinese terms and their English equivalents.

## Design Principles

- **Zero dependencies.** Standard library only. No pip install cascade.
- **Model-agnostic.** Works with any skill collection — s4h, dbs, custom, whatever.
- **Human-readable registry.** Plain JSON. Diff it, grep it, version-control it.
- **No API keys, no telemetry, no network calls.** Everything runs locally.
- **Bilingual first.** Chinese and English are both first-class query languages.

## License

MIT — see [LICENSE](LICENSE) file.

## Related

- [cn-llm-bridge](https://github.com/maxliven/cn-llm-bridge) — MCP bridge for multi-model orchestration (Qwen vision, faster-whisper, Kimi K2)
- [Claude Code](https://claude.ai/code) — Anthropic's CLI for Claude
