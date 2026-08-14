# Quorum — Multimodal Disclosure Intelligence

*A portfolio project spec for a mid-level SWE (2–6 YOE) pivoting into AI engineering.*
*Drafted 2026-08-11. Not part of the options-validator research scope — this doc is a
standalone career artifact parked in this repo for versioning.*

---

## 1. The one-line pitch

**Quorum answers questions about a public company's disclosures by cross-checking the
filing text, the page images (charts and tables), the earnings-call audio, and the XBRL
structured facts against each other — and refuses to emit a claim that only one source
supports.**

Every answer carries per-claim provenance: a cropped page image, an audio timestamp, and
a machine-checkable XBRL fact ID. Every claim carries a verdict:
`CORROBORATED` / `SINGLE_SOURCE` / `CONFLICTING` / `UNSUPPORTED → abstain`.

## 2. The real problem

An equity analyst, credit analyst, IR associate, or compliance reviewer needs to answer
questions like:

- "What did management guide FY26 capex to, and has that number moved since last quarter?"
- "The deck says gross margin expanded — does the 10-Q table agree, and did the CFO hedge
  that on the call?"
- "Where do the slides and the filing disagree?"

Today's tooling fails on the parts that matter:

| Failure mode | Why text-only RAG breaks |
|---|---|
| **Charts are invisible** | A margin-bridge waterfall in an investor deck is pixels. PDF text extraction returns axis labels, or nothing. |
| **Complex tables scramble** | Multi-level headers, footnoted restatements, and units-in-thousands collapse into unordered token soup. The model then confidently reports a number off by 1000×. |
| **Spoken guidance is unindexed** | The most decision-relevant sentence of the quarter is often said out loud in Q&A and never written down. |
| **Silent single-sourcing** | The system says "gross margin is 46.2%" and does not tell you that only one of four sources says so. In a disclosure context, *unflagged disagreement is the actual harm.* |

Quorum's thesis: **for high-stakes documents, the interesting output is not the answer, it
is the agreement structure across sources.** That reframing is what makes this a systems
project rather than a chatbot.

## 3. What it actually does (user-visible behavior)

1. Ingests a company's last N quarters: 10-K / 10-Q / 8-K (SEC EDGAR), investor decks and
   press-release PDFs, earnings-call audio, and XBRL company facts.
2. User asks a natural-language question.
3. A router classifies the query (numeric lookup / guidance change / qualitative-risk /
   comparison / unanswerable) and dispatches four retrieval lanes **in parallel**.
4. Each lane returns evidence spans. A claim extractor normalizes them into typed atomic
   claims: `{metric, value, unit, scale, period, entity, source_id, span}`.
5. A corroborator aligns claims across lanes (unit and fiscal-period normalization is the
   hard part) and assigns an agreement verdict per claim.
6. A verifier runs entailment (NLI) of each claim against its own cited span — catching the
   classic failure where the citation is real but doesn't say what the answer says.
7. Synthesis emits the answer with inline citations. **Conflicts are surfaced, never
   silently resolved.** Unsupported → abstain.
8. UI: clicking a claim highlights the exact cropped region on the page image and seeks the
   audio player to the timestamp where it was said.

That last interaction is the demo money-shot — it is visually obvious in 10 seconds that
this is not an API wrapper.

## 4. HuggingFace tasks used

Drawn directly from the task taxonomy in the screenshot. Each one is load-bearing, not
decorative.

| HF task | Role in Quorum | Concrete model |
|---|---|---|
| **Visual Document Retrieval** | *Primary retrieval.* Late-interaction (ColPali-style) multi-vector search over **rendered page images** — no OCR, no parsing pipeline. This is the architectural centerpiece. | `ColQwen2.5` / `ColPali-v1.3` |
| **Document Question Answering** | Reads the retrieved page image to extract the figure from the chart or table | `Qwen2.5-VL-7B-Instruct`, hosted Claude as the high-tier fallback |
| **Image-Text-to-Text** | Chart/table reasoning, deck-slide interpretation | same VLM |
| **Object Detection** | Layout detection → crops the *exact* figure/table region for the citation viewer | `DocLayout-YOLO`, `Table-Transformer` |
| **Automatic Speech Recognition** | Earnings-call audio → word-level timestamped transcript | `distil-whisper-large-v3` / `faster-whisper` |
| **Voice Activity Detection** | Turn segmentation feeding diarization (CEO vs CFO vs analyst attribution) | `pyannote/segmentation-3.0` |
| **Audio Classification** | Speaker-role assignment + prepared-remarks vs Q&A segment tagging | `pyannote` embeddings + light classifier |
| **Sentence Similarity / Feature Extraction** | Dense text lane embeddings | `BAAI/bge-m3` |
| **Text Ranking** | Cross-encoder reranking of the fused hybrid candidate set | `BAAI/bge-reranker-v2-m3` |
| **Zero-Shot Classification** | Query router (intent → lane selection) before any labeled data exists | `DeBERTa-v3-large-mnli` |
| **Text Classification** | Hedging/uncertainty detector on spoken guidance ("we *expect*… *roughly*… *if conditions*") — the signal that separates a firm number from a soft one; plus NLI entailment for the verifier | fine-tuned DeBERTa-v3 on your own labels |
| **Token Classification** | NER over money / period / metric / entity, to normalize claims into slots that can be matched to XBRL | `gliner` or fine-tuned span tagger |
| **Table Question Answering** | Structured lane over XBRL facts and statement tables | text-to-SQL over Postgres + `TAPAS`-style fallback |
| **Summarization** | Grounded quarter-over-quarter guidance diff | hosted LLM, constrained decoding |

Optional stretch (label it clearly as exploratory, don't let it eat the schedule):
**Time Series Forecasting** on the tabular XBRL history to flag "this quarter's stated
figure is a 4σ break from its own trend" as a data-quality alarm, *not* a prediction.

## 5. Architecture

```
                       ┌──────────────┐
   question ─────────► │   Router     │  zero-shot intent classifier
                       │ (LangGraph)  │  + budget allocator
                       └──────┬───────┘
              ┌───────────────┼───────────────┬────────────────┐
              ▼               ▼               ▼                ▼
      ┌──────────────┐ ┌─────────────┐ ┌────────────┐  ┌──────────────┐
      │ VISION lane  │ │  TEXT lane  │ │ AUDIO lane │  │ STRUCTURED   │
      │ ColPali →    │ │ BM25 + dense│ │ transcript │  │ XBRL facts   │
      │ MaxSim →     │ │ → RRF fuse  │ │ index →    │  │ in Postgres  │
      │ layout crop  │ │ → reranker  │ │ timestamped│  │ → SQL        │
      │ → VLM read   │ │             │ │ span       │  │              │
      └──────┬───────┘ └──────┬──────┘ └─────┬──────┘  └──────┬───────┘
             └────────────────┴──────────────┴────────────────┘
                                     ▼
                        ┌────────────────────────┐
                        │   Claim Extractor      │ typed slots, Pydantic-validated
                        └───────────┬────────────┘
                                    ▼
                        ┌────────────────────────┐
                        │   Corroborator         │ unit/scale/fiscal-period alignment
                        │   ("the quorum")       │ → CORROBORATED / SINGLE / CONFLICT
                        └───────────┬────────────┘
                                    ▼
                        ┌────────────────────────┐
                        │   Verifier (NLI)       │ does the cited span entail the claim?
                        └───────────┬────────────┘
                        ┌───────────┴────────────┐
              low conf / conflict                pass
                        │                         │
              ┌─────────▼─────────┐     ┌─────────▼─────────┐
              │ Escalate: re-plan │     │   Synthesizer     │
              │ w/ larger budget, │     │ answer + per-claim│
              │ then human flag   │     │ citations         │
              └───────────────────┘     └───────────────────┘
```

**Why this is a real multi-agent system and not a prompt chain:** the nodes have different
tools, different models, different cost tiers, and a *cyclic* escalation edge with a budget
cap. State is checkpointed so a run is replayable and resumable. A human-in-the-loop
interrupt fires on `CONFLICTING`. That is LangGraph's actual value proposition, and you can
articulate why you chose it over a linear chain.

## 6. The eval harness — this is the part that gets you hired

Most portfolio projects have no eval, or an LLM-judge score with no ground truth. Quorum
has an **automatically generated, non-LLM-judged numeric ground truth**, which is rare
enough that it becomes the thing you talk about in interviews.

### 6.1 Golden set generated from XBRL (zero hand-labeling)

SEC XBRL `companyfacts` gives you, for free and machine-readable: the fact, its value, its
unit, its fiscal period, and the accession number of the filing it came from. So you can
**programmatically synthesize hundreds of QA pairs with exact ground truth**:

> Q: "What was NVIDIA's total revenue for fiscal Q3 2026?"
> A: `35082000000 USD` — from `us-gaap:Revenues`, accession `0001045810-25-000xxx`

Scoring is exact-match on the normalized numeric tuple `(value, unit, scale, period)`. No
judge model, no rubric, no ambiguity. This single design decision converts a subjective
system into a measurable one.

### 6.2 Five eval suites

1. **Numeric exactness** — the XBRL golden set above. Metric: exact-match accuracy,
   sliced by *where the answer lives* (narrative text / statement table / chart-only).
   The chart-only slice is where you prove the visual lane earned its complexity.
2. **Retrieval quality** — nDCG@10, recall@k, MRR at page granularity. Relevance labels
   derive from the XBRL fact → filing page mapping, so they're free too. **Always run the
   text-only baseline alongside** so every number is a *lift*, not an absolute.
3. **Groundedness / faithfulness** — per-claim NLI entailment against its own cited span;
   citation precision and recall; **unsupported-claim rate** as the headline safety metric.
   LLM-judge only as a secondary, correlated-against-NLI signal.
4. **Adversarial + counterfactual** — the suite that shows judgment:
   - **Unit traps**: regenerate pages with "in thousands" → "in millions". Does the system
     follow the header or the memorized value?
   - **Period near-misses**: FY25 vs FY24 vs "trailing twelve months" phrased identically.
   - **Restatement traps**: a later filing restates an earlier figure — which does it cite?
   - **Injected contradictions**: patch a deck figure so it disagrees with XBRL. Metric:
     **conflict-detection recall**. This directly tests the product's core promise.
   - **Unanswerable set**: questions whose answer is genuinely not in the corpus. Metric:
     **abstention rate** (baseline RAG scores ~0% here; that contrast is the slide).
5. **Cost & latency SLOs** — p50/p95 end-to-end and per node, tokens per query, $/query,
   GPU-seconds per ingested page. Tracked as first-class regression metrics.

### 6.3 Evals as a merge gate

```yaml
# .github/workflows/eval.yml (sketch)
on: [pull_request]
jobs:
  eval-gate:
    steps:
      - run: quorum eval run --suite fast --frozen-corpus v3
      - run: quorum eval gate \
               --min numeric_exact_match=0.78 \
               --max unsupported_claim_rate=0.03 \
               --max p95_latency_s=9.0 \
               --baseline main
```

A PR that changes a prompt, a model, a chunker, or a reranker **cannot merge if the frozen
eval slice regresses.** Nightly runs the full suite. This is the LLMOps story that separates
you from candidates who "used LangChain."

## 7. LLMOps

| Concern | Implementation |
|---|---|
| **Tracing / observability** | Langfuse (self-hosted, free) or LangSmith; OpenTelemetry spans across every node; every trace links to its eval run |
| **Reproducibility** | Every answer stamped with `{prompt_hash, model_id, index_version, corpus_as_of, graph_commit}`. An answer you can't reproduce is an answer you can't debug. |
| **Prompt management** | Prompts are versioned files in-repo with tests, not strings in Python. Changes ship through the eval gate like code. |
| **Ingestion** | Prefect (or Dagster) DAG: fetch → dedupe by content hash → render pages → embed → index. Idempotent, incremental, resumable. Re-running never duplicates. |
| **Index lifecycle** | Versioned indices with an atomic alias flip; dual-write during migration; **shadow-eval the new embedding model on live traffic before promoting.** |
| **Caching** | Exact-match cache + semantic cache (Redis) keyed on `(normalized_query, corpus_as_of)`; ~30–50% of analyst queries are near-duplicates |
| **Cost control** | Model cascade — cheap model attempts first, escalate only on low verifier confidence; per-node token budgets; batched GPU inference via vLLM / TEI |
| **Safety & governance** | Structured outputs (Pydantic) with retry-on-schema-fail; explicit abstain policy; source ToS/licensing registry per corpus item; no paywalled or login-gated sources |
| **Deploy** | Docker Compose locally; GPU jobs on Modal or RunPod (serverless, cheap for batch ingest); FastAPI + SSE streaming; k6 load test for the SLO numbers you'll quote |

## 8. Tech stack (recommended, with the reasoning)

- **Orchestration: LangGraph.** You need cycles (escalation), checkpointing, and a
  human-in-the-loop interrupt. A DAG framework can't express the escalation edge, and a
  linear LangChain chain can't either. Use plain LangChain only for provider adapters.
- **Vector stores: two, deliberately.**
  - **Qdrant** for the ColPali lane — it supports native **multivector** collections with
    MaxSim scoring, which is exactly what late interaction needs. (Vespa is the other real
    option; it's more powerful and much heavier to operate solo.)
  - **Postgres + pgvector** for the text lane, all metadata, *and* the XBRL facts — so the
    structured lane is a plain SQL join, and filtered retrieval is a `WHERE` clause instead
    of a bolted-on metadata filter.
  - Being able to explain *why two stores* — and what you'd give up collapsing to one — is
    itself a senior-signal answer.
- **Inference**: vLLM (VLM), Text Embeddings Inference (embeddings + reranker), hosted
  Claude for synthesis and the high-tier page read.
- **Backend**: FastAPI, Pydantic v2, SSE streaming, Redis, MinIO/S3 for page images and audio.
- **Frontend**: Next.js + shadcn/ui. Page-image citation viewer with bounding-box overlay
  and an audio player that seeks to the cited timestamp.
- **Data sources (all free, all ToS-clean)**:
  - SEC EDGAR submissions + full-text + **XBRL `companyfacts`/`frames` APIs** — declare a
    User-Agent, respect 10 req/s. This is the backbone.
  - Investor decks / press releases from company IR pages (public, no login, honor robots).
  - Earnings-call audio: public IR webcast replays where terms permit, plus openly licensed
    transcript datasets on the Hub for the ones that don't.
  - **Keep a licensing register in-repo, one row per source.** Reviewers notice; it is a
    two-hour task that signals five years of judgment.
- **Skip**: LlamaIndex here. It's a fine ingestion toolkit, but your ingestion is a Prefect
  DAG with custom page rendering, and adding it buys abstraction you'd have to fight.

## 9. 12-week solo plan

**Deliberately baseline-first.** Building the eval harness *before* the fancy retrieval is
the strongest process signal in the whole project — it means every later claim is measured.

| Weeks | Deliverable | Ship gate |
|---|---|---|
| 1–2 | Ingestion DAG, 15–25 tickers × 8 quarters, page rendering, XBRL → Postgres, **golden-set generator** | golden set of 300+ auto-labeled numeric QAs exists |
| 3 | **Baseline text-only RAG** + full eval harness + tracing | baseline numbers published, warts included |
| 4–5 | Visual lane: ColPali index, layout crops, VLM page read | measured lift vs baseline on the chart/table slice |
| 6–7 | Audio lane: ASR, diarization, timestamped index, hedging classifier | timestamped citations resolve in the UI |
| 8–9 | LangGraph corroborator, conflict detection, abstention, escalation | conflict-detection recall on the injected-contradiction set |
| 10 | Adversarial suites (units, periods, restatements, unanswerables) | four adversarial suites green in CI |
| 11 | LLMOps hardening: CI eval gate, semantic cache, cascade, cost dashboard, k6 SLOs | PR gate blocks a deliberately-regressed prompt |
| 12 | UI polish, ablation report, architecture decision records, write-up, demo video | public repo + report |

**Cut-lines if you slip** (decide these now, not at week 10):
diarization → speaker labels from transcript metadata; Qdrant multivector → pooled ColPali
vectors in pgvector; Next.js UI → Streamlit + a recorded demo; 25 tickers → 8.
**Never cut**: the eval harness, the baseline comparison, the abstention behavior.

## 10. How this maps to real AI-engineering JDs

| Typical 2026 JD bullet | What you point at |
|---|---|
| "Design and ship RAG systems over enterprise documents" | Four-lane hybrid retrieval with reranking, incremental reindexing, and versioned indices |
| "Multimodal / document AI experience" | Visual document retrieval, DocVQA, layout detection, ASR + diarization — with measured per-modality lift |
| "Build agentic workflows / multi-agent orchestration" | LangGraph state machine with parallel lanes, cyclic escalation, budget caps, checkpointed replay, HITL interrupt |
| "Establish evaluation frameworks for LLM applications" | Five suites, auto-generated ground truth, adversarial and counterfactual sets, CI merge gate |
| "LLMOps: monitoring, versioning, CI/CD for models and prompts" | Langfuse tracing, prompt registry, shadow eval, canary index promotion, nightly regression runs |
| "Optimize inference cost and latency at scale" | Model cascade, semantic cache, batched GPU inference, published p95 and $/query with before/after |
| "Fine-tune or adapt open models" | Hedging classifier and NER span tagger fine-tuned on your own labeled data; documented model cards |
| "Partner with domain experts; handle ambiguous requirements" | The conflict-surfacing product decision — you chose to expose disagreement rather than resolve it, and can defend why |
| "Production Python, APIs, cloud, IaC" | FastAPI, Prefect, Docker, Postgres, Redis, S3, GitHub Actions — the SWE experience you already have, now visibly in an AI system |

**Why it beats the usual portfolio entries:** "chat with your PDF" has no eval and no
multimodality. "Autonomous web-research agent" has no ground truth, so nobody can tell if
it works. "Text-to-SQL" is solved and demos identically for everyone. Quorum has an
objective scoreboard, three modalities, and a defensible product opinion. It also gives you
a genuinely interesting interview answer to *"tell me about something that didn't work"* —
your ablation report will show at least one lane that underperformed its cost.

## 11. Resume-ready impact metrics

Use this shape. **Fill every bracket with a number you actually measured** — the ablation
table in your repo is the receipt, and an interviewer who asks "how did you measure that?"
should get a crisp answer, not a shrug.

> **Quorum — Multimodal Disclosure Intelligence** *(solo, 12 weeks)*
> - Built a four-lane multimodal RAG system (page-image late-interaction retrieval, hybrid
>   text, timestamped audio, structured XBRL) over **[N] filings / [M] pages / [H] hours of
>   earnings-call audio**, orchestrated as a LangGraph multi-agent state machine with
>   cyclic escalation and human-in-the-loop review.
> - Raised numeric-answer exact-match accuracy from **[a]% → [b]%** over a text-only RAG
>   baseline — **+[c] pts on chart- and table-sourced questions** — measured against a
>   **[300+]-question ground-truth set auto-generated from SEC XBRL facts** (no hand labeling,
>   no LLM judge).
> - Cut unsupported-claim rate **[d]% → [e]%** via per-claim NLI verification and a
>   cross-source corroboration gate; system now **abstains on [f]% of unanswerable
>   questions** (baseline: 0%) and detects **[g]% of injected source contradictions**.
> - Reduced cost per query **[h]% ($[i] → $[j])** and p95 latency **[k]s → [l]s** through a
>   model cascade, semantic caching, and batched GPU inference at **[m] QPS** sustained.
> - Shipped LLMOps: OpenTelemetry tracing, versioned prompts and indices with shadow-eval
>   canary promotion, and a **CI eval gate that blocks merges on regression** across five
>   suites (retrieval, faithfulness, numeric exactness, adversarial, cost/latency).

## 12. Portfolio packaging

Ship these five artifacts alongside the code — they are most of the perceived seniority:

1. **`EVAL.md`** — the ablation table. Every lane, every model swap, cost and lift for each.
   Include the things that didn't pay for themselves.
2. **Architecture Decision Records** (`docs/adr/`) — 6–10 short ones. Why LangGraph over a
   chain. Why two vector stores. Why ColPali over an OCR pipeline. Why you surface conflicts
   instead of resolving them.
3. **A system card** — capabilities, known failure modes, out-of-scope uses, data licensing
   register. Explicitly: *this is a research and retrieval tool, not investment advice.*
4. **A 3-minute demo video** — the citation viewer clicking through to a cropped chart and
   an audio seek. Lead with this; most reviewers won't clone the repo.
5. **One written post** — "What auto-generated ground truth from XBRL taught me about
   evaluating RAG." This is the piece that gets shared and pulls inbound.

## 13. Known risks, and how to defuse them

| Risk | Mitigation |
|---|---|
| **Multi-vector index size** — ColPali emits ~1k vectors per page; naive storage explodes | Binary quantization + pooling (published techniques cut footprint ~10–30× with modest recall loss). **Measure it and report the tradeoff — that measurement is itself a portfolio asset.** |
| **Audio licensing** | Use only public replays whose terms permit it, plus openly licensed Hub transcript datasets. Keep the licensing register. Never scrape behind a login or paywall. |
| **SEC rate limits** | Declared User-Agent, ≤10 req/s, aggressive local caching. Your ingestion DAG is already idempotent, so this costs you nothing. |
| **GPU cost** | Batch ingest on serverless GPU (Modal/RunPod) and cache embeddings permanently; query-time uses hosted APIs + small local models. A 25-ticker corpus is a low-hundreds-of-dollars project, not thousands. |
| **Hallucinated conflicts** (the corroborator cries wolf) | Unit/period normalization must be deterministic code, not a prompt. Track **false-conflict rate** as a named metric with its own eval slice. |
| **Scope creep** | The cut-lines in §9 are pre-committed. The forecasting stretch goal is explicitly optional and gets cut first. |

---

### The one-sentence version for a recruiter

*"I built a multimodal retrieval system over SEC filings, investor decks, and earnings-call
audio that cites the exact chart region and audio timestamp behind every number, refuses to
answer when its sources disagree, and is scored against a ground-truth set generated
automatically from XBRL — with the whole eval suite wired into CI as a merge gate."*
