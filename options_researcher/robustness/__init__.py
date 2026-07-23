"""Research-only validation robustness tools.

Nothing in this package is imported by the scanner, ranking, execution, or
portfolio paths.  Results are exploratory unless a signed registration and
owner promotion explicitly say otherwise.
"""

from options_researcher.robustness.models import ExperimentSpec

__all__ = ["ExperimentSpec"]
