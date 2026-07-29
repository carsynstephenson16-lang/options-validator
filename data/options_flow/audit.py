"""Executable, fail-closed quality audit for normalized options-flow data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, cast

import pandas as pd

AUDIT_SCHEMA = "options_flow_data_audit_v1"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    check: int
    severity: str
    message: str
    examples: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DataAuditResult:
    schema: str
    tickers: tuple[str, ...]
    date_range: tuple[str, str] | None
    row_count: int
    findings: tuple[AuditFinding, ...]
    verdict: str

    @property
    def ledger_note(self) -> str:
        return (
            f"{self.schema}: {self.verdict}; rows={self.row_count}; findings={len(self.findings)}"
        )


def _examples(frame: pd.DataFrame, mask: pd.Series, columns: Iterable[str]) -> tuple[str, ...]:
    selected = [column for column in columns if column in frame.columns]
    if not selected or not bool(mask.any()):
        return ()
    return tuple(
        frame.loc[mask, selected].head(3).astype(str).to_dict(orient="records").__str__(),
    )


def _session_series(frame: pd.DataFrame) -> pd.Series:
    if "session" in frame:
        return pd.to_datetime(frame["session"], errors="coerce").dt.strftime("%Y-%m-%d")
    return (
        pd.to_datetime(frame["trade_timestamp"], errors="coerce", utc=True)
        .dt.tz_convert("America/New_York")
        .dt.strftime("%Y-%m-%d")
    )


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, frame[name])


def _numeric(frame: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, pd.to_numeric(_series(frame, name), errors="coerce"))


def audit_options_data(
    trades: pd.DataFrame,
    *,
    expected_sessions: Iterable[str] | None = None,
    underlying_reference: pd.DataFrame | None = None,
    tradeable_mask: pd.Series | None = None,
    stale_seconds: float = 60.0,
) -> DataAuditResult:
    """Run the mandatory completeness, sanity, and structural audit.

    Findings touching ``tradeable_mask`` are blocking. The default is
    deliberately conservative: every row is treated as potentially tradeable.
    """
    required = {
        "symbol",
        "expiration",
        "strike",
        "right",
        "trade_timestamp",
        "quote_timestamp",
        "size",
        "trade_price",
        "bid",
        "ask",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        finding = AuditFinding(0, "BLOCK", f"missing required columns: {missing}")
        return DataAuditResult(
            AUDIT_SCHEMA,
            (),
            None,
            len(trades),
            (finding,),
            "BLOCK",
        )

    frame = trades.copy()
    frame["session"] = _session_series(frame)
    row_is_tradeable = (
        pd.Series(True, index=frame.index)
        if tradeable_mask is None
        else tradeable_mask.reindex(frame.index, fill_value=False).astype(bool)
    )
    findings: list[AuditFinding] = []

    def add(check: int, mask: pd.Series, message: str, columns: Iterable[str]) -> None:
        if not bool(mask.any()):
            return
        severity = "BLOCK" if bool((mask & row_is_tradeable).any()) else "WARN"
        findings.append(AuditFinding(check, severity, message, _examples(frame, mask, columns)))

    if expected_sessions is not None:
        observed = set(frame["session"].dropna().astype(str))
        missing_dates = sorted(set(expected_sessions) - observed)
        if missing_dates:
            findings.append(
                AuditFinding(
                    1,
                    "BLOCK",
                    f"missing trading sessions: {missing_dates[:10]}",
                    tuple(missing_dates[:3]),
                )
            )

    expirations_per_session = cast(
        pd.Series,
        frame.groupby("session", dropna=False)["expiration"].nunique(),
    )
    sparse_expiration_sessions = {
        str(session)
        for session, count in expirations_per_session.to_dict().items()
        if int(count) < 1
    }
    if sparse_expiration_sessions:
        findings.append(
            AuditFinding(
                2,
                "BLOCK",
                "session has no usable expiration",
                tuple(map(str, sparse_expiration_sessions)),
            )
        )

    if "underlying_price" in frame:
        distance = (_numeric(frame, "strike") / _numeric(frame, "underlying_price") - 1).abs()
        near_atm = distance <= 0.05
        atm_counts = cast(
            pd.Series,
            frame.loc[near_atm].groupby(["session", "expiration"])["strike"].nunique(),
        )
        thin = [str(key) for key, count in atm_counts.to_dict().items() if int(count) < 2]
        if thin:
            findings.append(
                AuditFinding(
                    3,
                    "WARN",
                    "fewer than two strikes within 5% of spot",
                    tuple(thin[:3]),
                )
            )

    missing_quote = cast(pd.Series, frame[["bid", "ask"]].isna().any(axis=1))
    add(4, missing_quote, "missing bid or ask", ("symbol", "session", "expiration", "strike"))

    numeric = {name: _numeric(frame, name) for name in ("bid", "ask", "size", "trade_price")}
    negative = (
        numeric["bid"].lt(0)
        | numeric["ask"].lt(0)
        | numeric["size"].lt(0)
        | numeric["trade_price"].lt(0)
    )
    if "prior_open_interest" in frame:
        negative |= _numeric(frame, "prior_open_interest").lt(0)
    add(5, negative, "negative quote, size, or trade price", required)
    add(6, numeric["bid"].gt(numeric["ask"]), "crossed market", required)

    mid = (numeric["bid"] + numeric["ask"]) / 2.0
    near_money = (
        (_numeric(frame, "moneyness_log").abs() <= 0.02)
        if "moneyness_log" in frame
        else pd.Series(False, index=frame.index)
    )
    add(
        7,
        numeric["bid"].eq(0) & numeric["ask"].gt(0) & near_money,
        "zero bid with positive ask near the money",
        required,
    )
    relative_spread = (numeric["ask"] - numeric["bid"]).div(mid.where(mid > 0))
    add(
        8,
        relative_spread.gt(0.20),
        "bid/ask spread exceeds 20% of midpoint",
        required,
    )
    add(
        15,
        numeric["bid"].le(0) & numeric["ask"].le(0),
        "bid and ask are both non-positive (dead market)",
        required,
    )

    trade_time = cast(
        pd.Series,
        pd.to_datetime(_series(frame, "trade_timestamp"), errors="coerce", utc=True),
    )
    quote_time = cast(
        pd.Series,
        pd.to_datetime(_series(frame, "quote_timestamp"), errors="coerce", utc=True),
    )
    age = (trade_time - quote_time).dt.total_seconds()
    add(
        9,
        age.lt(0) | age.gt(stale_seconds),
        f"quote is future-dated or older than {stale_seconds:g} seconds",
        ("symbol", "trade_timestamp", "quote_timestamp"),
    )

    if "iv" in frame:
        iv = _numeric(frame, "iv")
        add(10, iv.isna() | iv.le(0) | iv.gt(5), "IV missing or outside (0, 500%]", required)
    greek_masks: list[pd.Series] = []
    if "delta" in frame:
        greek_masks.append(_numeric(frame, "delta").abs().gt(1))
    if "gamma" in frame:
        greek_masks.append(_numeric(frame, "gamma").lt(0))
    if greek_masks:
        impossible_greek = greek_masks[0]
        for mask in greek_masks[1:]:
            impossible_greek |= mask
        add(11, impossible_greek, "Greek outside long-option bounds", required)

    duplicate_keys = (
        ["stable_trade_id"]
        if "stable_trade_id" in frame
        else [
            "symbol",
            "expiration",
            "strike",
            "right",
            "trade_timestamp",
            "trade_price",
            "size",
        ]
    )
    duplicate = frame.duplicated(duplicate_keys, keep=False)
    add(12, duplicate, "duplicate trade identity rows", duplicate_keys)

    if underlying_reference is not None:
        reference_required = {"symbol", "session", "close"}
        reference_missing = sorted(reference_required - set(underlying_reference.columns))
        if reference_missing:
            findings.append(
                AuditFinding(13, "BLOCK", f"underlying reference missing: {reference_missing}")
            )
        elif "underlying_price" in frame:
            reference = underlying_reference.loc[:, list(reference_required)].copy()
            merged = frame.merge(
                reference.rename(columns={"close": "independent_close"}),
                on=["symbol", "session"],
                how="left",
                validate="many_to_one",
            )
            mismatch = (
                _numeric(merged, "underlying_price")
                .div(_numeric(merged, "independent_close"))
                .sub(1)
                .abs()
                .gt(0.005)
            )
            add(
                13,
                pd.Series(mismatch.to_numpy(), index=frame.index),
                "underlying price differs from independent close by more than 0.5%",
                ("symbol", "session"),
            )

    expiration_dates = cast(
        pd.Series,
        pd.to_datetime(_series(frame, "expiration"), errors="coerce"),
    )
    session_dates = cast(
        pd.Series,
        pd.to_datetime(_series(frame, "session"), errors="coerce"),
    )
    weekend = (
        expiration_dates.dt.weekday.gt(4)
        | expiration_dates.isna()
        | expiration_dates.lt(session_dates)
    )
    add(
        14,
        weekend,
        "expiration is malformed, expired, or falls on a weekend",
        ("symbol", "session", "expiration", "strike", "right"),
    )

    verdict = (
        "BLOCK"
        if any(finding.severity == "BLOCK" for finding in findings)
        else ("PASS WITH WARNINGS" if findings else "PASS")
    )
    sessions = sorted(frame["session"].dropna().astype(str).unique())
    tickers = tuple(sorted(frame["symbol"].astype(str).unique()))
    return DataAuditResult(
        AUDIT_SCHEMA,
        tickers,
        (sessions[0], sessions[-1]) if sessions else None,
        len(frame),
        tuple(findings),
        verdict,
    )


def render_audit(result: DataAuditResult) -> str:
    """Render the required audit output for logs and receipts."""
    lines = [
        f"Data audited: tickers={','.join(result.tickers)} "
        f"date_range={result.date_range} rows={result.row_count}",
        "Failed checks:",
    ]
    failed = [finding for finding in result.findings if finding.severity == "BLOCK"]
    lines.extend(
        f"{finding.check}. {finding.message}; examples={list(finding.examples)}"
        for finding in failed
    )
    lines.append("Warnings:")
    warnings = [finding for finding in result.findings if finding.severity == "WARN"]
    lines.extend(
        f"{finding.check}. {finding.message}; examples={list(finding.examples)}"
        for finding in warnings
    )
    lines.extend((f"Verdict: {result.verdict}", f"Ledger note: {result.ledger_note}"))
    return "\n".join(lines)
