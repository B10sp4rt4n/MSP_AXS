"""Synthetic integration checks using real SQLite files and process restarts."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from labs.contingency.journal import Denied, Journal, SCOPES, SimulatedReceiver, database
from labs.contingency.server import make_server


class ContingencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.now = 10000.0
        self.local = Journal(self.root / "local.sqlite", clock=lambda: self.now)
        self.remote = SimulatedReceiver(self.root / "receiver.sqlite")
        self.a, self.b = SCOPES.values()
        for s in (self.a, self.b):
            self.local.prepare_fixture(s)
            self.remote.prepare_fixture(s, self.local.state(s)["snapshot"]["visit"])

    def entry(self, scope=None, request_id="request-1"):
        s = scope or self.a
        snap = self.local.state(s)["snapshot"]
        return self.local.record(s, request_id=request_id, visit=snap["visit"],
                                 action="entry", credential=snap["credential"])

    def exit(self, request_id="request-2"):
        snap = self.local.state(self.a)["snapshot"]
        return self.local.record(self.a, request_id=request_id, visit=snap["visit"], action="exit")

    def test_restart_preserves_entry_and_expiry_then_exit_and_sync(self):
        self.entry()
        original = self.local.state(self.a)["snapshot"]
        self.now += 5
        self.local = Journal(self.root / "local.sqlite", clock=lambda: self.now)
        self.local.prepare_fixture(self.a)
        self.assertEqual(self.local.state(self.a)["snapshot"], original)
        self.exit()
        self.assertEqual(self.local.sync(self.a, self.remote), 2)
        self.assertEqual(self.remote.state(self.a), {"state": "salida_registrada", "received": 2})

    def test_ack_loss_retry_keeps_one_event_after_receiver_restart(self):
        first = self.entry()
        with self.assertRaises(ConnectionError):
            self.local.sync(self.a, self.remote, lose_ack=True)
        self.assertEqual(self.local.state(self.a)["events"][0]["status"], "pending")
        self.remote = SimulatedReceiver(self.root / "receiver.sqlite")
        self.assertEqual(self.local.sync(self.a, self.remote), 1)
        self.assertEqual(self.entry()["event_uid"], first["event_uid"])
        self.assertEqual(self.local.sync(self.a, self.remote), 0)
        self.assertEqual(self.remote.state(self.a)["received"], 1)

    def test_retry_with_different_intent_is_rejected(self):
        self.entry()
        with self.assertRaises(Denied):
            self.exit(request_id="request-1")

    def test_reuse_pass_cannot_create_second_entry(self):
        self.entry()
        with self.assertRaises(Denied):
            self.entry(request_id="request-new")
        self.assertEqual(len(self.local.state(self.a)["events"]), 1)

    def test_wrong_pass_and_cross_tenant_visit_leave_no_changes(self):
        a, b = self.local.state(self.a)["snapshot"], self.local.state(self.b)["snapshot"]
        for visit, credential in [(a["visit"], "wrong"), (b["visit"], b["credential"])]:
            with self.assertRaises(Denied):
                self.local.record(self.a, request_id="bad", visit=visit, action="entry", credential=credential)
        self.assertEqual(self.local.state(self.a)["events"], [])
        self.assertEqual(self.local.state(self.b)["state"], "pendiente")

    def test_unknown_device_actor_gate_or_msp_denied(self):
        for field in ("node", "actor", "gate", "msp"):
            s = replace(self.a, **{field: "ajeno"})
            with self.subTest(field=field), self.assertRaises(Denied):
                self.local.state(s)

    def test_scopes_keep_independent_states_and_receipts(self):
        self.entry(self.a)
        self.entry(self.b)
        self.local.sync(self.a, self.remote)
        self.assertEqual(self.local.state(self.b)["events"][0]["status"], "pending")
        self.assertEqual(self.remote.state(self.b)["received"], 0)

    def test_expired_copy_blocks_entry_without_refresh_on_restart(self):
        self.now += 3600
        self.local = Journal(self.root / "local.sqlite", clock=lambda: self.now)
        self.local.prepare_fixture(self.a)
        with self.assertRaises(Denied):
            self.entry()

    def test_expired_copy_still_preserves_exit_observation(self):
        self.entry()
        self.now += 3600
        e = self.exit()
        self.assertTrue(e["snapshot_expired"])
        self.assertEqual(self.local.state(self.a)["state"], "salida_registrada")

    def test_clock_rollback_blocks_entry_and_flags_exit_for_review(self):
        self.entry()
        self.now -= 1
        with self.assertRaises(Denied):
            self.entry(self.b)
        self.assertTrue(self.exit()["clock_suspect"])
        self.local.sync(self.a, self.remote)
        self.assertEqual(self.local.state(self.a)["events"][-1]["status"], "conflict")

    def test_cancelled_remote_visit_preserves_entry_exit_as_conflicts(self):
        self.remote.cancel_fixture(self.a)
        self.entry()
        self.exit()
        self.local.sync(self.a, self.remote)
        self.assertEqual(self.remote.state(self.a), {"state": "cancelada", "received": 2})
        self.assertEqual([e["status"] for e in self.local.state(self.a)["events"]], ["conflict", "conflict"])

    def test_remote_rejects_cross_scope_and_uid_payload_collision(self):
        event = self.entry()
        with self.assertRaises(Denied):
            self.remote.receive(self.b, event)
        self.remote.receive(self.a, event)
        with self.assertRaises(Denied):
            self.remote.receive(self.a, {**event, "observed_at": 99})

    def test_remote_rejects_sequence_gaps(self):
        self.entry()
        event = self.exit()
        with self.assertRaises(Denied):
            self.remote.receive(self.a, event)
        self.assertEqual(self.remote.state(self.a)["received"], 0)

    def test_write_failure_rolls_back_projection_and_journal_together(self):
        with database(self.local.path) as db:
            db.execute("""CREATE TRIGGER fail_write BEFORE UPDATE ON visits
                BEGIN SELECT RAISE(ABORT, 'simulated full disk'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.entry()
        self.assertEqual(self.local.state(self.a)["state"], "pendiente")
        self.assertEqual(self.local.state(self.a)["events"], [])

    def test_journal_prohibits_update_delete(self):
        self.entry()
        for sql in ("UPDATE journal SET checksum='bad'", "DELETE FROM journal"):
            with self.assertRaises(sqlite3.IntegrityError), database(self.local.path) as db:
                db.execute(sql)

    def test_concurrent_same_request_produces_one_event(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.entry(), range(2)))
        self.assertEqual(results[0]["event_uid"], results[1]["event_uid"])
        self.assertEqual(len(self.local.state(self.a)["events"]), 1)

    def test_concurrent_different_requests_consume_pass_once(self):
        def attempt(n):
            try:
                return self.entry(request_id="request-" + str(n))
            except Denied:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)


class LocalHttpTests(unittest.TestCase):
    def test_html_api_sqlite_roundtrip_and_origin_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            server = make_server(directory, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}"
                with urllib.request.urlopen(url) as r:
                    html = r.read().decode()
                    self.assertIn("Laboratorio", html)
                    token = html.split("const token='")[1].split("'")[0]
                headers = {"X-Lab-Token": token, "Content-Type": "application/json", "Origin": url}
                def call(path, body=None, custom=None):
                    req = urllib.request.Request(url + path, headers=custom or headers,
                                                 data=json.dumps(body).encode() if body else None)
                    with urllib.request.urlopen(req) as response:
                        return json.load(response)
                snap = call("/api/state?condo=A")["snapshot"]
                body = {"condo": "A", "request_id": "browser-request", "visit": snap["visit"],
                        "action": "entry", "credential": snap["credential"]}
                first = call("/api/operation", body)
                self.assertEqual(call("/api/operation", body), first)
                call("/api/sync", {"condo": "A"})
                state = call("/api/state?condo=A")
                self.assertEqual(state["receiver"]["received"], 1)
                self.assertEqual(state["events"][0]["status"], "accepted")
                for bad in ({}, {**headers, "Origin": "https://ajeno.invalid"},
                            {**headers, "Host": "ajeno.invalid"}):
                    with self.assertRaises(urllib.error.HTTPError) as err:
                        call("/api/state?condo=A", custom=bad or {"X-Lab-Token": "wrong"})
                    self.assertEqual(err.exception.code, 403)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
