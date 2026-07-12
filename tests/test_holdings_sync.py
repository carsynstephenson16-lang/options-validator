"""7b-2R.2 finding 6: data/positions/holdings.csv is the source of truth
for share counts; README prose must never drift from it. The 38-vs-39 VST
discrepancy was reconciled to the later owner-verified 39 on 2026-07-11."""

import csv
import re
import unittest
from pathlib import Path


def book_shares() -> dict[str, int]:
    with Path("data/positions/holdings.csv").open() as f:
        return {row["symbol"].upper(): int(row["shares"])
                for row in csv.DictReader(f)}


class TestHoldingsBookIsSourceOfTruth(unittest.TestCase):
    def test_book_records_owner_verified_vst_position(self):
        self.assertEqual(book_shares().get("VST"), 39)

    def test_readme_share_claims_match_the_book(self):
        # every "<N> <SYM> shares" claim in README must equal the book --
        # prose is derived, the book is canonical
        readme = Path("README.md").read_text()
        claims = re.findall(r"(\d+)\s+([A-Z]{1,5})\s+shares", readme)
        self.assertTrue(claims, "README no longer states holdings; update "
                                "this test's regex or the README")
        book = book_shares()
        for count, sym in claims:
            self.assertEqual(
                int(count), book.get(sym),
                f"README claims {count} {sym} shares but the book "
                f"({'data/positions/holdings.csv'}) records "
                f"{book.get(sym)} -- fix the PROSE, never the book, unless "
                f"the owner verified a new count")
