---
name: advisor-tool
description: Configure, implement, or audit Anthropic's beta Advisor Tool in API clients and agent loops. Use when the user asks to add or use an advisor model, pair a faster executor with a stronger advisor, force or nudge advisor calls, add beta headers/tool definitions, debug advisor_tool_result or pause_turn behavior, control advisor cost/caching, or make sure long coding/research agents consult the advisor at the right checkpoints. Do not use for ordinary coding unless the task specifically involves Advisor Tool integration or an advisor tool is actually available in the current runtime.
---

# Advisor Tool

## Overview

Use this skill to wire Anthropic's beta server-side `advisor` tool into code or prompts. A skill cannot call the advisor by itself; the client request must include the beta header and tool definition, or the current agent runtime must expose an actual `advisor` tool.

**Transcript sensitivity (before forwarding history):** consulting the advisor forwards the executor's context to a server-side model — the system prompt, tool definitions, prior turns, and prior tool results. Before wiring it in, require redaction of secrets and PII across all four of those surfaces and explicit data-handling approval for that forwarding. Do not forward raw executor transcripts by default.

## Implementation Checklist

1. Verify the provider is the first-party Claude API or Claude Platform on AWS — the only platforms where the advisor tool is available (beta). It is **not** available on Amazon Bedrock, Google Vertex AI, or Microsoft Foundry; on those, explain the boundary and stop (there is no advisor fallback there). Anthropic Messages / Beta Messages API compatibility alone is not sufficient — check the actual provider. Only after this check passes, continue.
2. Add beta `advisor-tool-2026-03-01`.
3. Add a tool definition. Replace `model` with the advisor you select in step 4, and set `max_uses` to cap consults per request:

```json
{"type": "advisor_20260301", "name": "advisor", "model": "claude-opus-4-8", "max_tokens": 2048, "max_uses": 3}
```

4. Select a supported executor/advisor pair — don't hardcode the example's `model`. Validate the full compatibility contract before committing IDs: (1) the pair is officially supported by Anthropic for Advisor Tool on your deployment platform (Claude API or Claude Platform on AWS only); (2) the advisor meets Anthropic's minimum supported model level for the advisor tool; (3) the advisor is at least as capable as the executor (the request's top-level `model`). Check current official documentation or installed SDK constants — capability ordering or a model ID existing in isolation is not sufficient. An invalid pair returns `400 invalid_request_error`.
5. Preserve full assistant content, including `advisor_tool_result`, across turns. If removing the advisor tool later, also strip prior `advisor_tool_result` blocks or the API can return `400 invalid_request_error`.
6. Handle `pause_turn`: resend the unchanged assistant message with the same advisor tool and the `advisor-tool-2026-03-01` beta header so the server can complete the pending advisor call. When client-side tool calls are also pending, submit their `tool_result` blocks first, then issue the advisor resume request with the tool and header retained. Dropping the tool or the header while an `advisor_tool_result` is in history returns a 400.
7. Track `usage.iterations[]`; advisor tokens are billed separately from executor tokens.

## Call Timing

For coding and agent loops, steer the executor to call advisor after read-only orientation but before writes, architecture commitments, or state-changing actions. Also call before declaring a substantial task complete, after the durable artifact exists and tests/logs are in context.

For short factual lookups, arithmetic, or commands where the next step is obvious, do not force a consult.

If the executor under-calls, use a second-turn nudge only when the executor is Haiku, it already has sufficient context, and an unresolved non-obvious design decision or failure mode remains. Do not nudge Opus; omit the nudge for Sonnet unless measured task-specific benefit warrants it:

```text
You have not consulted the advisor yet. If the task has a non-obvious design decision or a failure mode you have not ruled out, call advisor now before committing to an approach.
```

Use `tool_choice: {"type": "tool", "name": "advisor"}` only for a specific forced consult, and do not combine forced tool use with extended thinking.

## Cost Controls

- Start with `max_tokens: 2048` on the advisor tool.
- Use `max_uses` for per-request caps.
- Count advisor calls client-side for conversation-level budgets.
- Enable `caching: {"type": "ephemeral", "ttl": "5m"}` only when expecting at least three advisor calls in a conversation; keep it consistent across turns.

## Validation

Test one request where the executor calls advisor, one multi-turn continuation preserving the result blocks, one mixed-continuation path where a turn ends with a client `tool_use` while an advisor call is pending (submit the client `tool_result` first, then resume with the retained advisor tool and beta header), and one path where the advisor is removed after stripping prior advisor blocks. For agent loops, inspect transcripts to confirm the first consult happens after orientation and before substantive work.
