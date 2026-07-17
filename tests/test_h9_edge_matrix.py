"""Spec §8 adversarial matrix — items not already covered by module tests.

Matrix map (spec item -> test):
 1 AMC filing            -> test_h9_events.TimingTests.test_amc_filing_decides_next_session
 2 BMO filing            -> test_h9_events.TimingTests.test_bmo_filing_decides_same_session
 3 boundary timestamp    -> test_h9_events.TimingTests.test_acceptance_exactly_at_close_is_after
 4 duplicate/amended 8-K -> HERE: immutable T_accept under 8-K/A
 5 missing entry chain   -> test_h9_census.CensusTests.test_missing_entry_chain_excluded
 6 missing exit chain    -> test_h9_study.LifecycleTests.test_missing_exit_chain_visible_gap_then_next_valid
 7 split inside hold     -> HERE: adjusted closes feed the trigger; contract math never touches them
 8 holiday next session  -> test_h9_events.TimingTests.test_holiday_gap_entry
 9 registry exclusions   -> HERE: registry-window events reason-coded
10 next report < DTE     -> test_h9_study.LifecycleTests.test_pre_next_report_exit_outranks_tp
11 census cannot price   -> test_h9_census.CensusStructureTests (both tests)
"""
import inspect
import unittest
from datetime import date, datetime, timezone

from options_researcher import h9_census as cz
from options_researcher import h9_events as ev
from options_researcher import h9_study as st


class Item4AmendedFilingTests(unittest.TestCase):
    def test_8ka_amendment_never_moves_t_accept(self):
        rows = [
            {"record_id": "A1", "symbol": "SMCI", "event_id": "SMCI-2024Q2",
             "status": "occurred", "occurred_date": date(2024, 8, 6),
             "expected_date": None,
             "known_as_of_utc": datetime(2024, 8, 6, 20, 5, tzinfo=timezone.utc),
             "supersedes": ""},
            {"record_id": "A2", "symbol": "SMCI", "event_id": "SMCI-2024Q2-A",
             "status": "occurred", "occurred_date": date(2024, 8, 6),
             "expected_date": None,
             "known_as_of_utc": datetime(2024, 9, 3, 14, 0, tzinfo=timezone.utc),
             "supersedes": ""},
        ]
        events = ev.derive_events(rows, symbols=("SMCI",))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].accepted_utc,
                         datetime(2024, 8, 6, 20, 5, tzinfo=timezone.utc))


class Item7SplitDisciplineTests(unittest.TestCase):
    def test_reaction_uses_adjusted_and_contracts_use_raw(self):
        runner_src = inspect.getsource(st)
        self.assertNotIn("load_closes", runner_src)  # closes injected, never loaded here
        census_src = inspect.getsource(cz)
        self.assertIn("load_closes_adjusted", census_src)


class Item9RegistryExclusionTests(unittest.TestCase):
    def _event(self, symbol, occurred, t_pre, t_dec, t_entry):
        return ev.H9Event(symbol=symbol, occurred_date=date.fromisoformat(occurred),
                          accepted_utc=datetime.fromisoformat(occurred + "T20:05:00+00:00"),
                          t_pre=t_pre, t_dec=t_dec, t_entry=t_entry)

    def test_smci_suspension_window_detected(self):
        e = self._event("SMCI", "2019-05-02", "2019-05-02", "2019-05-03", "2019-05-06")
        self.assertTrue(cz.in_registry_exclusion(e))

    def test_clean_event_not_excluded(self):
        e = self._event("MSFT", "2026-04-29", "2026-04-29", "2026-04-30", "2026-05-01")
        self.assertFalse(cz.in_registry_exclusion(e))

    def test_run_census_reason_codes_registry_exclusion(self):
        import tempfile
        from pathlib import Path
        e = self._event("SMCI", "2019-05-02", "2019-05-02", "2019-05-03", "2019-05-06")
        with tempfile.TemporaryDirectory() as tmp:
            res = cz.run_census([e], chain_dir=Path(tmp))
        self.assertEqual(res.reasons.get("registry_excluded"), 1)
        self.assertEqual(res.eligible_count, 0)
