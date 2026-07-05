"""CLI entry point for cc-skill-router.

Commands:
    skill-router init     Bootstrap the skill-router skill into Claude Code.
    skill-router scan     Generate registry from skill directories.
    skill-router search   Search the registry for matching skills.
    skill-router list     List all skills in the registry.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .registry import generate_registry
from .search import search

# Default registry path — kept under user's home, not tied to any
# specific Claude Code setup. Users can override with -r/--registry.
DEFAULT_REGISTRY_DIR = Path.home() / ".skill-router"
DEFAULT_REGISTRY_PATH = DEFAULT_REGISTRY_DIR / "index.json"


def _load_registry(path: Path) -> dict:
    """Load and validate the registry JSON file.

    Gracefully handles missing file, corrupted JSON, and empty registry.
    """
    if not path.is_file():
        print(f"[ERROR] Registry not found: {path}", file=sys.stderr)
        print("  Run 'skill-router scan' first to generate it.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, encoding="utf-8") as f:
            registry = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Registry file is corrupted: {path}", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        print("  Run 'skill-router scan' to regenerate it.", file=sys.stderr)
        sys.exit(1)

    if not isinstance(registry, dict):
        print(f"[ERROR] Invalid registry format in: {path}", file=sys.stderr)
        print("  Run 'skill-router scan' to regenerate it.", file=sys.stderr)
        sys.exit(1)

    return registry


def cmd_init(args: argparse.Namespace) -> None:
    """Bootstrap: copy the skill-router SKILL.md into ~/.claude/skills/."""
    target_dir = Path(args.target or str(Path.home() / ".claude" / "skills" / "skill-router"))

    # Locate the bundled SKILL.md
    skill_md = Path(__file__).resolve().parent.parent / "skills" / "skill-router" / "SKILL.md"
    if not skill_md.is_file():
        print("[ERROR] Bundled SKILL.md not found. Reinstall the package.", file=sys.stderr)
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill_md, target_dir / "SKILL.md")

    print(f"✓ Skill installed: {target_dir / 'SKILL.md'}")
    print("  Next: run 'skill-router scan' to index your skills.")


def cmd_scan(args: argparse.Namespace) -> None:
    """Generate the registry from skill directories."""
    skill_dirs = [Path(d) for d in args.dirs] if args.dirs else None
    output = Path(args.output) if args.output else DEFAULT_REGISTRY_PATH

    registry = generate_registry(skill_dirs=skill_dirs, output_path=output)

    print(f"✓ Registry generated: {output}")
    print(f"  {len(registry)} skills indexed")

    if len(registry) == 0:
        print()
        print("  No skills found. This might mean:")
        print("    1. You haven't installed any Claude Code skills yet.")
        print("    2. Your skill directories are at a different path.")
        print("  Try: skill-router scan -d /path/to/your/skills")
        return

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
    registry_path = Path(args.registry) if args.registry else DEFAULT_REGISTRY_PATH

    if not registry_path.is_file():
        print(f"[ERROR] Registry not found: {registry_path}", file=sys.stderr)
        print("  Run 'skill-router scan' first to generate it.", file=sys.stderr)
        print("  If your skills are at a custom location:", file=sys.stderr)
        print("    skill-router scan -d /path/to/skills -o /path/to/index.json", file=sys.stderr)
        sys.exit(1)

    registry = _load_registry(registry_path)

    if len(registry) == 0:
        print("⚠ Registry is empty. Run 'skill-router scan' to index your skills.")
        return

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
        print("  Tips:")
        print("    - Try broader or different keywords")
        print("    - Use -f json to see raw output")
        print("    - skill-router list to browse all skills")
        return

    # Pretty table output
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
    registry_path = Path(args.registry) if args.registry else DEFAULT_REGISTRY_PATH
    registry = _load_registry(registry_path)

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
        bridge = " *" if e.get("is_bridge") else ""
        print(f"  {e['name']}  [{e.get('group', '?')}/{e.get('domain', '?')}]{bridge}")


def main() -> None:
    # Ensure UTF-8 output on Windows (GBK codec can't handle Unicode)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="skill-router",
        description=(
            "Semantic skill router for Claude Code — "
            "bilingual (Chinese/English) fuzzy search over your skill registry."
        ),
    )
    parser.add_argument("--version", action="version", version=f"skill-router {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── init ──────────────────────────────────────────────────────────────
    init_parser = subparsers.add_parser(
        "init", help="Install the skill-router skill into Claude Code"
    )
    init_parser.add_argument(
        "target",
        nargs="?",
        help="Target directory (default: ~/.claude/skills/skill-router)",
    )

    # ── scan ──────────────────────────────────────────────────────────────
    scan_parser = subparsers.add_parser("scan", help="Generate registry from skill directories")
    scan_parser.add_argument(
        "-d",
        "--dirs",
        nargs="+",
        help="Skill directories to scan (default: ~/.claude/skills ~/.codex/skills)",
    )
    scan_parser.add_argument(
        "-o",
        "--output",
        help=f"Output path for index.json (default: {DEFAULT_REGISTRY_PATH})",
    )
    scan_parser.add_argument("-v", "--verbose", action="store_true", help="Show group breakdown")

    # ── search ────────────────────────────────────────────────────────────
    search_parser = subparsers.add_parser("search", help="Search the registry for matching skills")
    search_parser.add_argument("query", help="Search query (Chinese or English)")
    search_parser.add_argument(
        "-n", "--top", type=int, default=5, help="Number of results (default: 5)"
    )
    search_parser.add_argument("--domain", help="Filter by domain (e.g., creativity, ethics)")
    search_parser.add_argument(
        "-g",
        "--group",
        help="Filter by group (thinking/coding/tools/content/persona/runbook/infra)",
    )
    search_parser.add_argument(
        "-t", "--type", dest="type", help="Filter by type (s4h/dbs/ponytail/tool/plugin)"
    )
    search_parser.add_argument("-r", "--registry", help="Path to registry JSON")
    search_parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    # ── list ──────────────────────────────────────────────────────────────
    list_parser = subparsers.add_parser("list", help="List all skills in the registry")
    list_parser.add_argument("--domain", help="Filter by domain")
    list_parser.add_argument("-g", "--group", help="Filter by group")
    list_parser.add_argument("-t", "--type", dest="type", help="Filter by type")
    list_parser.add_argument("-r", "--registry", help="Path to registry JSON")
    list_parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "scan":
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
