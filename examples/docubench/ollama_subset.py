#!/usr/bin/env python3
"""Run a DocuBench subset through local Ollama without vendoring DocuBench."""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def api(base_url, route, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base_url.rstrip("/") + route, data=data,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def model_identity(base_url, model):
    details = api(base_url, "/api/show", {"model": model})
    tags = api(base_url, "/api/tags")
    tag = next((item for item in tags.get("models", []) if item.get("name") == model), {})
    return {
        "tag": model,
        "digest": tag.get("digest"),
        "details": details.get("details"),
        "capabilities": details.get("capabilities", []),
    }


def runtime_identity(base_url, model):
    try:
        running = api(base_url, "/api/ps").get("models", [])
    except RuntimeError as exc:
        return {"source": "ollama_api_ps_after_request", "unavailable": str(exc),
                "scope": "Ollama runtime allocation unavailable"}
    item = next((entry for entry in running if entry.get("name") == model), {})
    return {
        "size_bytes": item.get("size"),
        "vram_bytes": item.get("size_vram"),
        "context_length": item.get("context_length"),
        "expires_at": item.get("expires_at"),
        "source": "ollama_api_ps_after_request",
        "scope": "Ollama-reported loaded model allocation; not host peak RSS",
    }


def document_for(repo, doc_id):
    matches = list((repo / "documents").glob(doc_id + ".*"))
    if len(matches) != 1:
        raise ValueError(f"expected one document for {doc_id}, found {len(matches)}")
    return matches[0]


def images_for(path, max_pages):
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        return [base64.b64encode(path.read_bytes()).decode("ascii")], "native_image"
    if suffix != ".pdf":
        raise ValueError(f"vision mode does not yet convert {suffix} files")
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise RuntimeError("pdftoppm is required to render PDF pages")
    with tempfile.TemporaryDirectory() as folder:
        prefix = Path(folder) / "page"
        command = [renderer, "-png", "-r", "144", "-f", "1", "-l", str(max_pages), str(path), str(prefix)]
        subprocess.run(command, check=True, capture_output=True)
        pages = sorted(Path(folder).glob("page-*.png"))
        if not pages:
            raise RuntimeError("PDF renderer produced no pages")
        return [base64.b64encode(page.read_bytes()).decode("ascii") for page in pages], "pdf_png_144dpi"


def text_for(path):
    suffix = path.suffix.lower()
    if suffix in {".txt", ".csv", ".xml", ".html"}:
        return path.read_text(encoding="utf-8", errors="replace"), "native_text"
    if suffix != ".pdf":
        raise ValueError(f"text mode does not yet convert {suffix} files")
    converter = shutil.which("pdftotext")
    if not converter:
        raise RuntimeError("pdftotext is required for PDF text mode")
    result = subprocess.run([converter, "-layout", str(path), "-"], check=True,
                            capture_output=True, text=True)
    return result.stdout, "pdftotext_layout"


def prompt_for(repo, doc_id):
    template_path = repo / "prompts" / "extraction_prompt.txt"
    template = template_path.read_text(encoding="utf-8").strip()
    prompt = template.format(doc_id=doc_id)
    guideline = repo / "guidelines" / f"{doc_id}.txt"
    if guideline.is_file():
        prompt += "\n\nAdditional schema instructions:\n" + guideline.read_text(encoding="utf-8").strip()
    return prompt + "\n\nReturn only one complete JSON object matching the supplied schema."


def run_model(repo, base_url, model, mode, doc_id, max_pages, identity):
    started = time.monotonic()
    document = document_for(repo, doc_id)
    schema = read_json(repo / "schemas" / f"{doc_id}.json")
    message = {"role": "user", "content": prompt_for(repo, doc_id)}
    if mode == "vision":
        message["images"], input_mode = images_for(document, max_pages)
    else:
        text, input_mode = text_for(document)
        message["content"] += "\n\nDOCUMENT CONTENT:\n" + text
    payload = {"model": model, "messages": [message], "stream": False,
               "format": schema, "options": {"temperature": 0, "num_predict": 8192}}
    prompt_hash = hashlib.sha256(message["content"].encode("utf-8")).hexdigest()
    response = {}
    content = ""
    try:
        response = api(base_url, "/api/chat", payload)
        content = response.get("message", {}).get("content", "")
        data = json.loads(content)
        status, error = "ok", None
    except Exception as exc:
        data, status, error = {}, "failed", {"type": exc.__class__.__name__, "message": str(exc)}
        response = {}
    meta = {
        "provider": "ollama", "model": identity, "doc_id": doc_id,
        "input_mode": input_mode, "source_file": document.name,
        "source_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
        "prompt_sha256": prompt_hash, "temperature": 0, "num_predict": 8192,
        "response_chars": len(content),
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest() if content else None,
        "ollama_runtime": runtime_identity(base_url, model) if response else None,
        "total_duration_ns": response.get("total_duration"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
        "eval_count": response.get("eval_count"),
        "eval_duration_ns": response.get("eval_duration"),
    }
    result = {"status": status, "data": data, "time_sec": round(time.monotonic() - started, 4), "meta": meta}
    if error:
        error["response_excerpt"] = content[:500]
        result["error"] = error
    return result


def score(repo, doc_id, result):
    # The standalone scorer consumes the extracted data object, while committed
    # submission files use an envelope containing data and metadata.
    with tempfile.TemporaryDirectory() as folder:
        raw = Path(folder) / "data.json"
        write_json(raw, result.get("data", {}))
        command = [sys.executable, str(repo / "scorer.py"), str(raw),
                   str(repo / "schemas" / f"{doc_id}.json"), str(repo / "labels" / f"{doc_id}.json")]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(completed.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", required=True, choices=["vision", "text"])
    parser.add_argument("--doc-id", action="append", required=True)
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--max-pages", type=int, default=4)
    parser.add_argument("--reuse-existing", action="store_true",
                        help="rescore existing result envelopes without calling Ollama")
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    identity = model_identity(args.ollama_url, args.model)
    outcomes = []
    for doc_id in args.doc_id:
        result_path = repo / "results" / args.engine / f"{doc_id}.json"
        if args.reuse_existing and result_path.is_file():
            result = read_json(result_path)
        else:
            result = run_model(repo, args.ollama_url, args.model, args.mode, doc_id, args.max_pages, identity)
            write_json(result_path, result)
        scored = score(repo, doc_id, result)
        outcomes.append({"doc_id": doc_id, "status": result["status"], "score": scored["final"],
                         "time_sec": result["time_sec"], "result": str(result_path.relative_to(repo))})
        print(json.dumps(outcomes[-1]), flush=True)
    aggregate = sum(item["score"] for item in outcomes) / len(outcomes)
    model_allocations = []
    for item in outcomes:
        result = read_json(repo / item["result"])
        runtime = result.get("meta", {}).get("ollama_runtime") or {}
        if runtime:
            model_allocations.append(runtime)
    summary = {"engine": args.engine, "model": identity, "mode": args.mode,
               "document_count": len(outcomes), "aggregate": aggregate, "documents": outcomes,
               "resources": {
                   "ollama_loaded_size_bytes": max((x.get("size_bytes") or 0 for x in model_allocations), default=None),
                   "ollama_vram_bytes": max((x.get("vram_bytes") or 0 for x in model_allocations), default=None),
                   "scope": "Ollama API model allocation; adapter process RSS is recorded separately by FieldKit"
               }}
    write_json(repo / "results" / f"{args.engine}-fieldkit-summary.json", summary)
    return 0 if all(item["status"] == "ok" for item in outcomes) else 2


if __name__ == "__main__":
    raise SystemExit(main())
