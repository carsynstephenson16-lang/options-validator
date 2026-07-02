# Options Researcher Foundation

This foundation creates a local scaffold around the options validation harness.
It improves capture and review discipline without expanding the project into a
live scanner, paid data integration, or broker execution system.

## Structure

- `options_researcher/` contains a tiny importable manifest for required paths
  and forbidden capabilities.
- `scripts/validate_foundation.py` checks that the scaffold still exists.
- `scripts/new_research_note.py` creates markdown notes from tracked Obsidian
  templates.
- `.obsidian/templates/` contains local note templates that can be used from an
  Obsidian vault opened at the repository root.
- `docs/notebooklm/templates/` contains NotebookLM source and prompt templates.
- `docs/research-notes/` is the default location for generated notes.

## Boundaries

- No paid APIs are added by this foundation.
- No live trading is added.
- No broker order placement is added.
- No secrets belong in templates, scripts, docs, or source code.
- OOS data remains behind the existing pre-registration and reveal gates.

## Validation

Run:

```bash
uv run python scripts/validate_foundation.py
uv run python -m unittest discover -s tests
```
