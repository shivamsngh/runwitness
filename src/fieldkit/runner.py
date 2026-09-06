import json
import os
import platform
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .evidence import directory_bytes, host_evidence, sha256
from .gates import evaluate
from .metrics import extract_metrics
from .report import render_report


def _venv_python(venv):
    unix = Path(venv) / "bin" / "python"
    windows = Path(venv) / "Scripts" / "python.exe"
    return unix if unix.is_file() else windows


def _command(argv, benchmark):
    command = list(argv)
    venv = benchmark.get("venv")
    if venv and Path(command[0]).name in {"python", "python3", "python.exe"}:
        interpreter = _venv_python(venv)
        if not interpreter.is_file():
            raise ValueError(f"virtual environment has no Python interpreter: {venv}")
        command[0] = str(interpreter)
    return command


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rss_kb(pid):
    try:
        result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True,
                                text=True, timeout=2, check=False)
        return int(result.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def _child_high_water_mb():
    try:
        import resource
        value = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        divisor = 1048576 if platform.system() == "Darwin" else 1024
        return round(value / divisor, 3)
    except (ImportError, ValueError):
        return None


def _execute(argv, cwd, timeout, stdout_path, stderr_path):
    peak = {"kb": 0}
    started = time.monotonic()
    with Path(stdout_path).open("w", encoding="utf-8") as out, Path(stderr_path).open("w", encoding="utf-8") as err:
        process = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, text=True)
        peak["kb"] = _rss_kb(process.pid)
        stop = threading.Event()

        def observe():
            while not stop.wait(0.05):
                peak["kb"] = max(peak["kb"], _rss_kb(process.pid))

        watcher = threading.Thread(target=observe, daemon=True)
        watcher.start()
        timed_out = False
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            exit_code = process.wait()
        finally:
            stop.set()
            watcher.join(timeout=1)
    observed_mb = round(peak["kb"] / 1024, 3) if peak["kb"] else None
    source = "pid polling via ps"
    if observed_mb is None:
        observed_mb = _child_high_water_mb()
        source = "OS completed-child high-water mark fallback" if observed_mb is not None else "unavailable"
    return {"argv": argv, "exit_code": exit_code, "timed_out": timed_out,
            "wall_seconds": round(time.monotonic() - started, 4),
            "peak_rss_mb": observed_mb, "memory_measurement_source": source}


def _collector_command(command, deployment, evidence_path):
    collector = deployment.get("collector")
    if not collector:
        return command
    options = ["run", "--output", str(evidence_path),
               "--sample-interval-ms", str(collector.get("sample_interval_ms", 100))]
    if deployment.get("network", {}).get("mode") == "deny":
        options.append("--network-deny")
    return list(collector["command"]) + options + ["--"] + command


def _safe_source(workdir, relative):
    root = Path(workdir).resolve()
    source = (root / relative).resolve()
    if source != root and root not in source.parents:
        raise ValueError(f"native result escapes benchmark workdir: {relative}")
    return source


def run(config, config_path, output_dir):
    benchmark, deployment = config["benchmark"], config["deployment"]
    workdir = Path(benchmark["workdir"])
    if not workdir.is_dir():
        raise ValueError(f"benchmark workdir does not exist: {workdir}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    bundle = Path(output_dir).resolve()
    bundle.mkdir(parents=True, exist_ok=False)
    logs = bundle / "logs"
    native = bundle / "benchmark"
    evidence_dir = bundle / "evidence"
    logs.mkdir(); native.mkdir(); evidence_dir.mkdir()
    timeout = float(deployment.get("timeout_seconds", 3600))
    disk_before = directory_bytes(workdir)
    validation = None
    if benchmark.get("validate"):
        validation = _execute(_command(benchmark["validate"], benchmark), workdir, timeout,
                              logs / "validate.stdout.txt", logs / "validate.stderr.txt")
    if validation and (validation["exit_code"] != 0 or validation["timed_out"]):
        execution = {"argv": benchmark["run"], "exit_code": None, "timed_out": False,
                     "wall_seconds": 0, "peak_rss_mb": 0, "skipped": "validation failed"}
    else:
        prefix = deployment.get("execution", {}).get("command_prefix", [])
        benchmark_command = prefix + _command(benchmark["run"], benchmark)
        wrapped_command = _collector_command(benchmark_command, deployment, evidence_dir / "system.json")
        execution = _execute(wrapped_command, workdir, timeout,
                             logs / "run.stdout.txt", logs / "run.stderr.txt")
    disk_after = directory_bytes(workdir)
    copied = []
    for relative in benchmark.get("native_results", []):
        source = _safe_source(workdir, relative)
        if source.is_file():
            destination = native / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied.append({"path": str(destination.relative_to(bundle)), "sha256": sha256(destination),
                           "bytes": destination.stat().st_size})
    mapped, mapping_errors = extract_metrics(benchmark.get("metrics", {}), workdir)
    network = deployment.get("network", {})
    isolation = {
        "requested_mode": network.get("mode", "not_enforced"),
        "enforced": bool(deployment.get("execution", {}).get("command_prefix")),
        "mechanism": deployment.get("execution", {}).get("mechanism"),
        "note": "FieldKit records configured enforcement; it does not infer zero network activity."
    }
    metrics = dict(mapped)
    metrics.update({"runtime.wall_seconds": execution["wall_seconds"],
                    "runtime.exit_code": execution["exit_code"],
                    "resources.peak_rss_mb": execution["peak_rss_mb"],
                    "resources.workdir_delta_mb": round((disk_after - disk_before) / 1048576, 3),
                    "isolation.enforced": isolation["enforced"]})
    system_evidence = None
    system_evidence_path = evidence_dir / "system.json"
    if deployment.get("collector") and system_evidence_path.is_file():
        try:
            system_evidence = json.loads(system_evidence_path.read_text(encoding="utf-8"))
            system_evidence["artifact"] = {"path": "evidence/system.json", "sha256": sha256(system_evidence_path)}
            if system_evidence.get("status") == "complete":
                metrics["resources.process_tree_peak_rss_mb"] = round(system_evidence["peak_tree_rss_bytes"] / 1048576, 3)
                metrics["resources.process_tree_peak_count"] = system_evidence["peak_process_count"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            system_evidence = {"status": "invalid", "note": "collector evidence could not be parsed"}
    if system_evidence and system_evidence.get("network"):
        isolation.update(system_evidence["network"])
        metrics["isolation.enforced"] = isolation["enforced"]
    run_valid = execution.get("exit_code") == 0 and not execution.get("timed_out")
    decision = evaluate(deployment.get("gates", []), metrics, run_valid)
    manifest = {
        "schema_version": "0.1", "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": {"name": benchmark["name"], "version": benchmark.get("version"),
                      "workdir": str(workdir), "venv": benchmark.get("venv"),
                      "native_results": copied},
        "deployment": {"name": deployment.get("name", "unnamed"),
                       "policy": deployment.get("policy"), "network": isolation},
        "host": host_evidence(), "validation": validation,
        "execution": {**execution, "resource_scope": ("benchmark root process and sampled descendants; external runtimes require adapter-native evidence"
                                                        if system_evidence and system_evidence.get("status") == "complete"
                                                        else "adapter root process only; external runtimes require adapter-native evidence")},
        "collector": system_evidence,
        "metrics": metrics, "metric_mapping_errors": mapping_errors,
        "config": {"path": str(config_path), "sha256": sha256(config_path)},
    }
    _write_json(evidence_dir / "runtime.json", execution)
    _write_json(evidence_dir / "host.json", manifest["host"])
    _write_json(evidence_dir / "isolation.json", isolation)
    _write_json(bundle / "decision.json", decision)
    _write_json(bundle / "manifest.json", manifest)
    (bundle / "report.html").write_text(render_report(manifest, decision), encoding="utf-8")
    return bundle, decision
