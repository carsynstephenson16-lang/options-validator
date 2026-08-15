"""Package init.

Snapshots the Schwab capture invocation marker at the earliest possible
import, before any submodule can trigger a dotenv load (config.py,
data.schwab_adapter, LumiBot all mutate os.environ from .env files at
runtime). Only a marker present in the true process-start environment --
i.e. set by launchd via the pre-close plist -- is captured here, so a
marker smuggled into a .env file can never promote a hand-run capture to
unattended provenance (rev-2.1 item 3a; adversarial review 2026-08-15
finding F2). Consumed by options_researcher.schwab_chain_capture.
"""

import os

INVOCATION_MARKER_AT_IMPORT = os.environ.get("OPTIONS_VALIDATOR_INVOCATION_SOURCE")
