#!/usr/bin/env python3
"""Create a local markdown research note from a tracked Obsidian template."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / ".obsidian" / "templates"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "research-notes"
TEMPLATES = {
    "hypothesis": "research-hypothesis.md",
    "experiment": "experiment-log.md",
    "data-audit": "data-source-audit.md",
    "oos-check": "oos-reveal-checklist.md",
}


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError("title must contain at least one letter or number")
    return slug


def render_template(template_text: str, *, title: str, today: date) -> str:
    return (
        template_text
        .replace("{{title}}", title)
        .replace("{{date}}", today.isoformat())
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="new_research_note")
    parser.add_argument("title", help="note title")
    parser.add_argument(
        "--template",
        choices=sorted(TEMPLATES),
        default="hypothesis",
        help="template to use",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="directory for the generated note",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        slug = slugify(args.title)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    template_path = TEMPLATE_DIR / TEMPLATES[args.template]
    output_dir = Path(args.output_dir)
    output_path = output_dir / f"{date.today().isoformat()}-{slug}.md"

    if output_path.exists():
        print(f"refusing to overwrite existing note: {output_path}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    text = render_template(template_path.read_text(), title=args.title, today=date.today())
    output_path.write_text(text)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
