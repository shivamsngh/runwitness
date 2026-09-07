import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from runwitness.aws_evidence import (  # noqa: E402
    AwsEvidenceError,
    EVALUATOR_VERSION,
    SCHEMA_VERSION,
    evaluate_aws_evidence,
    evaluate_aws_evidence_file,
)
from runwitness.cli import main  # noqa: E402


FIXTURES = ROOT / "examples" / "aws_evidence"


class AwsEvidenceTests(unittest.TestCase):
    def load(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_sanitized_fixture_outcomes(self):
        expected = {
            "pass.json": "pass",
            "fail-public-path.json": "fail",
            "unknown-missing.json": "unknown",
            "unknown-permission-denied.json": "unknown",
            "unknown-stale.json": "unknown",
        }
        for name, outcome in expected.items():
            with self.subTest(name=name):
                result = evaluate_aws_evidence_file(FIXTURES / name)
                self.assertEqual(result["overall"], outcome)
                self.assertEqual(result["schema_version"], SCHEMA_VERSION)
                self.assertEqual(result["evaluator_version"], EVALUATOR_VERSION)

    def test_pass_has_traceable_control_decisions(self):
        result = evaluate_aws_evidence(self.load("pass.json"))
        self.assertTrue(result["decisions"])
        for decision in result["decisions"]:
            self.assertEqual(decision["status"], "pass")
            self.assertTrue(decision["evidence_references"])
            self.assertTrue(all(pointer.startswith("/") for pointer in decision["evidence_references"]))

    def test_failure_takes_precedence_over_unknown(self):
        evidence = self.load("fail-public-path.json")
        evidence["sources"]["logging"] = {"status": "permission_denied", "reason": "fixture"}
        result = evaluate_aws_evidence(evidence)
        self.assertEqual(result["overall"], "fail")
        self.assertIn("unknown", {item["status"] for item in result["decisions"]})

    def test_invalid_takes_precedence(self):
        evidence = self.load("pass.json")
        evidence["sources"]["storage"]["data"]["encrypted"] = "yes"
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "invalid")

    def test_missing_source_never_passes(self):
        evidence = self.load("pass.json")
        del evidence["sources"]["routes"]
        result = evaluate_aws_evidence(evidence)
        self.assertEqual(result["overall"], "unknown")
        self.assertEqual(next(item for item in result["decisions"] if item["control"] == "routes")["status"], "unknown")

    def test_endpoint_allowlist_is_exact(self):
        evidence = self.load("pass.json")
        evidence["sources"]["endpoints"]["data"]["service_names"] = ["com.amazonaws.us-east-1.s3"]
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "fail")
        evidence["profile"]["network_variant"] = "restricted_egress"
        evidence["profile"]["allowed_endpoint_services"] = ["com.amazonaws.us-east-1.s3"]
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "pass")

    def test_strict_variant_rejects_an_endpoint_allowlist(self):
        evidence = self.load("pass.json")
        evidence["profile"]["allowed_endpoint_services"] = ["com.amazonaws.us-east-1.s3"]
        evidence["sources"]["endpoints"]["data"]["service_names"] = ["com.amazonaws.us-east-1.s3"]
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "invalid")

    def test_incomplete_scope_is_invalid(self):
        evidence = self.load("pass.json")
        evidence["scope"]["account_ref"] = ""
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "invalid")

    def test_artifact_mismatch_fails(self):
        evidence = self.load("pass.json")
        evidence["sources"]["artifacts"]["data"]["observed_digests"]["model"] = "sha256:different"
        result = evaluate_aws_evidence(evidence)
        self.assertEqual(result["overall"], "fail")
        self.assertEqual(next(item for item in result["decisions"] if item["control"] == "artifact_identity")["status"], "fail")

    def test_bad_window_is_invalid(self):
        evidence = self.load("pass.json")
        evidence["evaluation_window"]["end"] = evidence["evaluation_window"]["start"]
        self.assertEqual(evaluate_aws_evidence(evidence)["overall"], "invalid")

    def test_wrong_schema_version_is_rejected(self):
        evidence = self.load("pass.json")
        evidence["schema_version"] = "future"
        with self.assertRaises(AwsEvidenceError):
            evaluate_aws_evidence(evidence)

    def test_fixtures_contain_only_sanitized_scope_references(self):
        for path in FIXTURES.glob("*.json"):
            evidence = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(path=path.name):
                self.assertTrue(evidence["scope"]["account_ref"].startswith("sanitized:"))
                self.assertTrue(evidence["scope"]["instance_ref"].startswith("sanitized:"))
                self.assertTrue(evidence["scope"]["subnet_ref"].startswith("sanitized:"))
                self.assertNotIn("arn:aws:", path.read_text(encoding="utf-8"))

    def test_cli_writes_machine_readable_decision(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "decision.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["aws-evaluate", str(FIXTURES / "pass.json"), "--output", str(output)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["overall"], "pass")
            self.assertEqual(json.loads(stdout.getvalue())["overall"], "pass")


if __name__ == "__main__":
    unittest.main()
