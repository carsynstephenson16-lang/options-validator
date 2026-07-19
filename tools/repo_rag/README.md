# Repository RAG

Isolated, read-only RAG application for this repository. The initial milestone
contains the policy boundary, offline providers, CLI status contract, and
tests. It does not modify the parent repository, call the network, or require
credentials.

## Commands

```bash
uv run python -m repo_rag status
uv run python -m unittest discover -s tests
```

`status` prints machine-readable JSON describing the repository policy and
offline provider configuration.

## Boundary

This application is advisory. Retrieved material remains subject to the parent
repository's canonical-source, validation, and safety rules. No write or action
tools are present.
