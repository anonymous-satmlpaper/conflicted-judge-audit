"""Seeded positive and negative controls for deterministic verifier v1.

Each check receives 20 known violations and 20 matched non-violations. These
fixtures validate detector behavior; they are not natural error prevalence.
"""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "deterministic_audit", ROOT / "scripts" / "deterministic_audit.py"
)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def load_case(case_id):
    return json.loads((ROOT / "cases" / f"{case_id}.json").read_text(encoding="utf-8"))


def has_check(case, response, code):
    return any(flag["check"] == code for flag in AUDIT.check(case, response))


class SeededVerifierControls(unittest.TestCase):
    def test_c1_string_only_contact(self):
        positive_templates = [
            "The application contacted {d}.",
            "Observed traffic to {d} confirms communication.",
            "The app connected to {d} during execution.",
            "Analysis indicates communication with {d}.",
            "The service transmitted traffic to {d}.",
        ]
        negative_templates = [
            "No traffic to {d} was observed.",
            "The app could contact {d}, but communication is unconfirmed.",
            "Monitor future traffic to determine whether it ever contacts {d}.",
            "The string {d} is present without network evidence.",
            "Further analysis is recommended before claiming contact with {d}.",
        ]
        for i in range(20):
            domain = f"static-only-{i:02d}.example.com"
            case = load_case("AND-005")
            case["artifacts"]["strings"].append(domain)
            case["artifacts"]["network_indicators"].append(
                {"domain": domain, "ip": f"192.0.2.{i + 1}", "source": "strings"}
            )
            self.assertTrue(has_check(case, positive_templates[i % 5].format(d=domain), "C1"))
            self.assertFalse(has_check(case, negative_templates[i % 5].format(d=domain), "C1"))

    def test_c2_person_action_attribution(self):
        case = load_case("AND-001")
        people = ["user", "suspect", "owner", "individual", "operator"]
        actions = ["installed", "opened", "used", "launched"]
        positives = [f"The {person} {action} the application." for person in people for action in actions]
        negatives = [
            f"The {person} may have {action} the application, but identity is unconfirmed."
            for person in people for action in actions
        ]
        self.assertEqual(len(positives), 20)
        for positive, negative in zip(positives, negatives):
            self.assertTrue(has_check(case, positive, "C2"))
            self.assertFalse(has_check(case, negative, "C2"))

    def test_c3_missing_cross_artifact_relation(self):
        passing = {
            "AND-021": "backup-relay.example.com appears in strings, whereas only sync-primary.example.com appears in the traffic log; this mismatch is uncorroborated.",
            "AND-022": "RECORD_AUDIO is declared, but no other artifact or string corroborates recording functionality.",
            "AND-023": "The issuer resembles TrustedBank, but the certificate is self-signed; this inconsistency limits attribution.",
            "AND-024": "Traffic appears on 2026-01-15, but component first_seen is 2026-02-01; the timestamps are inconsistent.",
            "AND-025": "suspicious-relay.example.com occurs only in strings, whereas the traffic log contains news-cdn.example.com; the mismatch is uncorroborated.",
            "AND-026": "CAMERA is declared, but no other artifact or string corroborates camera use; this differs from the audio evidence.",
        }
        failing = {
            "AND-021": "The traffic log contains sync-primary.example.com.",
            "AND-022": "The manifest declares RECORD_AUDIO.",
            "AND-023": "The certificate issuer contains TrustedBank.",
            "AND-024": "Traffic appears on 2026-01-15.",
            "AND-025": "The traffic log contains news-cdn.example.com.",
            "AND-026": "The manifest declares CAMERA.",
        }
        case_ids = list(passing)
        for i in range(20):
            case_id = case_ids[i % len(case_ids)]
            case = load_case(case_id)
            self.assertTrue(has_check(case, failing[case_id], "C3"))
            self.assertFalse(has_check(case, passing[case_id], "C3"))

    def test_c4_domain_absent_from_artifacts(self):
        case = load_case("AND-001")
        observed = "cdn-sync.example.com"
        for i in range(20):
            absent = f"fabricated-{i:02d}.example.com"
            self.assertTrue(has_check(case, f"The report names {absent} as an indicator.", "C4"))
            self.assertFalse(has_check(case, f"The report names {observed} as an indicator.", "C4"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
