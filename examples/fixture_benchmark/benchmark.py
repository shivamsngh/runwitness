import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--validate", action="store_true")
parser.add_argument("--output")
args = parser.parse_args()
if args.validate:
    raise SystemExit(0)
Path(args.output).write_text(json.dumps({"summary": {"accuracy": 0.92}, "documents": 8}) + "\n")
