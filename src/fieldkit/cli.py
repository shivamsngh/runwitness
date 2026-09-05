import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .runner import run


def parser():
    root = argparse.ArgumentParser(prog="fieldkit", description="Run any benchmark with deployment evidence")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate an adapter and policy")
    validate.add_argument("config")
    execute = commands.add_parser("run", help="run a benchmark and create an evidence bundle")
    execute.add_argument("config")
    execute.add_argument("--output", required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        config, source = load_config(args.config)
        if args.command == "validate":
            print(json.dumps({"valid": True, "benchmark": config["benchmark"]["name"]}))
            return 0
        bundle, decision = run(config, source, Path(args.output))
        print(json.dumps({"bundle": str(bundle), "decision": decision["overall"]}))
        return 0 if decision["overall"] == "pass" else 2
    except (ConfigError, OSError, ValueError) as exc:
        print(f"fieldkit: {exc}", file=sys.stderr)
        return 1
