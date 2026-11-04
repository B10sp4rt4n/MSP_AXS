"""O1 synthetic authority → signed package → node proof → durable SQLite journal."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from labs.contingency.journal import Denied, Journal, SCOPES, database
from labs.contingency.packages import LabAuthority, PackageTrust, VerifiedJournal, encode, proof_message


class SignedPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = 10000.0
        self.scope = SCOPES["A"]
        self.issuer = Ed25519PrivateKey.generate()
        self.node = Ed25519PrivateKey.generate()
        self.public = self.node.public_key().public_bytes_raw()
        self.authority = LabAuthority("issuer-lab-1", self.issuer)
        self.trust = PackageTrust({"issuer-lab-1": self.issuer.public_key().public_bytes_raw()})
        fixture = Journal(self.root / "fixture.sqlite", clock=lambda: self.now)
        fixture.prepare_fixture(self.scope)
        self.snapshot = fixture.state(self.scope)["snapshot"]
        self.local = VerifiedJournal(self.root / "verified.sqlite", self.trust, clock=lambda: self.now)
        self.authority.enroll(self.scope, self.public)
        self.envelope = self.issue()

    def issue(self, **kwargs):
        return self.authority.issue(self.scope, self.public, self.snapshot,
                                    lease_expires_at=17200, **kwargs)

    def record(self, *, action="entry", request_id="request-1", envelope=None, key=None, **kwargs):
        env = envelope or self.envelope
        args = {"request_id": request_id, "visit": self.snapshot["visit"], "action": action,
                "credential": self.snapshot["credential"] if action == "entry" else ""}
        proof = encode((key or self.node).sign(proof_message(env, self.scope, **args)))
        return self.local.record(self.scope, **{**args, **kwargs}, proof=proof)

    def test_signed_package_device_proof_and_restart(self):
        self.local.install(self.scope, self.envelope)
        event = self.record()
        self.assertIn("node_signature", event["authorization"])
        self.local = VerifiedJournal(self.root / "verified.sqlite", self.trust, clock=lambda: self.now)
        self.assertEqual(self.record(), event)
        self.record(action="exit", request_id="request-2")
        self.assertEqual(len(self.local.state(self.scope)["events"]), 2)

    def test_node_does_not_need_issuer_private_key(self):
        self.local.install(self.scope, self.envelope)
        del self.authority, self.issuer
        self.assertEqual(self.record()["action"], "entry")

    def test_no_fixture_bypass_in_verified_adapter(self):
        with self.assertRaises(Denied):
            self.local.prepare_fixture(self.scope)

    def test_no_implicit_downgrade_to_unsigned_o0_receiver(self):
        with self.assertRaises(Denied):
            self.local.sync(self.scope, None)

    def test_uninstalled_scope_cannot_record(self):
        with self.assertRaises(Denied):
            self.record()

    def test_enrollment_is_required_and_revoke_stops_issuance(self):
        self.authority.revoke(self.scope)
        with self.assertRaises(Denied):
            self.issue()

    def test_enrollment_rejects_different_node_key(self):
        wrong = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        with self.assertRaises(Denied):
            self.authority.issue(self.scope, wrong, self.snapshot, lease_expires_at=17200)

    def test_each_scope_dimension_is_bound(self):
        for field in ("msp", "tenant", "gate", "node", "actor"):
            with self.subTest(field=field), self.assertRaises(Denied):
                self.local.install(replace(self.scope, **{field: "other"}), self.envelope)

    def test_altered_signed_snapshot_rejected(self):
        env = deepcopy(self.envelope)
        env["claims"]["snapshot"]["expires_at"] += 1
        with self.assertRaises(Denied):
            self.local.install(self.scope, env)

    def test_unpinned_signer_and_embedded_key_rejected(self):
        self.local.trust = PackageTrust({})
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.envelope)
        env = {**self.envelope, "public_key": encode(self.public)}
        with self.assertRaises(Denied):
            self.local.install(self.scope, env)

    def test_expired_and_future_copy_rejected(self):
        for now in (9999, 13600):
            self.now = now
            with self.subTest(now=now), self.assertRaises(Denied):
                self.local.install(self.scope, self.envelope)

    def test_lease_expiry_blocks_new_observations(self):
        self.local.install(self.scope, self.envelope)
        self.record()
        self.now = 17200
        with self.assertRaises(Denied):
            self.record(action="exit", request_id="request-2")

    def test_expired_snapshot_allows_exit_under_valid_lease(self):
        self.local.install(self.scope, self.envelope)
        self.record()
        self.now = 13600
        self.assertTrue(self.record(action="exit", request_id="request-2")["snapshot_expired"])

    def test_signed_action_permission_enforced(self):
        self.envelope = self.issue(actions=("exit",))
        self.local.install(self.scope, self.envelope)
        with self.assertRaises(Denied):
            self.record()

    def test_wrong_device_private_key_rejected(self):
        self.local.install(self.scope, self.envelope)
        with self.assertRaises(Denied):
            self.record(key=Ed25519PrivateKey.generate())
        self.assertEqual(self.local.state(self.scope)["events"], [])

    def test_node_proof_binds_request_and_intent(self):
        self.local.install(self.scope, self.envelope)
        with self.assertRaises(Denied):
            self.record(visit="another-visit")

    def test_identical_install_does_not_reset_consumption(self):
        self.local.install(self.scope, self.envelope)
        self.record()
        self.local.install(self.scope, self.envelope)
        with self.assertRaises(Denied):
            self.record(request_id="request-new")

    def test_version_rollback_and_version_collision_rejected_after_restart(self):
        self.local.install(self.scope, self.envelope)
        self.local.install(self.scope, self.issue(version=2))
        self.local = VerifiedJournal(self.root / "verified.sqlite", self.trust, clock=lambda: self.now)
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.envelope)
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.issue(version=2, actions=("entry",)))

    def test_renewal_retains_journal_and_consumed_visit(self):
        self.local.install(self.scope, self.envelope)
        event = self.record()
        self.snapshot["expires_at"] += 1
        env = self.issue(version=2)
        self.local.install(self.scope, env)
        self.assertEqual(self.local.state(self.scope)["events"][0]["event_uid"], event["event_uid"])
        with self.assertRaises(Denied):
            self.record(request_id="request-new", envelope=env)

    def test_known_revocation_checked_on_each_record(self):
        self.local.install(self.scope, self.envelope)
        self.local.trust = PackageTrust(self.trust.keys, revoked_leases=[self.envelope["claims"]["lease_id"]])
        with self.assertRaises(Denied):
            self.record()

    def test_known_device_revocation_blocks_install(self):
        self.local.trust = PackageTrust(self.trust.keys, revoked_nodes=[encode(self.public)])
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.envelope)

    def test_local_snapshot_tamper_is_rejected(self):
        self.local.install(self.scope, self.envelope)
        with database(self.local.path) as db:
            db.execute("UPDATE snapshots SET payload='{}'")
        with self.assertRaises(Denied):
            self.record()

    def test_unsigned_o0_database_cannot_be_upgraded_implicitly(self):
        self.local = VerifiedJournal(self.root / "fixture.sqlite", self.trust, clock=lambda: self.now)
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.envelope)

    def test_protocol_rejects_extra_fields_and_nonfinite_clock(self):
        env = deepcopy(self.envelope)
        env["claims"]["private_key"] = "not-allowed"
        with self.assertRaises(Denied):
            self.local.install(self.scope, env)
        self.now = float("nan")
        with self.assertRaises(Denied):
            self.local.install(self.scope, self.envelope)


if __name__ == "__main__":
    unittest.main()
