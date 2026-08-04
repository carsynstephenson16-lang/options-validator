"""Shared point-in-time knowability helper for the options-flow study lane.

Every forward-looking outcome/target column produced in this package encodes
its own required look-ahead horizon (in trading sessions) as a trailing
integer in its column name -- e.g. ``return_5`` needs 5 future sessions,
``return_21`` needs 21, ``future_rv21`` needs 21, ``excess_return_5`` and
``iv_change_5`` need 5. `required_horizon_for` parses that convention so
purge windows (`options_researcher.flow.study`) and analog-candidate
emission (`options_researcher.flow.analogs`) can enforce that a column's
declared/assumed horizon can never fall short of what the column actually
needs -- the review findings this module fixes were both instances of a
caller-supplied or gate-supplied horizon silently under-covering the real
requirement encoded in the column's own name.
"""

from __future__ import annotations

import re

_TRAILING_HORIZON_RE = re.compile(r"(\d+)$")


def required_horizon_for(column: str) -> int:
    """Return the forward-looking horizon (in trading sessions) encoded in
    `column`'s name, e.g. ``required_horizon_for("return_21") == 21``.

    Raises ValueError for any column that does not encode a trailing
    horizon -- an unknown target/outcome column must fail loudly rather than
    silently default to a horizon that could be too small (the P2 leakage
    finding this closes).
    """
    match = _TRAILING_HORIZON_RE.search(column)
    if not match:
        raise ValueError(
            f"column {column!r} does not encode a forward-looking horizon "
            "(expected a trailing integer, e.g. 'return_21' or 'future_rv21')"
        )
    return int(match.group(1))
