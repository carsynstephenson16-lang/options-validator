"""Direct coverage for research.facts append/dedupe semantics."""

import tempfile
import unittest
from pathlib import Path

from research.facts import append_fact, read_facts


class AppendFactDedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_identical_replay_under_dedupe_prefix_appends_once(self):
        fact = "SCHWAB_CHAIN_CAPTURE session=2026-08-13 manifest_hash=aa receipt_hash=bb"
        prefix = "SCHWAB_CHAIN_CAPTURE session=2026-08-13 "

        append_fact(fact, base_dir=self.base, dedupe_prefix=prefix)
        append_fact(fact, base_dir=self.base, dedupe_prefix=prefix)

        self.assertEqual(1, len(read_facts(self.base)))

    def test_divergent_payload_under_same_prefix_raises_instead_of_skipping(self):
        prefix = "SCHWAB_CHAIN_CAPTURE session=2026-08-13 "
        append_fact(
            prefix + "manifest_hash=aa receipt_hash=bb",
            base_dir=self.base,
            dedupe_prefix=prefix,
        )

        with self.assertRaisesRegex(RuntimeError, "payload differs"):
            append_fact(
                prefix + "manifest_hash=aa receipt_hash=DIFFERENT",
                base_dir=self.base,
                dedupe_prefix=prefix,
            )
        self.assertEqual(1, len(read_facts(self.base)))

    def test_prefix_must_be_nonempty_prefix_of_fact(self):
        with self.assertRaises(ValueError):
            append_fact("abc", base_dir=self.base, dedupe_prefix="")
        with self.assertRaises(ValueError):
            append_fact("abc", base_dir=self.base, dedupe_prefix="zzz")

    def test_bad_historical_byte_does_not_break_a_dedupe_append(self):
        log = self.base / "facts.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(b"2026-01-01T00:00:00+00:00\tOLD \xff NOTE\n")
        prefix = "SCHWAB_CHAIN_CAPTURE session=2026-08-13 "

        append_fact(
            prefix + "manifest_hash=aa receipt_hash=bb",
            base_dir=self.base,
            dedupe_prefix=prefix,
        )

        self.assertEqual(2, len(read_facts(self.base)))


if __name__ == "__main__":
    unittest.main()
