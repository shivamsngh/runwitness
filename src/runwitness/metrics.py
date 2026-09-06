import json
from pathlib import Path


def lookup(value, path):
    current = value
    for part in path.split(".") if path else []:
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def extract_metrics(mapping, workdir):
    values, errors = {}, {}
    for name, spec in mapping.items():
        try:
            source = (Path(workdir) / spec["file"]).resolve()
            root = Path(workdir).resolve()
            if source != root and root not in source.parents:
                raise ValueError("metric file escapes benchmark workdir")
            document = json.loads(source.read_text(encoding="utf-8"))
            values[name] = lookup(document, spec.get("path", ""))
        except (OSError, ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            errors[name] = str(exc)
    return values, errors
