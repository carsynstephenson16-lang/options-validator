"""The diagnostic source-hash contract must bind a REPRODUCIBLE surface.

Two properties, both measured rather than asserted:

1. Every file the ACTIVE contract binds is visible to git (not gitignored), so
   the hash can be recomputed from a clean checkout by anyone, at any time.
   The v2 contract failed this: 98% of its inputs were two scratch `.venv`
   directories under `tools/`, which no clean checkout contains.
2. The live H7 forward window's registered `gates.source_hash` re-derives
   exactly from a clean checkout of its own `code_commit`. This is the
   property the registration's integrity anchor was supposed to have, and the
   2026-07-22 correction plan initially recorded it as permanently lost.

Both tests are offline and skip (never fail) when the git object or the git
checkout itself is unavailable, e.g. in a shallow CI clone.
"""

import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    DIAGNOSTIC_SOURCE_PATHS_V3,
    REPO_ROOT,
    diagnostic_source_hash,
    source_snapshot,
)

REGISTRATION = REPO_ROOT / "ledger" / "h7_forward" / "events.jsonl"


def _git(*args, **kwargs):
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True, text=True, check=False, **kwargs,
    )


def _is_git_checkout() -> bool:
    return _git("rev-parse", "--git-dir").returncode == 0


class TestActiveContractBindsOnlyTrackedSource(unittest.TestCase):
    def test_no_bound_file_is_gitignored(self):
        """A gitignored input cannot be reproduced from a clean checkout."""
        if not _is_git_checkout():
            self.skipTest("not a git checkout")
        snapshot = source_snapshot(
            paths=DIAGNOSTIC_SOURCE_PATHS_V3, exclude_dot_dirs=True
        )
        self.assertGreater(len(snapshot), 0)
        # check-ignore echoes back only the paths that ARE ignored.
        result = _git("check-ignore", "--stdin", input="\n".join(sorted(snapshot)))
        ignored = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(
            ignored, [],
            "the active diagnostic source-hash contract binds gitignored files, "
            "which makes every receipt unreproducible from a clean checkout: "
            f"{ignored[:10]}",
        )

    def test_active_version_is_the_dot_excluding_contract(self):
        """v3 semantics are what property 1 above is measured against."""
        self.assertEqual(DIAGNOSTIC_SOURCE_HASH_VERSION, 3)


class TestRegisteredWindowSourceHashRederives(unittest.TestCase):
    """The 2026-07-20 registration's integrity anchor is not inert."""

    def _registration(self) -> dict:
        if not REGISTRATION.exists():
            self.skipTest("no H7 forward event ledger in this checkout")
        for line in REGISTRATION.read_text().splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event_type") == "window_registration":
                return event["payload"]
        self.skipTest("no window_registration event recorded")

    def test_gates_source_hash_matches_clean_checkout_of_code_commit(self):
        payload = self._registration()
        commit = payload["code_commit"]
        registered = payload["gates"]["source_hash"]
        if not _is_git_checkout():
            self.skipTest("not a git checkout")
        if _git("cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            self.skipTest(f"commit {commit[:8]} not present (shallow clone?)")

        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "src.tar"
            written = _git("archive", "--format=tar", "-o", str(archive), commit)
            self.assertEqual(written.returncode, 0, written.stderr)
            clean = Path(tmp) / "clean"
            clean.mkdir()
            with tarfile.open(archive) as tar:
                tar.extractall(clean, filter="data")

            # v2 and v3 agree on a clean checkout: they differ only on
            # dot-prefixed paths, which a clean checkout does not contain.
            for version in (2, 3):
                self.assertEqual(
                    diagnostic_source_hash(root=clean, version=version),
                    registered,
                    f"registered gates.source_hash does not re-derive at v{version} "
                    f"from a clean checkout of {commit[:8]}",
                )


if __name__ == "__main__":
    unittest.main()
