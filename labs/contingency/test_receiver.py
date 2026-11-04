"""O2a: real loopback HTTP + signature checks + independent durable SQLite files."""
from copy import deepcopy
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.error

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from labs.contingency.journal import Denied, Journal, SCOPES, database
from labs.contingency.packages import LabAuthority, PackageTrust, VerifiedJournal, encode, proof_message
from labs.contingency.receiver import AuthenticatedReceiver, loopback_sender, make_receiver_server, signed_request, sync_authenticated


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root, self.now, self.scope = Path(self.tmp.name), 10000, SCOPES["A"]
        self.issuer, self.node, self.receipt_key = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.trust = PackageTrust({"issuer": self.issuer.public_key().public_bytes_raw()})
        self.authority = LabAuthority("issuer", self.issuer)
        self.authority.enroll(self.scope, self.node.public_key().public_bytes_raw())
        fixture = Journal(self.root / "fixture.sqlite", clock=lambda: self.now)
        fixture.prepare_fixture(self.scope)
        self.snap = fixture.state(self.scope)["snapshot"]
        self.package = self.issue()
        self.journal = VerifiedJournal(self.root / "node.sqlite", self.trust, clock=lambda: self.now)
        self.journal.install(self.scope, self.package)
        self.receiver = AuthenticatedReceiver(self.root / "receiver.sqlite", self.trust, self.receipt_key, clock=lambda: self.now)
        self.receiver.enroll_fixture(self.scope, self.node.public_key().public_bytes_raw(), self.snap["visit"])

    def issue(self, version=1):
        return self.authority.issue(self.scope, self.node.public_key().public_bytes_raw(), self.snap, version=version, lease_expires_at=17200)

    def event(self, action="entry", request_id="request-1"):
        args = {"request_id": request_id, "visit": self.snap["visit"], "action": action,
                "credential": self.snap["credential"] if action == "entry" else ""}
        proof = encode(self.node.sign(proof_message(self.package, self.scope, **args)))
        return self.journal.record(self.scope, **args, proof=proof)

    def sync(self, send=None, **kwargs):
        return sync_authenticated(self.journal, self.scope, send or self.receiver.receive,
                                  node_key=self.node, receiver_public_key=self.receipt_key.public_key().public_bytes_raw(), **kwargs)

    def state(self):
        with database(self.receiver.path) as db:
            return (db.execute("SELECT state FROM projection WHERE scope=?", (self.scope.key,)).fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
                    db.execute("SELECT COUNT(*) FROM audit_outbox").fetchone()[0])

    def test_http_authenticated_roundtrip_and_isolation(self):
        server = make_receiver_server(self.receiver)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            send = loopback_sender(f"http://127.0.0.1:{server.server_port}/lab/o2/events")
            self.event()
            self.event("exit", "request-2")
            self.assertEqual(self.sync(send), 2)
            self.assertEqual(self.state(), ("salida_registrada", 2, 2))
            self.assertEqual(self.sync(send), 0)
            self.assertEqual(self.journal.state(self.scope)["events"][-1]["status"], "accepted")
            with self.assertRaises(urllib.error.HTTPError):
                send({"unsigned": True})
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_loss_after_commit_retry_after_receiver_restart(self):
        self.event()
        with self.assertRaises(ConnectionError):
            self.sync(lose_ack=True)
        self.receiver = AuthenticatedReceiver(self.receiver.path, self.trust, self.receipt_key, clock=lambda: self.now)
        self.sync()
        self.assertEqual(self.state(), ("entrada_registrada", 1, 1))

    def test_cancelled_visit_preserved_with_observations_and_audit(self):
        self.receiver.cancel_fixture(self.scope)
        self.event()
        self.event("exit", "request-2")
        self.sync()
        self.assertEqual(self.state(), ("cancelada", 2, 2))
        self.assertEqual([e["status"] for e in self.journal.state(self.scope)["events"]], ["conflict", "conflict"])

    def test_unknown_or_revoked_device_cannot_ingest(self):
        event = self.event()
        self.receiver.disable_fixture(self.scope)
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, self.package, event, self.node))
        self.assertEqual(self.state()[1:], (0, 0))

    def test_wrong_transport_key_rejected(self):
        event = self.event()
        wrong = Ed25519PrivateKey.generate()
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, self.package, event, wrong))

    def test_transport_covers_complete_event(self):
        req = signed_request(self.scope, self.package, self.event(), self.node)
        req["event"]["observed_at"] += 1
        with self.assertRaises(Denied):
            self.receiver.receive(req)

    def test_tenant_crossing_rejected_even_when_request_resigned(self):
        event = self.event()
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(SCOPES["B"], self.package, event, self.node))

    def test_invalid_issuer_package_rejected_even_with_valid_node_signature(self):
        event = self.event()
        package = deepcopy(self.package)
        package["claims"]["snapshot"]["expires_at"] += 1
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, package, event, self.node))

    def test_invalid_capture_proof_rejected(self):
        event = self.event()
        event["authorization"]["node_signature"] = encode(b"0" * 64)
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, self.package, event, self.node))

    def test_same_uid_different_signed_content_rejected(self):
        event = self.event()
        self.receiver.receive(signed_request(self.scope, self.package, event, self.node))
        event["observed_at"] += 1
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, self.package, event, self.node))
        self.assertEqual(self.state()[1:], (1, 1))

    def test_sequence_gap_is_not_acknowledged(self):
        self.event()
        second = self.event("exit", "request-2")
        with self.assertRaises(Denied):
            self.receiver.receive(signed_request(self.scope, self.package, second, self.node))
        self.assertEqual(self.state()[1:], (0, 0))

    def test_expired_on_reception_but_valid_at_observation(self):
        self.event()
        self.now = 20000
        self.sync()
        self.assertEqual(self.state(), ("entrada_registrada", 1, 1))

    def test_known_revoked_lease_keeps_fact_for_review(self):
        self.event()
        self.receiver.trust = PackageTrust(self.trust.keys, revoked_leases=[self.package["claims"]["lease_id"]])
        self.sync()
        self.assertEqual(self.state(), ("pendiente", 1, 1))
        self.assertEqual(self.journal.state(self.scope)["events"][0]["status"], "conflict")

    def test_clock_future_observation_is_received_as_conflict(self):
        event = self.event()
        event["observed_at"] = self.now + 1
        ack = self.receiver.receive(signed_request(self.scope, self.package, event, self.node))
        self.assertEqual(ack["receipt"]["status"], "conflict")
        self.assertEqual(self.state(), ("pendiente", 1, 1))

    def test_renewal_keeps_historical_packages_for_pending_events(self):
        first = self.event()
        self.snap["expires_at"] += 1
        self.package = self.issue(version=2)
        self.journal.install(self.scope, self.package)
        self.event("exit", "request-2")
        self.sync()
        self.assertEqual(self.state(), ("salida_registrada", 2, 2))
        self.assertEqual(self.journal.state(self.scope)["events"][0]["event_uid"], first["event_uid"])

    def test_untrusted_receipt_key_leaves_pending(self):
        self.event()
        wrong = Ed25519PrivateKey.generate()
        with self.assertRaises(Denied):
            sync_authenticated(self.journal, self.scope, self.receiver.receive, node_key=self.node,
                               receiver_public_key=wrong.public_key().public_bytes_raw())
        self.assertEqual(self.journal.state(self.scope)["events"][0]["status"], "pending")
        self.sync()
        self.assertEqual(self.state()[1:], (1, 1))

    def test_modified_receipt_is_not_acknowledged_locally(self):
        self.event()
        def malicious(request):
            ack = self.receiver.receive(request)
            ack["receipt"]["event_uid"] = "another"
            return ack
        with self.assertRaises(Denied):
            self.sync(malicious)
        self.assertEqual(self.journal.state(self.scope)["events"][0]["status"], "pending")

    def test_outbox_failure_rolls_back_observation_and_projection(self):
        self.event()
        with database(self.receiver.path) as db:
            db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_outbox BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.sync()
        self.assertEqual(self.state(), ("pendiente", 0, 0))
        self.assertEqual(self.journal.state(self.scope)["events"][0]["status"], "pending")

    def test_no_external_transport_or_redirect_destination(self):
        for url in ("https://example.invalid/lab/o2/events", "http://localhost:8766/lab/o2/events", "http://127.0.0.1:8766/other"):
            with self.subTest(url=url), self.assertRaises(Denied):
                loopback_sender(url)

    def test_receiver_keeps_original_fact_and_outbox_append_only(self):
        self.event()
        self.sync()
        for table in ("observations", "audit_outbox"):
            with self.subTest(table=table), self.assertRaises(sqlite3.IntegrityError), database(self.receiver.path) as db:
                db.execute(f"DELETE FROM {table}")
        with database(self.journal.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM verified_acknowledgments").fetchone()[0], 1)

    def test_event_extra_field_or_nonfinite_time_rejected(self):
        for change in ({"extra": "field"}, {"observed_at": float("nan")}):
            event = {**self.event(), **change}
            with self.assertRaises(Denied):
                self.receiver.receive(signed_request(self.scope, self.package, event, self.node))


if __name__ == "__main__":
    unittest.main()
