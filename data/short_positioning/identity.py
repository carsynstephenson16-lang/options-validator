"""Effective-dated security identity.

A ticker is not an identity. Symbol reuse, share-class overlap, and corporate
actions resolve to a status that blocks derived history rather than joining
two different securities into one series.

The alias mapping is local and gitignored; an absent mapping is normal and
yields SYMBOL_ONLY, never an invented identifier.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from data.short_positioning.models import (
    IDENTITY_STATUSES,
    IdentityStatus,
    SecurityIdentityV1,
    ShortPositioningSchemaError,
)

ALIAS_SCHEMA = "security-alias/v1"
ALIAS_RELATIVE_PATH = Path("identity") / "aliases.json"


@dataclass(frozen=True, slots=True)
class SecurityAliasV1:
    schema_version: Literal["security-alias/v1"]
    symbol: str
    market: str | None
    security_id: str | None
    security_id_scheme: str | None
    issue_name: str | None
    effective_from: date
    effective_to: date | None
    identity_status: IdentityStatus
    note: str | None

    def __post_init__(self) -> None:
        if self.schema_version != ALIAS_SCHEMA:
            raise ShortPositioningSchemaError(f"alias schema_version must be {ALIAS_SCHEMA}")
        if self.identity_status not in IDENTITY_STATUSES:
            raise ShortPositioningSchemaError(f"unknown identity status {self.identity_status}")
        if self.effective_to is not None and self.effective_from > self.effective_to:
            raise ShortPositioningSchemaError("alias effective_from must not follow effective_to")

    def covers(self, asof: date) -> bool:
        if asof < self.effective_from:
            return False
        return self.effective_to is None or asof <= self.effective_to


def load_effective_dated_aliases(root: Path) -> tuple[SecurityAliasV1, ...]:
    """Read the local alias mapping. A missing mapping is empty, not an error."""
    path = Path(root) / ALIAS_RELATIVE_PATH
    if not path.exists():
        return ()

    try:
        rows = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ShortPositioningSchemaError(f"alias mapping is not decodable JSON: {exc}") from exc
    if not isinstance(rows, list):
        raise ShortPositioningSchemaError("alias mapping must be a JSON array")

    aliases = []
    for row in rows:
        if not isinstance(row, dict):
            raise ShortPositioningSchemaError("each alias must be a JSON object")
        aliases.append(
            SecurityAliasV1(
                schema_version=row.get("schema_version", ALIAS_SCHEMA),
                symbol=row["symbol"],
                market=row.get("market"),
                security_id=row.get("security_id"),
                security_id_scheme=row.get("security_id_scheme"),
                issue_name=row.get("issue_name"),
                effective_from=date.fromisoformat(row["effective_from"]),
                effective_to=(
                    None
                    if row.get("effective_to") is None
                    else date.fromisoformat(row["effective_to"])
                ),
                identity_status=row.get("identity_status", "VERIFIED"),
                note=row.get("note"),
            )
        )
    return tuple(aliases)


def resolve_security_identity(
    symbol: str,
    *,
    asof: date,
    aliases: tuple[SecurityAliasV1, ...] = (),
    market: str | None = None,
    issue_name: str | None = None,
) -> SecurityIdentityV1:
    """Resolve one symbol to an identity as it stood on ``asof``.

    No alias means SYMBOL_ONLY. Two overlapping aliases mean AMBIGUOUS and no
    identifier: a wrong join is worse than a missing one.
    """
    candidates = [
        alias
        for alias in aliases
        if alias.symbol == symbol
        and alias.covers(asof)
        and (market is None or alias.market is None or alias.market == market)
    ]

    if not candidates:
        return SecurityIdentityV1(
            schema_version="security-identity/v1",
            security_id=None,
            security_id_scheme=None,
            symbol=symbol,
            market=market,
            issue_name=issue_name,
            effective_from=None,
            effective_to=None,
            identity_status="SYMBOL_ONLY",
        )

    if len(candidates) > 1:
        return SecurityIdentityV1(
            schema_version="security-identity/v1",
            security_id=None,
            security_id_scheme=None,
            symbol=symbol,
            market=market,
            issue_name=issue_name,
            effective_from=None,
            effective_to=None,
            identity_status="AMBIGUOUS",
        )

    alias = candidates[0]
    return SecurityIdentityV1(
        schema_version="security-identity/v1",
        security_id=None
        if alias.identity_status in ("AMBIGUOUS", "SYMBOL_ONLY")
        else alias.security_id,
        security_id_scheme=alias.security_id_scheme,
        symbol=symbol,
        market=alias.market or market,
        issue_name=alias.issue_name or issue_name,
        effective_from=alias.effective_from,
        effective_to=alias.effective_to,
        identity_status=alias.identity_status,
    )
