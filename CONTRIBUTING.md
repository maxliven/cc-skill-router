# Contributing

Thanks for considering contributing to cc-skill-router!

## Setup

```bash
git clone https://github.com/maxliven/cc-skill-router.git
cd cc-skill-router
pip install -e ".[dev]"
```

## Development

### Code Quality

```bash
ruff check . && ruff format .
```

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
cc-skill-router/
├── skill_router/       # Core package
│   ├── __init__.py     # SkillRouter public API
│   ├── cli.py          # CLI (click-free, stdlib argparse)
│   ├── registry.py     # Skill registry (JSON-backed)
│   └── search.py       # Search engine + CN_KEYWORD_MAP
├── tests/              # Test suite
├── skills/             # Bundled skill definitions
├── pyproject.toml
└── README.md
```

## Pull Request Guidelines

- Write a clear description of the change and why it's needed
- Link to any related issues
- Add or update tests for the changed behavior
- Run `ruff check . && ruff format .` before committing
- Run `pytest tests/ -v` and ensure all pass

## Adding Chinese Keywords

Edit `skill_router/search.py` → `CN_KEYWORD_MAP`. Add your domain-specific terms following the existing pattern:

```python
"中文词": ["english", "keywords", "here"],
```

Each Chinese key maps to a list of English terms that appear in skill names or descriptions.
