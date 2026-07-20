# Master Prompt: Implement the Modern AI Notebook Findings

Use this document with Claude Code, Codex, or another coding agent from the root of the target repository. Replace every value in `<angle brackets>` before starting.

## 0. What this project is actually building

The notebook describes an agent system with four connected capabilities:

1. A knowledge system that ingests private/current material, chunks it, embeds it, indexes it, and retrieves it with citations.
2. A model integration layer that gives the selected model grounded context and typed tools.
3. A stateful workflow that plans, retrieves, uses tools, asks for approval before risky actions, verifies results, and persists state.
4. A measured improvement loop that records failures and feedback without allowing the agent to silently change production behavior.

The Transformer section is an educational implementation track. It should be built separately unless the product specifically requires training or modifying a Transformer. A RAG system does not retrain the model or permanently add knowledge to its weights; it gives the model relevant external context at request time.

## 1. Operating contract for the coding agent

You are the implementation agent for `<PROJECT_NAME>` in `<REPOSITORY_PATH>`.

Before changing code:

- Inspect the repository, current branch, package manifests, entry points, tests, deployment files, environment configuration, and existing instructions.
- Treat existing behavior as the baseline. Do not replace working components merely because the notebook names a different framework.
- Identify which notebook findings already exist, which are partially implemented, and which are absent.
- Do not assume the model name, embedding model, vector database, framework versions, or deployment target. Read configuration and verify supported versions from the project’s authoritative documentation.
- Do not print, commit, upload, or request secrets. Use environment-variable names and safe local fakes in tests.
- Do not make network calls, production writes, destructive changes, or external side effects without explicit approval.
- Do not reveal private chain-of-thought. Provide a concise rationale, assumptions, decisions, and evidence instead.
- Use typed interfaces, small changes, tests-first where practical, and reversible migrations.

Create and maintain these files:

- `docs/ai-system/ARCHITECTURE.md`: current architecture and data-flow diagram.
- `docs/ai-system/REQUIREMENTS_TRACEABILITY.md`: every notebook finding mapped to a requirement, implementation, test, and status.
- `docs/ai-system/DECISIONS.md`: framework, model, storage, security, and cost decisions with alternatives considered.
- `docs/ai-system/THREAT_MODEL.md`: prompt injection, data leakage, unauthorized tools, poisoned documents, and tenant/ACL risks.
- `docs/ai-system/EVALUATION.md`: datasets, metrics, thresholds, and regression procedure.
- `docs/ai-system/IMPLEMENTATION_LEDGER.md`: phase, files changed, tests run, evidence, known gaps, and next step.

At the end of every phase, report:

1. What changed.
2. What did not change and why.
3. Tests and commands run, with results.
4. Requirements completed and still open.
5. Any assumption requiring human approval.
6. The exact next phase.

Do not proceed to the next phase if the phase gate fails.

## 2. Phase 0 — Reconnaissance and requirements extraction

Read the notebook export at `<NOTEBOOK_EXPORT_PATH>` and any source notes supplied with the project. Extract findings into a traceability matrix with these categories:

- Transformer foundation: encoder/decoder decomposition, Q/K/V scaled dot-product attention, multi-head attention, positional encoding, output logits/softmax, cross-entropy, and label smoothing.
- RAG: ingestion, parsing, semantic chunking, embeddings, vector storage, retrieval, augmentation, grounded generation, citations, updates, deletion/revocation, and access control.
- Agent architecture: planning/task decomposition, tool selection, typed tool calls, workflow state, memory, verification, human approval, and failure recovery.
- Improvement: feedback, self-critique, hindsight, evaluation, regression tests, and controlled promotion of lessons.
- Retrieval engineering: approximate-nearest-neighbor tradeoffs, metadata filtering, CRUD/freshness behavior, and whether the selected backend exposes HNSW, product quantization, MIPS, or another index strategy.
- Optional planning research: structured plans, Tree-of-Thoughts-style candidate comparison, LLM-to-classical-planner/PDDL translation, and external expert-module routing. Treat these as experiments unless the product has a deterministic planning domain that needs them.
- Optional advanced path: GraphRAG for relationship-heavy data.
- Development workflow: repository scaffolding, documentation access/MCP, implementation order, and agent handoffs.

For each item, record whether it is:

- required for the product;
- an educational lab;
- optional until evidence shows it is needed; or
- a notebook claim that must be verified before implementation.

Deliverable: a proposed architecture, dependency graph, risk list, open questions, and a phase plan. Ask only questions that cannot be answered by repository inspection and whose answer would materially change the design. Do not write functional code in this phase.

### Phase 0 gate

The human approves the architecture, product scope, model/provider, data classes, side-effect policy, and phase order. No API keys are required yet.

## 3. Phase 1 — Safe skeleton and provider boundaries

Implement the smallest runnable vertical skeleton:

- configuration loaded from environment variables or a typed settings object;
- a model-provider adapter with the exact model ID configurable;
- an embedding-provider adapter;
- interfaces for document ingestion, parsing, chunking, indexing, retrieval, memory, tools, and approvals;
- a CLI or API health check using fake providers by default;
- structured event logging with request ID, user/session ID, model ID, prompt version, latency, and outcome;
- no production credentials and no real side-effecting tools.

Keep provider-specific code behind adapters. The rest of the application must not import vendor SDK details directly.

### Phase 1 gate

The skeleton starts locally, fake providers work, configuration errors are clear, tests run without network access, and no secret is present in source control.

## 4. Phase 2 — Knowledge ingestion and durable memory

Implement an idempotent ingestion pipeline:

1. Discover allowed files, APIs, or database records.
2. Parse plain text and structured documents. Add a separate adapter for difficult PDFs/tables only if the data requires it.
3. Normalize text while preserving source identity, page/section, headings, tables, timestamps, and permissions.
4. Chunk by semantic boundaries with measured size and overlap. Make chunking configurable.
5. Generate embeddings through the adapter.
6. Store vectors and metadata in a replaceable vector-store adapter. Start with the simplest local testable backend; add a hosted backend only when deployment needs it. Treat MIPS/ANN, HNSW, product quantization, serverless partitioning, and freshness layers as backend implementation choices to benchmark—not algorithms to reimplement by default.
7. Make ingestion idempotent using source and content hashes.
8. Support updates, stale-record replacement, deletion, revocation, and permission-aware filtering.
9. Store provenance for every chunk: source ID, version, locator, hash, ingestion time, parser, embedding model, and access scope.

Distinguish three kinds of memory:

- conversation memory: current interaction context;
- durable knowledge: approved source documents and their indexed chunks;
- user/task memory: explicit preferences, decisions, and task state.

Never automatically promote every conversation or model reflection into durable knowledge. Add an explicit classification and approval path.

### Phase 2 gate

Fixtures can be ingested twice without duplicates; changed and deleted documents are handled; permissions are enforced; source locators survive indexing; and chunk/metadata tests pass.

## 5. Phase 3 — Retrieval-Augmented Generation

Implement the RAG path as a deterministic, testable pipeline:

`user query -> query classification -> retrieval -> optional reranking -> context budget -> grounded prompt -> model answer -> citation/verification -> response`

Requirements:

- retrieve by semantic similarity and, where useful, keyword/hybrid search;
- apply metadata and permission filters before context reaches the model;
- make top-k, score thresholds, reranking, and context limits configurable;
- record whether retrieval is exact or approximate, and benchmark recall/latency/freshness before tuning HNSW, PQ, or other ANN settings;
- preserve chunk IDs and source locators through the entire request;
- instruct the model to answer only from supplied evidence for grounded questions;
- require an explicit “insufficient evidence” response when evidence is missing;
- cite claims to source locators and make citation verification testable. Prefer claim-level provenance such as `[source_id:page_or_section]`; do not require long verbatim quotations when a short source locator is sufficient;
- log retrieved IDs, scores, filters, prompt version, and answer status without logging sensitive content unnecessarily;
- separate retrieval failures, generation failures, citation failures, and authorization failures.

Do not describe RAG as eliminating hallucinations. Measure retrieval quality, groundedness, citation correctness, abstention, latency, and cost on a fixed evaluation set.

### Phase 3 gate

Known-answer tests demonstrate that relevant evidence is retrieved, irrelevant/unauthorized evidence is excluded, answers cite the right sources, and the system abstains when evidence is insufficient.

## 6. Phase 4 — Tools and agent workflow

Implement the workflow using the project’s chosen state-machine/orchestration approach. Use LangGraph if it fits the repository and requirements; do not add it solely because the notebook names it.

Define explicit state, for example:

`received -> classify -> plan -> retrieve -> choose_tool -> execute_or_approve -> verify -> answer -> reflect -> persist`

Each state must have typed input/output and a failure route. Add:

- a tool registry with typed JSON schemas;
- allowlisted tools only;
- read-only, reversible, and side-effecting permission tiers;
- dry-run mode;
- timeout, retry, idempotency, and circuit-breaker behavior;
- tool-result validation;
- an approval interrupt before database writes, code execution, messages, purchases, deployments, or other consequential actions;
- audit events recording who/what approved an action and what actually happened;
- a bounded retry budget and a clear stop condition.
- strict machine-readable schemas at system boundaries; if a tool call cannot be validated, return a structured error and do not execute it;
- optional dependency-aware task lists for multi-tool requests, with explicit task IDs and validated references to earlier outputs;
- an optional PDDL/classical-planner adapter only when the project has a stable domain model and needs deterministic long-horizon planning;

The model may choose a tool, but it may not redefine tool permissions. Use structured tool calls rather than requiring the model to print a hidden “Thought” trace or a fragile ReAct text format.

### Phase 4 gate

The workflow passes state-transition tests, tool-schema tests, timeout/retry tests, approval pause/resume tests, unauthorized-action tests, and audit-log tests.

## 7. Phase 5 — Memory persistence and controlled improvement

Implement short-term and cross-session persistence with explicit retention rules:

- checkpoint state by conversation/session;
- load only the minimum authorized memory for a request;
- support deletion and retention expiry;
- prevent one user or tenant from retrieving another’s memory;
- provide an inspectable memory write log.
- score candidate memories by recency, importance, and relevance to the active task, but treat any fixed "seven items" limit as a tunable heuristic rather than a system invariant;

Implement a Reflexion-like improvement loop as an evaluation subsystem, not an autonomous self-modification mechanism:

1. Capture the task, plan summary, tool events, evidence, answer, feedback, and outcome.
2. Run a rubric-based evaluator for correctness, groundedness, citation quality, tool choice, efficiency, and policy compliance.
3. Produce a concise lesson candidate and link it to the failure evidence.
4. Test the proposed change against a regression set.
5. Require human or release-gate approval before changing prompts, routing, tools, retrieval settings, or durable knowledge.
6. Version and roll back every promoted change.

Add hindsight evaluation that compares prior output and feedback against the next attempt. Store metrics and lessons separately from source truth.

### Phase 5 gate

The system can resume sessions, honor deletion/retention, detect repeated failed actions, create lessons, and prove that unapproved reflections cannot change production behavior.

## 8. Phase 6 — Evaluation, security, and operations

Build an evaluation harness before calling the agent complete. Include:

- ingestion correctness and idempotency;
- retrieval precision/recall or hit rate;
- answer groundedness and citation correctness;
- abstention on unsupported questions;
- tool selection and argument validity;
- workflow completion and recovery;
- human-approval enforcement;
- cross-session memory isolation;
- prompt-injection and malicious-document fixtures;
- latency, token usage, cost, and failure rates.

Create a small golden set with expected sources, acceptable answer facts, forbidden claims, and expected tool/approval behavior. Record baseline metrics before optimization.

Threat-model at minimum:

- instructions hidden inside retrieved documents;
- untrusted tool output;
- sensitive data leaking into prompts, logs, or citations;
- poisoned or stale knowledge;
- authorization bypass through metadata filters;
- runaway loops and repeated side effects;
- model/provider outages;
- unsafe code execution.
- domain-specific high-risk actions, including chemical, biological, financial, medical, or infrastructure operations, must have stricter tool allowlists and human approval where applicable.

Add redaction, least-privilege credentials, source trust labels, content sanitization, rate limits, tracing, alerts, and rollback procedures as appropriate.

### Phase 6 gate

The evaluation suite is reproducible, security tests pass, operational dashboards/logs exist, failure behavior is documented, and a human can disable tools or revert the last release.

## 9. Phase 7 — Educational Transformer lab

Build this in an isolated `labs/transformer/` directory so it cannot silently affect the production agent. Use NumPy first for clarity and a tensor framework only if training is required.

Implement and test in this order:

1. Vector/matrix shape utilities and numerical-stability helpers.
2. Scaled dot-product attention: scores, scaling by `sqrt(d_k)`, masking, softmax, and weighted value sum.
3. Multi-head attention: separate Q/K/V projections, reshape into heads, attention per head, concatenate, and output projection.
4. Sinusoidal positional encoding for sequence length 100 and embedding size 512.
5. Residual connections, normalization, and feed-forward block.
6. Encoder block and decoder block, including causal and cross-attention masks.
7. Linear vocabulary projection, softmax/log-probabilities, cross-entropy, and label smoothing.
8. A tiny overfit-able toy task with shape, mask, gradient/numerical, and loss-decrease tests.

The agent must explain shapes and invariants in code comments and tests. This lab teaches the architecture; it does not make the production model retain the notebook.

Do not implement raw Chain-of-Thought, hidden reasoning replay, or a requirement to expose internal thoughts. If experimenting with Tree-of-Thoughts, ReAct, or Reflexion, expose only candidate plans, tool calls, observations, scores, and concise decision summaries.

### Phase 7 gate

Each component has tests, numerical edge cases are covered, the toy task learns, and the lab is isolated from production dependencies and runtime paths.

## 10. Phase 8 — Optional GraphRAG

Do not add GraphRAG by default. First prove that ordinary or hybrid RAG cannot answer the project’s relationship-heavy questions. If needed:

- define the entity/relation schema;
- extract candidate entities and relationships with provenance;
- validate and version graph writes;
- preserve source links for every edge;
- retrieve graph neighborhoods plus supporting text;
- compare GraphRAG against the baseline on a relationship-focused evaluation set;
- keep a rollback path to ordinary RAG.

## 11. Prompt sequence to run with the agent

Use one prompt per phase. Do not paste all phase prompts in one request if doing so would cause the agent to skip gates.

### Kickoff prompt

> Read `docs/ai-system/IMPLEMENTATION_LEDGER.md` and the repository instructions. Perform Phase 0 only. Inspect the repository and `<NOTEBOOK_EXPORT_PATH>`, build the traceability matrix, identify what already exists, and propose the smallest safe architecture. Do not write functional code. Do not assume vendor/model/framework choices. Stop with the phase-gate report and the exact decisions I must approve.

### Phase implementation prompt

> Implement Phase `<N>` from the master plan. First restate the phase gate and the requirements it covers. Inspect existing code before editing. Make the smallest coherent change, add or update tests, run the relevant checks, and update the architecture, traceability matrix, decisions, and implementation ledger. Do not start the next phase. Do not use real secrets or perform external side effects. If a requirement is ambiguous, stop and ask one focused question; otherwise make a reversible documented assumption.

### Review prompt

> Review the current implementation against `REQUIREMENTS_TRACEABILITY.md` and the notebook findings. Find omissions, false claims, security gaps, weak tests, stale documentation, and behavior that is only mocked. Do not change code yet. For each issue, give severity, evidence, affected requirement, exact correction, and a test that would prove the correction. End with go/no-go for the next phase.

### Verification prompt

> Verify the completed phases from the outside in. Run the full test suite, static checks, type checks, evaluation harness, security fixtures, and a local end-to-end flow with fake providers. Inspect generated artifacts and logs. Report exact commands and results. Mark a requirement complete only when implementation and evidence both exist.

### Release-readiness prompt

> Perform a release-readiness audit. Confirm model/provider configuration, secret handling, authorization, source citations, deletion and retention, tool approvals, retry/idempotency behavior, observability, cost limits, rollback, and regression metrics. Produce a go/no-go report. Do not deploy or activate side-effecting tools.

## 12. Recommended Cursor/Claude Code/Codex operating method

1. Put this file and the notebook export under version control in the target repository’s documentation area.
2. Add the operating contract to the repository’s `AGENTS.md`, `CLAUDE.md`, or equivalent instruction file.
3. Start the agent at the repository root, not from a random subdirectory.
4. Run the kickoff prompt and approve the architecture before code generation.
5. Run exactly one phase prompt at a time.
6. After each phase, run the review prompt in a fresh context or independent reviewer.
7. Run the verification prompt after every two or three phases and before any real credentials or deployment.
8. Keep fake providers and local fixtures as the default test path.
9. Only then configure a development vector store/model endpoint, with least-privilege credentials.
10. Enable production tools last, one permission tier at a time, behind approval and rollback controls.

The correct handoff is not “the agent knows everything.” It is a repository containing source notes, decisions, traceability, tests, evaluation data, versioned prompts, and a reproducible implementation history.
