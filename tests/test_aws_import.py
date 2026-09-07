import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from runwitness.aws_evidence import AwsEvidenceError  # noqa: E402
from runwitness.aws_import import IMPORT_VERSION, import_aws_capture, verify_aws_import_bundle  # noqa: E402
from runwitness.evidence import sha256  # noqa: E402

FIXTURES = ROOT / "examples" / "aws_import"


class AwsImportTests(unittest.TestCase):
    def test_pass_import_is_offline_and_preserves_hashed_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            output, decision = import_aws_capture(FIXTURES / "pass" / "capture.json", Path(folder) / "bundle")
            self.assertEqual(decision["overall"], "pass")
            evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema_version"], IMPORT_VERSION)
            self.assertEqual(sha256(output / "capture.json"), manifest["capture_manifest_sha256"])
            self.assertEqual(len(manifest["artifacts"]), 9)
            for artifact in manifest["artifacts"]:
                self.assertEqual(sha256(output / artifact["path"]), artifact["sha256"])
            self.assertIsNone(evidence["sources"]["ec2"]["data"]["public_ipv4"])
            self.assertEqual(evidence["sources"]["routes"]["data"]["entries"][0]["target_type"], "local")
            self.assertEqual(verify_aws_import_bundle(output)["overall"], "pass")

    def test_verifier_detects_tampered_raw_source(self):
        with tempfile.TemporaryDirectory() as folder:
            output, _ = import_aws_capture(FIXTURES / "pass" / "capture.json", Path(folder) / "bundle")
            (output / "raw" / "routes.json").write_text("{}", encoding="utf-8")
            result = verify_aws_import_bundle(output)
            self.assertEqual(result["overall"], "fail")
            failed = [item for item in result["checks"] if item["status"] == "fail"]
            self.assertEqual(failed[0]["path"], "raw/routes.json")

    def test_permission_denied_becomes_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            output, decision = import_aws_capture(FIXTURES / "permission-denied" / "capture.json", Path(folder) / "bundle")
            self.assertEqual(decision["overall"], "unknown")
            evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["sources"]["ec2"]["status"], "permission_denied")
            self.assertEqual(evidence["sources"]["packet_controls"]["status"], "unavailable")

    def test_public_gateway_import_fails_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            capture_root = Path(folder) / "capture"
            shutil.copytree(FIXTURES / "pass", capture_root)
            route_path = capture_root / "raw" / "describe-route-tables.json"
            routes = json.loads(route_path.read_text(encoding="utf-8"))
            routes["RouteTables"][0]["Routes"].append({"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-fixture", "State": "active"})
            route_path.write_text(json.dumps(routes), encoding="utf-8")
            _, decision = import_aws_capture(capture_root / "capture.json", Path(folder) / "bundle")
            self.assertEqual(decision["overall"], "fail")
            route_decision = next(item for item in decision["decisions"] if item["control"] == "public_routes")
            self.assertIn("internet_gateway", route_decision["reason"])

    def test_empty_scoped_response_becomes_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            capture_root = Path(folder) / "capture"
            shutil.copytree(FIXTURES / "pass", capture_root)
            groups_path = capture_root / "raw" / "describe-security-groups.json"
            groups_path.write_text('{"SecurityGroups":[]}', encoding="utf-8")
            output, decision = import_aws_capture(capture_root / "capture.json", Path(folder) / "bundle")
            self.assertEqual(decision["overall"], "unknown")
            evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["sources"]["packet_controls"]["status"], "unavailable")

    def test_import_rejects_path_escape_and_removes_partial_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            capture_root = Path(folder) / "capture"
            shutil.copytree(FIXTURES / "pass", capture_root)
            capture_path = capture_root / "capture.json"
            capture = json.loads(capture_path.read_text(encoding="utf-8"))
            capture["inputs"]["ec2"]["path"] = "../outside.json"
            capture_path.write_text(json.dumps(capture), encoding="utf-8")
            output = Path(folder) / "bundle"
            with self.assertRaises(AwsEvidenceError):
                import_aws_capture(capture_path, output)
            self.assertFalse(output.exists())

    def test_import_refuses_to_overwrite_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "bundle"
            output.mkdir()
            with self.assertRaises(AwsEvidenceError):
                import_aws_capture(FIXTURES / "pass" / "capture.json", output)


if __name__ == "__main__":
    unittest.main()
