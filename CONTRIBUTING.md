# Contributing

Thanks for considering contributing to cc-skill-router!

## Setup

```bash
git clone https://github.com/maxliven/cc-skill-router.git
cd cc-skill-router
pip install -e ".[dev]"
```

We use [uv](https://github.com/astral-sh/uv) in CI, but plain `pip` works fine for local development.

## Development

### Code Quality

```bash
ruff check skill_router/ tests/
ruff format --check skill_router/ tests/
```

To auto-format:

```bash
ruff format skill_router/ tests/
```

### Running Tests

```bash
pytest tests/ -v
```

With coverage:

```bash
pytest tests/ -v --cov=skill_router --cov-report=term
```

### Type Checking

We aim for full type coverage. If you have `mypy` installed:

```bash
mypy skill_router/
```

### Project Structure

```
cc-skill-router/
├── skill_router/           # Core package
│   ├── __init__.py         # SkillRouter public API
│   ├── cli.py              # CLI (click-free, stdlib argparse)
│   ├── registry.py         # Skill registry + SKILL.md frontmatter parser
│   ├── search.py           # Search engine + CN_KEYWORD_MAP
│   └── skills/             # Bundled skill definitions
├── tests/                  # Test suite
│   ├── test_search.py
│   ├── test_registry.py
│   ├── test_cli.py
│   └── test_router.py
├── .github/workflows/      # CI/CD
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── CHANGELOG.md
```

## Pull Request Guidelines

- Write a clear description of the change and why it's needed.
- Link to any related issues.
- Add or update tests for the changed behavior.
- Run `ruff check skill_router/ tests/ && ruff format --check skill_router/ tests/` before committing.
- Run `pytest tests/ -v` and ensure all tests pass.
- Keep dependencies at zero for runtime code. If you genuinely need a third-party library, open an issue to discuss it first.

## Adding Chinese Keywords

Edit `skill_router/search.py` → `CN_KEYWORD_MAP`. Add your domain-specific terms following the existing pattern:

```python
"中文词": ["english", "keywords", "here"],
```

Each Chinese key maps to a list of English terms that appear in skill names or descriptions.

Please also add a test case in `tests/test_search.py` to document the new mapping.

## Reporting Bugs

Open an issue with:

- A minimal reproduction command or script.
- Your Python version and OS.
- The output of `skill-router --version`.

## Suggesting Features

Open an issue describing:

- The problem you're trying to solve.
- Your proposed solution.
- Whether it keeps the package zero-dependency.

Thanks!
