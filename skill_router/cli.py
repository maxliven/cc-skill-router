"""CLI entry point for cc-skill-router.

Commands:
    skill-router scan     Generate registry from skill directories.
    skill-router search   Search the registry for matching skills.
    skill-router list     List all skills in the registry.
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .registry import generate_registry
from .search import search


def _default_registry_path() -> Path:
    """Default path for the registry index."""
    return Path.home() / ".ai-shared" / "skills" / ".registry" / "index.json"


def _load_registry(path: Path) -> dict:
    """Load registry from JSON file."""
    if not path.is_file():
        print(f"❌ Registry not found: {path}", file=sys.stderr)
        print("   Run 'skill-router scan' first to generate it.", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cmd_scan(args: argparse.Namespace) -> None:
    """Generate the registry from skill directories."""
    skill_dirs = [Path(d) for d in args.dirs] if args.dirs else None
    output = Path(args.output) if args.output else _default_registry_path()

    registry = generate_registry(skill_dirs=skill_dirs, output_path=output)

    print(f"✓ Registry generated: {output}")
    print(f"  {len(registry)} skills indexed")

    if args.verbose:
        groups: dict[str, int] = {}
        for entry in registry.values():
            g = entry.get("group", "unknown")
            groups[g] = groups.get(g, 0) + 1
        print("  Groups:")
        for g, count in sorted(groups.items()):
            print(f"    {g}: {count}")


def cmd_search(args: argparse.Namespace) -> None:
    """Search the registry for matching skills."""
    registry_path = Path(args.registry) if args.registry else _default_registry_path()
    registry = _load_registry(registry_path)

    results = search(
        query=args.query,
        registry=registry,
        top=args.top,
        domain=args.domain or "",
        group=args.group or "",
        skill_type=args.type or "",
    )

    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        print(f"⚠ No matching skills found for: {args.query}")
        return

    # Pretty table output (matches PowerShell style)
    print(f"┌─ Skill Search ({len(results)} matches) {'─' * 45}┐")
    for i, r in enumerate(results):
        desc = r.get("description", "")
        short_desc = desc[:52] + "..." if len(desc) > 55 else desc
        print("│")
        print(f"│ [{i + 1}] {r['name']} ({r.get('domain', '?')})")
        print(f"│    Score: {r['score']}/10    Type: {r.get('type', '?')}")
        print(f"│    {short_desc}")
    print("└" + "─" * 64 + "┘")


def cmd_list(args: argparse.Namespace) -> None:
    """List all skills in the registry."""
    registry_path = Path(args.registry) if args.registry else _default_registry_path()
    registry = _load_registry(registry_path)

    # Apply filters
    entries = list(registry.values())
    if args.domain:
        entries = [e for e in entries if e.get("domain") == args.domain]
    if args.group:
        entries = [e for e in entries if e.get("group") == args.group]
    if args.type:
        entries = [e for e in entries if e.get("type") == args.type]

    entries.sort(key=lambda e: e["name"])

    if args.format == "json":
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return

    print(f"Skills ({len(entries)}):")
    for e in entries:
        bridge = " 🌉" if e.get("is_bridge") else ""
        print(f"  {e['name']} [{e.get('group', '?')}/{e.get('domain', '?')}]{bridge}")


def main() -> None:
    # Ensure UTF-8 output on Windows (GBK codec can't handle Unicode symbols)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="skill-router",
        description="Semantic skill router for Claude Code — "
        "scan, search, and list your skill registry.",
    )
    parser.add_argument(
        "--version", action="version", version=f"skill-router {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── scan ──────────────────────────────────────────────────────────────
    scan_parser = subparsers.add_parser(
        "scan", help="Generate registry from skill directories"
    )
    scan_parser.add_argument(
        "-d", "--dirs", nargs="+",
        help="Skill directories to scan (default: ~/.claude/skills ~/.codex/skills)",
    )
    scan_parser.add_argument(
        "-o", "--output",
        help="Output path for index.json (default: ~/.ai-shared/skills/.registry/index.json)",
    )
    scan_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show group breakdown"
    )

    # ── search ────────────────────────────────────────────────────────────
    search_parser = subparsers.add_parser(
        "search", help="Search the registry for matching skills"
    )
    search_parser.add_argument("query", help="Search query (Chinese or English)")
    search_parser.add_argument(
        "-n", "--top", type=int, default=5, help="Number of results (default: 5)"
    )
    search_parser.add_argument(
        "-d", "--domain", help="Filter by domain (e.g., creativity, ethics)"
    )
    search_parser.add_argument(
        "-g", "--group",
        help="Filter by group (thinking/coding/tools/content/persona/runbook/infra)",
    )
    search_parser.add_argument(
        "-t", "--type", dest="type", help="Filter by type (s4h/dbs/ponytail/tool/plugin)"
    )
    search_parser.add_argument(
        "-r", "--registry", help="Path to registry JSON (default: auto-detect)"
    )
    search_parser.add_argument(
        "-f", "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )

    # ── list ──────────────────────────────────────────────────────────────
    list_parser = subparsers.add_parser(
        "list", help="List all skills in the registry"
    )
    list_parser.add_argument(
        "-d", "--domain", help="Filter by domain"
    )
    list_parser.add_argument(
        "-g", "--group", help="Filter by group"
    )
    list_parser.add_argument(
        "-t", "--type", dest="type", help="Filter by type"
    )
    list_parser.add_argument(
        "-r", "--registry", help="Path to registry JSON"
    )
    list_parser.add_argument(
        "-f", "--format", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
