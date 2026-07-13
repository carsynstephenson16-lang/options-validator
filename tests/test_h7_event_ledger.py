"""Stage 3 H7 forward-event ledger -- BUILD-ONLY. Tested only through the
owner-agreed public seams: append_event / read_events / verify, the
idempotency contract, and the `verify` CLI. Real temp files; only system
boundaries (clock, os.replace, fsync, concurrency) are mocked. No real
forward event is ever written to the default store."""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from options_researcher import h7_event_ledger as el


def _ev(**over):
    """A minimal valid logical event dict; override single fields to probe."""
    base = {
        "schema_version": 1,
        "event_id": "e1",
        "event_type": "data_gate",
        "occurred_at_utc": "2026-07-10T20:00:00+00:00",
        "evaluation_session": "2026-07-10",
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": {"whole_universe_verdict": "NO_GO", "go_count": 0},
    }
    base.update(over)
    return base


class LedgerBase(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / "h7_forward"   # absent until first append
        self.events = self.base / "events.jsonl"
        self.head = self.base / "HEAD"

    def _clock(self, iso="2026-07-11T00:00:00+00:00"):
        return lambda: datetime.fromisoformat(iso)


class TestVerifyEmpty(LedgerBase):
    def test_absent_ledger_is_valid_empty_and_creates_nothing(self):
        res = el.verify(base_dir=self.base)
        self.assertTrue(res.valid)
        self.assertTrue(res.empty)
        self.assertEqual(res.count, 0)
        self.assertIsNone(res.head)
        self.assertFalse(self.base.exists())   # nothing created
        self.assertFalse(self.events.exists())
        self.assertFalse(self.head.exists())

    def test_cli_valid_empty_exit_0(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = el.main(["verify", "--base-dir", str(self.base)])
        self.assertEqual(rc, 0)
        self.assertIn("VALID EMPTY", buf.getvalue())
        self.assertFalse(self.base.exists())


class TestAppendAndChain(LedgerBase):
    def test_first_event_is_seq_0_zero_prev_hash(self):
        r = el.append_event(_ev(), base_dir=self.base, clock=self._clock())
        self.assertEqual(r.seq, 0)
        self.assertTrue(r.appended)
        events = el.read_events(self.base)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].prev_hash, "0" * 64)
        self.assertEqual(events[0].seq, 0)
        self.assertEqual(self.head.read_text().strip(), r.record_hash)

    def test_worked_fixture_matches_literal_known_hashes(self):
        # Hashes computed independently (hashlib, outside the implementation)
        # so this is not a tautological recompute.
        r = el.append_event(_ev(), base_dir=self.base, clock=self._clock())
        ev = el.read_events(self.base)[0]
        self.assertEqual(
            ev.logical_hash,
            "d2238b62f01e395a3cde50896405fcdb86a0ed3c2e828ca5dc2cc66e7880523e")
        self.assertEqual(
            ev.record_hash,
            "a8579ceeabfa8e468e030239db696494c16cb0a56de9980c1871ceda8b67b437")
        self.assertEqual(r.record_hash, ev.record_hash)

    def test_second_event_links_to_first(self):
        r0 = el.append_event(_ev(event_id="e1"), base_dir=self.base,
                             clock=self._clock())
        r1 = el.append_event(_ev(event_id="e2", causes=["e1"]),
                             base_dir=self.base, clock=self._clock())
        self.assertEqual(r1.seq, 1)
        events = el.read_events(self.base)
        self.assertEqual(events[1].prev_hash, r0.record_hash)
        self.assertEqual(events[1].causes, ["e1"])
        # HEAD now points at the tip
        self.assertEqual(self.head.read_text().strip(), r1.record_hash)

    def test_read_events_verifies_before_returning(self):
        el.append_event(_ev(), base_dir=self.base, clock=self._clock())
        # corrupt HEAD; read_events must refuse, not return partial records
        self.head.write_text("deadbeef\n")
        with self.assertRaises(el.LedgerCorruptionError):
            el.read_events(self.base)


class TestIdempotency(LedgerBase):
    def test_identical_duplicate_is_no_op(self):
        r0 = el.append_event(_ev(), base_dir=self.base, clock=self._clock())
        before = self.events.read_bytes()
        mtime = self.events.stat().st_mtime_ns
        r1 = el.append_event(_ev(), base_dir=self.base,
                             clock=self._clock("2026-08-01T00:00:00+00:00"))
        self.assertFalse(r1.appended)
        self.assertEqual(r1.seq, r0.seq)
        self.assertEqual(r1.record_hash, r0.record_hash)
        self.assertEqual(self.events.read_bytes(), before)   # no byte change
        self.assertEqual(self.events.stat().st_mtime_ns, mtime)  # no mtime change

    def test_conflicting_duplicate_refuses_without_mutation(self):
        el.append_event(_ev(), base_dir=self.base, clock=self._clock())
        before = self.events.read_bytes()
        head_before = self.head.read_bytes()
        with self.assertRaises(el.EventConflictError):
            el.append_event(_ev(payload={"go_count": 99}),
                            base_dir=self.base, clock=self._clock())
        self.assertEqual(self.events.read_bytes(), before)
        self.assertEqual(self.head.read_bytes(), head_before)


class TestCausalRules(LedgerBase):
    def test_backward_cause_passes(self):
        el.append_event(_ev(event_id="a1"), base_dir=self.base,
                        clock=self._clock())
        r = el.append_event(_ev(event_id="b2", causes=["a1"]),
                            base_dir=self.base, clock=self._clock())
        self.assertTrue(r.appended)

    def test_missing_cause_refuses(self):
        with self.assertRaises(el.EventValidationError):
            el.append_event(_ev(event_id="b2", causes=["nope"]),
                            base_dir=self.base, clock=self._clock())
        self.assertFalse(self.base.exists() and self.events.exists())

    def test_self_cause_refuses(self):
        with self.assertRaises(el.EventValidationError):
            el.append_event(_ev(event_id="a1", causes=["a1"]),
                            base_dir=self.base, clock=self._clock())

    def test_duplicate_cause_refuses(self):
        el.append_event(_ev(event_id="a1"), base_dir=self.base,
                        clock=self._clock())
        with self.assertRaises(el.EventValidationError):
            el.append_event(_ev(event_id="b2", causes=["a1", "a1"]),
                            base_dir=self.base, clock=self._clock())

    def test_forward_cause_refuses(self):
        # cause names an id that only appears later -> not earlier -> refuse
        el.append_event(_ev(event_id="a1"), base_dir=self.base,
                        clock=self._clock())
        with self.assertRaises(el.EventValidationError):
            el.append_event(_ev(event_id="b2", causes=["c3"]),
                            base_dir=self.base, clock=self._clock())


class TestFieldValidation(LedgerBase):
    def _refuse(self, **over):
        with self.assertRaises(el.EventValidationError):
            el.append_event(_ev(**over), base_dir=self.base,
                            clock=self._clock())
        self.assertFalse(self.events.exists())

    def test_unknown_event_type_refuses(self):
        self._refuse(event_type="not_a_type")

    def test_lowercase_symbol_refuses(self):
        self._refuse(symbol="nvda")

    def test_invalid_lane_refuses(self):
        self._refuse(lane="z")

    def test_naive_timestamp_refuses(self):
        self._refuse(occurred_at_utc="2026-07-10T20:00:00")

    def test_bad_session_date_refuses(self):
        self._refuse(evaluation_session="2026-7-10")

    def test_non_object_payload_refuses(self):
        self._refuse(payload=[1, 2, 3])

    def test_unknown_top_level_field_refuses(self):
        bad = _ev()
        bad["extra"] = 1
        with self.assertRaises(el.EventValidationError):
            el.append_event(bad, base_dir=self.base, clock=self._clock())

    def test_nan_payload_refuses_before_write(self):
        self._refuse(payload={"x": float("nan")})
        self.assertFalse(self.events.exists())


class TestCorruptionDetection(LedgerBase):
    def _two_events(self):
        el.append_event(_ev(event_id="a1"), base_dir=self.base,
                        clock=self._clock())
        el.append_event(_ev(event_id="b2", causes=["a1"]),
                        base_dir=self.base, clock=self._clock())

    def _lines(self):
        return self.events.read_text().split("\n")[:-1]

    def _rewrite(self, lines, head=None):
        self.events.write_text("\n".join(lines) + "\n")
        if head is not None:
            self.head.write_text(head + "\n")

    def _assert_corrupt(self):
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)

    def test_payload_tamper_breaks_record_hash(self):
        self._two_events()
        lines = self._lines()
        lines[0] = lines[0].replace('"NO_GO"', '"GO"')
        self._rewrite(lines)
        self._assert_corrupt()

    def test_field_tamper_breaks_hash(self):
        self._two_events()
        lines = self._lines()
        lines[1] = lines[1].replace('"data_gate"', '"skip"')
        self._rewrite(lines)
        self._assert_corrupt()

    def test_broken_prev_hash_refuses(self):
        import json as _json
        self._two_events()
        lines = self._lines()
        obj = _json.loads(lines[1])
        obj["prev_hash"] = "0" * 64   # should equal seq-0 record_hash
        lines[1] = el.canonical_json(obj)
        self._rewrite(lines)
        self._assert_corrupt()

    def test_incorrect_seq_refuses(self):
        self._two_events()
        import json as _json
        lines = self._lines()
        obj = _json.loads(lines[1])
        obj["seq"] = 5
        lines[1] = el.canonical_json(obj)
        self._rewrite(lines)
        self._assert_corrupt()

    def test_deleted_record_refuses(self):
        self._two_events()
        lines = self._lines()
        self._rewrite([lines[0]])   # drop the tip but keep old HEAD
        self._assert_corrupt()

    def test_reordered_records_refuse(self):
        self._two_events()
        lines = self._lines()
        self._rewrite([lines[1], lines[0]])
        self._assert_corrupt()

    def test_stale_head_refuses(self):
        self._two_events()
        first = el.read_events(self.base)[0].record_hash
        self.head.write_text(first + "\n")   # points at seq 0, not the tip
        self._assert_corrupt()

    def test_partial_json_refuses(self):
        self._two_events()
        lines = self._lines()
        lines[1] = lines[1][:20]   # truncated JSON
        self._rewrite(lines)
        self._assert_corrupt()

    def test_trailing_garbage_refuses(self):
        self._two_events()
        self.events.write_text(self.events.read_text() + "garbage\n")
        self._assert_corrupt()

    def test_one_file_present_is_corrupt(self):
        self._two_events()
        self.head.unlink()
        self._assert_corrupt()

    def test_cli_corruption_exit_2_no_traceback(self):
        self._two_events()
        self.head.write_text("deadbeef\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = el.main(["verify", "--base-dir", str(self.base)])
        self.assertEqual(rc, 2)
        self.assertIn("INVALID", buf.getvalue())
        self.assertNotIn("Traceback", buf.getvalue())

    def test_cli_populated_valid_exit_0(self):
        self._two_events()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = el.main(["verify", "--base-dir", str(self.base)])
        self.assertEqual(rc, 0)
        self.assertIn("VALID records=2", buf.getvalue())


class TestHashPerfectForgery(LedgerBase):
    """The strongest attacks: rebuild a chain so every prev_hash/record_hash
    and HEAD are internally PERFECT, but a SEMANTIC rule is broken. verify
    must refuse on semantics, not merely on a hash mismatch. Hashes here are
    recomputed with a standalone hashlib+json (not the module's helpers)."""

    @staticmethod
    def _cj(obj):
        import json as _json
        return _json.dumps(obj, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False)

    @staticmethod
    def _h(text):
        import hashlib
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _forge(self, logicals):
        """logicals: list of full logical dicts (9 fields). Builds a
        hash-perfect chain and writes events.jsonl + HEAD."""
        lines, prev = [], "0" * 64
        for i, lg in enumerate(logicals):
            lh = self._h(self._cj(lg))
            rec = dict(lg)
            rec["seq"] = i
            rec["recorded_at_utc"] = "2026-07-11T00:00:00+00:00"
            rec["logical_hash"] = lh
            rec["prev_hash"] = prev
            rec["record_hash"] = self._h(self._cj(rec))
            lines.append(self._cj(rec))
            prev = rec["record_hash"]
        self.base.mkdir(parents=True, exist_ok=True)
        self.events.write_text("\n".join(lines) + "\n")
        self.head.write_text(prev + "\n")

    def test_perfect_duplicate_id_chain_refuses(self):
        self._forge([_ev(event_id="dup"), _ev(event_id="dup")])
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)

    def test_perfect_forward_cause_in_storage_refuses(self):
        # seq 0 causes "b2" which only appears at seq 1 -> lookahead baked in
        self._forge([_ev(event_id="a1", causes=["b2"]),
                     _ev(event_id="b2")])
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)

    def test_perfect_chain_not_starting_at_seq_0_refuses(self):
        # a single hash-perfect record whose seq is 1, not 0
        lg = _ev(event_id="a1")
        lh = self._h(self._cj(lg))
        rec = dict(lg)
        rec.update(seq=1, recorded_at_utc="2026-07-11T00:00:00+00:00",
                   logical_hash=lh, prev_hash="0" * 64)
        rec["record_hash"] = self._h(self._cj(rec))
        self.base.mkdir(parents=True, exist_ok=True)
        self.events.write_text(self._cj(rec) + "\n")
        self.head.write_text(rec["record_hash"] + "\n")
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)


class TestConcurrency(LedgerBase):
    def _spawn(self, events):
        import threading
        barrier = threading.Barrier(len(events))
        results, errors = {}, {}

        def worker(idx, ev):
            barrier.wait()   # maximize contention on the lock
            try:
                results[idx] = el.append_event(
                    ev, base_dir=self.base, clock=self._clock())
            except Exception as exc:   # noqa: BLE001 -- test records outcome
                errors[idx] = exc

        threads = [threading.Thread(target=worker, args=(i, ev))
                   for i, ev in enumerate(events)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results, errors

    def test_two_distinct_writers_make_one_valid_two_record_chain(self):
        results, errors = self._spawn(
            [_ev(event_id="w1"), _ev(event_id="w2")])
        self.assertEqual(errors, {})
        chain = el.read_events(self.base)   # verifies
        self.assertEqual(len(chain), 2)
        self.assertEqual([e.seq for e in chain], [0, 1])
        self.assertEqual({e.event_id for e in chain}, {"w1", "w2"})
        self.assertTrue(all(r.appended for r in results.values()))

    def test_two_identical_writers_make_one_record_one_idempotent(self):
        results, errors = self._spawn([_ev(event_id="same"),
                                       _ev(event_id="same")])
        self.assertEqual(errors, {})
        chain = el.read_events(self.base)
        self.assertEqual(len(chain), 1)
        appended = [r.appended for r in results.values()]
        self.assertEqual(sorted(appended), [False, True])   # one wrote, one no-op
        self.assertEqual({r.record_hash for r in results.values()},
                         {chain[0].record_hash})


class TestCrashInjection(LedgerBase):
    def test_os_replace_failure_leaves_detected_stale_head(self):
        from unittest import mock
        el.append_event(_ev(event_id="a1"), base_dir=self.base,
                        clock=self._clock())
        head_after_first = self.head.read_text()
        with mock.patch.object(el.os, "replace",
                               side_effect=OSError("replace boom")):
            with self.assertRaises(OSError):
                el.append_event(_ev(event_id="b2", causes=["a1"]),
                                base_dir=self.base, clock=self._clock())
        # events.jsonl got the 2nd record but HEAD is stale -> detected
        self.assertEqual(len(self.events.read_text().split("\n")[:-1]), 2)
        self.assertEqual(self.head.read_text(), head_after_first)
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)

    def test_fsync_failure_never_reports_success(self):
        from unittest import mock
        with mock.patch.object(el.os, "fsync",
                               side_effect=OSError("fsync boom")):
            with self.assertRaises(OSError):
                el.append_event(_ev(), base_dir=self.base,
                                clock=self._clock())
        # no success result was returned; the store is left detectably corrupt
        # (events.jsonl present, HEAD never written)
        self.assertTrue(self.events.exists())
        self.assertFalse(self.head.exists())
        with self.assertRaises(el.LedgerCorruptionError):
            el.verify(self.base)


if __name__ == "__main__":
    unittest.main()
