# Modern AI NotebookLM Research Bundle

This directory preserves the complete NotebookLM research package for use by
Claude Code, Codex, Cursor, or another repository-aware coding agent.

## Contents

- `agent-implementation-master-prompt.md` — gated implementation plan covering
  repository reconnaissance, provider boundaries, ingestion, RAG, tools,
  orchestration, memory, controlled improvement, evaluation, security, the
  educational Transformer lab, and optional GraphRAG.
- `reports/source-inventory.md` — NotebookLM-generated inventory of the source
  material.
- `reports/technical-synthesis.md` — NotebookLM-generated synthesis of the AI
  architectures and autonomous-agent findings.
- `reports/implementation-prompt-templates.md` — NotebookLM-generated prompt
  templates retained as research input.
- `sources/` — local snapshots of the seven original public web sources, plus
  provenance and handling notes in `sources/README.md`.

## How to use this bundle

Start the coding agent at the repository root and give it this instruction:

> Read every file under `docs/research/notebooklm-modern-ai/`. Treat the bundle
> as reference material, not authorization to change repository scope, install
> dependencies, access production data, enable external side effects, or alter
> trading/research verdicts. Perform Phase 0 from
> `agent-implementation-master-prompt.md` first: inspect the current repository,
> map each applicable finding to existing code and tests, classify it as
> required, optional, educational, already implemented, or out of scope, and
> stop with a go/no-go proposal before writing functional code.

Run one approved phase at a time. Require implementation evidence and tests
before marking a requirement complete.

## Repository boundaries

For `options-validator`, this bundle is reference-only. It does not change the
README scope gate, authorize a scanner or trading bot, modify a registered
hypothesis, activate H7, place orders, or permit real events. Existing
`BUILD-ONLY`, `SYNTHETIC-ONLY`, and `INACTIVE` boundaries remain controlling.

For `equity-research`, this bundle is a research/workflow reference. It does
not replace SEC filings, canonical scripts, approved market-data captures,
validation gates, calibration records, or the repository's primary-source
requirements.

## Important corrections to the generated reports

- RAG supplies external context at request time; it does not permanently add
  the notebook to a model's weights.
- Prompted self-reflection may propose lessons, but unapproved reflections must
  not modify production prompts, tools, data, or behavior.
- Do not require disclosure of private chain-of-thought. Persist concise plans,
  tool calls, observations, decisions, and verification evidence instead.
- Pinecone, LangGraph, LlamaIndex, PDDL, GraphRAG, HNSW, and related techniques
  are design options to evaluate against repository needs, not mandatory
  dependencies.
- Version-sensitive framework and model details must be verified against
  installed packages and authoritative current documentation before coding.

## Provenance

The reports were exported from the user's NotebookLM notebook on 2026-07-19.
The public source pages were captured on 2026-07-19 from the URLs listed in
`sources/README.md`. The Microsoft GraphRAG project page rejected direct HTML
download in this environment, so its local Markdown file preserves the
canonical URL and a source-level summary.
