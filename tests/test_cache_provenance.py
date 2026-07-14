import tempfile
import unittest
from pathlib import Path

from data.cache_provenance import load_blind_cache_facts


class BlindCacheFactTests(unittest.TestCase):
    def test_latest_canonical_fact_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.log"
            first = "a" * 64
            latest = "b" * 64
            path.write_text(
                "2026-07-10T20:01:00+00:00\tBLIND_CACHE symbol=NVDA "
                f"date=2026-07-10 rows=1 sha256={first}\n"
                "2026-07-10T20:02:00+00:00\tBLIND_CACHE symbol=NVDA "
                f"date=2026-07-10 rows=1 sha256={latest}\n"
            )
            facts = load_blind_cache_facts(path)
            fact = facts[("NVDA", "2026-07-10")]
            self.assertEqual(fact["sha256"], latest)
            self.assertEqual(
                fact["fetched"].isoformat(), "2026-07-10T20:02:00+00:00"
            )

    def test_claimed_but_malformed_fact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "facts.log"
            path.write_text(
                "2026-07-10T20:01:00+00:00\tBLIND_CACHE symbol=NVDA "
                "date=2026-07-10 rows=1 sha256=not-a-sha\n"
            )
            with self.assertRaisesRegex(ValueError, "malformed BLIND_CACHE"):
                load_blind_cache_facts(path)


if __name__ == "__main__":
    unittest.main()
