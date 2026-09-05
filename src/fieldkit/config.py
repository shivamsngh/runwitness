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
    for gate in deployment.get("gates", []):
        if not isinstance(gate, dict) or not gate.get("metric") or gate.get("op") not in {
            "==", "!=", ">", ">=", "<", "<=", "exists"
        }:
            raise ConfigError("each gate needs metric and a supported op")
