# Ops Failure Classification Design

**Goal:** Turn Schwab refresh-token expiry into an actionable, named,
fail-closed operational failure in both unattended capture lanes, and harden
the experiment dashboard subprocess test against stale HTML.

## Design

Recognize only Authlib `OAuthError` failures whose error code is
`invalid_grant` and whose description identifies a refresh token. A shared
predicate keeps that decision identical across the intraday and independent
preclose capture modules. Each CLI boundary prints one safe, single-line
`auth EXPIRED` diagnostic with `uv run python tools/setup_schwab.py`, returns
nonzero, performs no retry, and leaves credential storage unchanged. Other
OAuth errors continue to raise rather than being mislabeled.

The intraday and preclose wrappers capture the Python command's combined
output and classify the named line before their generic nonzero fallback.
Both emit a CRITICAL/BROKEN line containing `SCHWAB REAUTH REQUIRED` and the
same remediation command. Classification remains evidence-based from printed
lines rather than exit codes.

Offline tests construct the real Authlib exception and mock the external
capture boundary. Shell tests execute the wrappers' real classification
blocks with fixture output. The dashboard subprocess test asserts `wrote ` in
stdout for both invocations, with a temporary print-label mutation used to
prove the new assertion can fail.

## Constraints

- No network calls, retries, credential reads/writes, or new dependencies.
- Preserve all existing nonzero exits and generic fallbacks.
- Do not modify `ledger/`, `~/options-validator-ops`, or
  `~/options-validator-research`.
- Capture every RED failure verbatim in the dated receipt.
