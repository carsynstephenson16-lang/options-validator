"""Owner-frozen external-provider acquisition policy.

ThetaData acquisition was operationally disabled on 2026-07-31. This policy
has no environment-variable override: immutable cached reads stay available,
while any path that could authenticate, fetch, write provider bytes, or append
an acquisition fact must fail before construction or mutation.
"""

from typing import Final

THETADATA_ACQUISITION_DISABLED: Final = True
THETADATA_DISABLED_EFFECTIVE: Final = "2026-07-31T21:26:46-04:00"


class ProviderDisabledError(RuntimeError):
    """An operator-disabled external-provider acquisition was attempted."""


def require_thetadata_acquisition(operation: str) -> None:
    """Refuse every ThetaData acquisition path without consulting the env."""
    if THETADATA_ACQUISITION_DISABLED:
        raise ProviderDisabledError(
            "ThetaData acquisition is disabled effective "
            f"{THETADATA_DISABLED_EFFECTIVE}; refused {operation}. "
            "Immutable cached reads remain enabled."
        )
