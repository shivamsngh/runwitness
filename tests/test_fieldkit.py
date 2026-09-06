import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fieldkit.config import ConfigError, load_config, validate_config
from fieldkit.bundle import compare_bundles, verify_bundle
from fieldkit.gates import evaluate
from fieldkit.metrics import extract_metrics
from fieldkit.runner import _command, run


class FieldKitTests(unittest.TestCase):
    def test_verify_and_compare_bundles(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundles = []
            for index, score in enumerate((0.5, 0.8)):
                bundle = root / str(index)
                (bundle / "benchmark").mkdir(parents=True)
                artifact = bundle / "benchmark" / "result.json"
                artifact.write_text(json.dumps({"score": score}))
                import hashlib
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                (bundle / "manifest.json").write_text(json.dumps({
                    "run_id": str(index), "benchmark": {"name": "fixture", "native_results": [
                        {"path": "benchmark/result.json", "sha256": digest}
                    ]}, "metrics": {"quality": score, "isolation": False}
                }))
                (bundle / "decision.json").write_text('{}')
                bundles.append(bundle)
            self.assertEqual(verify_bundle(bundles[0])["overall"], "pass")
            comparison = compare_bundles(bundles[0], bundles[1])
            by_name = {item["metric"]: item for item in comparison["metrics"]}
            self.assertIsNone(by_name["isolation"]["delta"])
            self.assertAlmostEqual(by_name["quality"]["delta"], 0.3)
            (bundles[0] / "benchmark" / "result.json").write_text("tampered")
            self.assertEqual(verify_bundle(bundles[0])["overall"], "fail")
    def test_config_rejects_shell_string(self):
        with self.assertRaises(ConfigError):
            validate_config({"schema_version": "0.1", "benchmark": {"name": "x", "run": "echo x"},
                             "deployment": {"gates": []}})

    def test_metric_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, "result.json").write_text('{"summary":{"score":0.91}}')
            values, errors = extract_metrics({"quality": {"file": "result.json", "path": "summary.score"}}, folder)
            self.assertEqual(values["quality"], 0.91)
            self.assertEqual(errors, {})

    def test_benchmark_virtual_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            interpreter = Path(folder) / "bin" / "python"
            interpreter.parent.mkdir()
            os.symlink(sys.executable, interpreter)
            resolved = _command(["python3", "benchmark.py"], {"venv": folder})
            self.assertEqual(Path(resolved[0]).resolve(), Path(sys.executable).resolve())
            self.assertEqual(resolved[1], "benchmark.py")

    def test_gate_states(self):
        self.assertEqual(evaluate([{"metric": "x", "op": ">=", "value": 1}], {"x": 2})["overall"], "pass")
        self.assertEqual(evaluate([{"metric": "x", "op": ">=", "value": 3}], {"x": 2})["overall"], "fail")
        self.assertEqual(evaluate([{"metric": "missing", "op": "exists"}], {})["overall"], "unknown")
        self.assertEqual(evaluate([], {}, False)["overall"], "invalid")

    def test_end_to_end_bundle(self):
        fixture = ROOT / "examples" / "fixture_benchmark"
        generated = fixture / "native-results.json"
        try:
            config, source = load_config(fixture / "fieldkit.json")
            with tempfile.TemporaryDirectory() as folder:
                destination = Path(folder) / "bundle"
                bundle, decision = run(config, source, destination)
                self.assertEqual(decision["overall"], "pass")
                self.assertTrue((bundle / "manifest.json").is_file())
                self.assertTrue((bundle / "decision.json").is_file())
                self.assertTrue((bundle / "report.html").is_file())
                copied = json.loads((bundle / "benchmark" / "native-results.json").read_text())
                self.assertEqual(copied["summary"]["accuracy"], 0.92)
        finally:
            generated.unlink(missing_ok=True)

    def test_failing_benchmark_is_invalid(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config_file = root / "fieldkit.json"
            config_file.write_text(json.dumps({
                "schema_version": "0.1",
                "benchmark": {"name": "failure", "workdir": ".",
                              "run": [sys.executable, "-c", "raise SystemExit(7)"]},
                "deployment": {"gates": []}
            }))
            config, source = load_config(config_file)
            _, decision = run(config, source, root / "bundle")
            self.assertEqual(decision["overall"], "invalid")


if __name__ == "__main__":
    unittest.main()
