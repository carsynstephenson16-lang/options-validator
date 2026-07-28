# Independent Research Critic Rules

1. **Temporal Alignment:** Every research audit must enforce strictly comparable timestamps (`America/New_York` timezone). Never mix data across different as-of times or assume market state from weekend/after-hours aggregator quotes.
2. **Primary Source Verification:** Prioritize SEC filings, issuer IR statements, exchanges, and regulatory bodies over secondary financial news aggregators.
3. **Canonical Data Supremacy:** Deterministic repository market receipts take precedence over web text and LLM research inferences.
4. **Mandatory PJM Catalyst Tracking:** For VST and CEG, ensure the PJM Base Residual Auction catalyst remains tracked (`confirmed: false` with source link) until officially scheduled by PJM.
5. **Read-Only Operation:** Audits must operate strictly in read-only mode, producing report outputs without mutating repository state, market receipts, or trading verdicts.
