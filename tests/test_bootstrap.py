import unittest

from metrics import scoreboard


def _trade(pnl, date="2021-01-04", symbol="SPY", car=100.0):
    return {"pnl": pnl, "capital_at_risk": car, "entry_date": date, "symbol": symbol}


class ContractTests(unittest.TestCase):
    def test_scoreboard_raises_without_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "symbol": "SPY"}])

    def test_scoreboard_raises_without_symbol(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 5.0, "capital_at_risk": 100.0, "entry_date": "2021-01-04"}])

    def test_scoreboard_raises_on_unparseable_entry_date(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date="not-a-date")])

    def test_scoreboard_raises_on_non_date_entry_type(self):
        with self.assertRaises(ValueError):
            scoreboard([_trade(5.0, date=123)])


if __name__ == "__main__":
    unittest.main()
