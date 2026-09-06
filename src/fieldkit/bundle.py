import json
from pathlib import Path

from .evidence import sha256


def _json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_bundle(bundle):
    root = Path(bundle).resolve()
    manifest_path = root / "manifest.json"
    decision_path = root / "decision.json"
    checks = []
    for path, name in ((manifest_path, "manifest"), (decision_path, "decision")):
        checks.append({"name": name, "path": str(path), "status": "pass" if path.is_file() else "fail"})
    if not manifest_path.is_file():
        return {"bundle": str(root), "overall": "fail", "checks": checks}
    manifest = _json(manifest_path)
    for artifact in manifest.get("benchmark", {}).get("native_results", []):
        relative = artifact.get("path", "")
        target = (root / relative).resolve()
        safe = target == root or root in target.parents
        if not safe or not target.is_file():
            status, actual = "fail", None
        else:
            actual = sha256(target)
            status = "pass" if actual == artifact.get("sha256") else "fail"
        checks.append({"name": "native_result", "path": relative, "expected_sha256": artifact.get("sha256"),
                       "actual_sha256": actual, "status": status})
    return {"bundle": str(root), "run_id": manifest.get("run_id"),
            "overall": "pass" if checks and all(x["status"] == "pass" for x in checks) else "fail",
            "checks": checks}


def compare_bundles(left, right):
    left_manifest = _json(Path(left) / "manifest.json")
    right_manifest = _json(Path(right) / "manifest.json")
    left_metrics = left_manifest.get("metrics", {})
    right_metrics = right_manifest.get("metrics", {})
    metrics = []
    for name in sorted(set(left_metrics) | set(right_metrics)):
        before, after = left_metrics.get(name), right_metrics.get(name)
        numeric = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)
        delta = after - before if numeric(before) and numeric(after) else None
        metrics.append({"metric": name, "left": before, "right": after, "delta": delta})
    warnings = []
    if left_manifest.get("benchmark", {}).get("name") != right_manifest.get("benchmark", {}).get("name"):
        warnings.append("benchmark names differ")
    if left_metrics.get("quality.document_count") != right_metrics.get("quality.document_count"):
        warnings.append("document counts differ; aggregate quality is not directly comparable")
    return {
        "left": {"bundle": str(Path(left).resolve()), "run_id": left_manifest.get("run_id"),
                 "benchmark": left_manifest.get("benchmark", {}).get("name")},
        "right": {"bundle": str(Path(right).resolve()), "run_id": right_manifest.get("run_id"),
                  "benchmark": right_manifest.get("benchmark", {}).get("name")},
        "metrics": metrics, "warnings": warnings,
    }
