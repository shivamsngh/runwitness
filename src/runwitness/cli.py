import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, load_config
from .bundle import compare_bundles, verify_bundle
from .runner import run
from .aws_evidence import AwsEvidenceError, evaluate_aws_evidence_file


def parser():
    root = argparse.ArgumentParser(prog="runwitness", description="Run any benchmark with deployment evidence")
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate an adapter and policy")
    validate.add_argument("config")
    execute = commands.add_parser("run", help="run a benchmark and create an evidence bundle")
    execute.add_argument("config")
    execute.add_argument("--output", required=True)
    verify = commands.add_parser("verify", help="verify evidence-bundle artifact hashes")
    verify.add_argument("bundle")
    compare = commands.add_parser("compare", help="compare metrics from two evidence bundles")
    compare.add_argument("left")
    compare.add_argument("right")
    aws_evaluate = commands.add_parser("aws-evaluate", help="evaluate a caller-supplied AWS evidence document offline")
    aws_evaluate.add_argument("evidence")
    aws_evaluate.add_argument("--output")
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_bundle(args.bundle)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["overall"] == "pass" else 2
        if args.command == "compare":
            print(json.dumps(compare_bundles(args.left, args.right), indent=2, sort_keys=True))
            return 0
        if args.command == "aws-evaluate":
            result = evaluate_aws_evidence_file(args.evidence)
            rendered = json.dumps(result, indent=2, sort_keys=True)
            if args.output:
                Path(args.output).write_text(rendered + "\n", encoding="utf-8")
            print(rendered)
            return 0 if result["overall"] == "pass" else 2
        config, source = load_config(args.config)
        if args.command == "validate":
            print(json.dumps({"valid": True, "benchmark": config["benchmark"]["name"]}))
            return 0
        bundle, decision = run(config, source, Path(args.output))
        print(json.dumps({"bundle": str(bundle), "decision": decision["overall"]}))
        return 0 if decision["overall"] == "pass" else 2
    except (AwsEvidenceError, ConfigError, OSError, ValueError) as exc:
        print(f"runwitness: {exc}", file=sys.stderr)
        return 1
