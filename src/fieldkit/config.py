import json
import os
from pathlib import Path


class ConfigError(ValueError):
    pass


def load_config(path):
    source = Path(path).resolve()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(str(exc)) from exc
    validate_config(data)
    benchmark = data["benchmark"]
    raw_workdir = os.path.expandvars(benchmark.get("workdir", "."))
    workdir = Path(raw_workdir).expanduser()
    if not workdir.is_absolute():
        workdir = source.parent / workdir
    benchmark["workdir"] = str(workdir.resolve())
    if benchmark.get("venv"):
        venv = Path(os.path.expandvars(benchmark["venv"])).expanduser()
        if not venv.is_absolute():
            venv = workdir / venv
        benchmark["venv"] = str(venv.resolve())
    for key in ("validate", "run"):
        if key in benchmark:
            benchmark[key] = [os.path.expandvars(part) for part in benchmark[key]]
    collector = data["deployment"].get("collector")
    if collector:
        collector["command"] = [os.path.expandvars(part) for part in collector["command"]]
        executable = Path(collector["command"][0]).expanduser()
        if not executable.is_absolute() and len(executable.parts) > 1:
            collector["command"][0] = str((source.parent / executable).resolve())
    return data, source


def validate_config(data):
    if not isinstance(data, dict):
        raise ConfigError("configuration must be a JSON object")
    if data.get("schema_version") != "0.1":
        raise ConfigError("schema_version must be '0.1'")
    benchmark = data.get("benchmark")
    deployment = data.get("deployment")
    if not isinstance(benchmark, dict) or not isinstance(deployment, dict):
        raise ConfigError("benchmark and deployment objects are required")
    if not benchmark.get("name"):
        raise ConfigError("benchmark.name is required")
    command = benchmark.get("run")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ConfigError("benchmark.run must be a non-empty argv array")
    if "validate" in benchmark and not isinstance(benchmark["validate"], list):
        raise ConfigError("benchmark.validate must be an argv array")
    if not isinstance(deployment.get("gates", []), list):
        raise ConfigError("deployment.gates must be an array")
    collector = deployment.get("collector")
    if collector is not None:
        if not isinstance(collector, dict) or not isinstance(collector.get("command"), list) or not collector["command"]:
            raise ConfigError("deployment.collector.command must be a non-empty argv array")
        if not all(isinstance(part, str) for part in collector["command"]):
            raise ConfigError("deployment.collector.command must contain strings")
        interval = collector.get("sample_interval_ms", 100)
        if not isinstance(interval, int) or interval < 10:
            raise ConfigError("deployment.collector.sample_interval_ms must be an integer of at least 10")
    for gate in deployment.get("gates", []):
        if not isinstance(gate, dict) or not gate.get("metric") or gate.get("op") not in {
            "==", "!=", ">", ">=", "<", "<=", "exists"
        }:
            raise ConfigError("each gate needs metric and a supported op")
