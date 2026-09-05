# Ollama + Phi + DocuBench

This integration has three independent layers:

1. **Ollama/model runner** reads each document and schema, calls the selected
   local model, and writes one native result envelope per document.
2. **DocuBench** validates and scores those result envelopes against its labels
   using its own scorer.
3. **FieldKit** invokes that workflow, preserves the native results, records
   deployment evidence, and evaluates deployment gates.

FieldKit does not copy or modify DocuBench code, data, labels, or scoring.

## Important model constraint

Ollama's `phi` tag is Phi-2: a text-only model with a 2K context window. It
cannot directly inspect DocuBench's PDFs and images. To test it fairly, the
runner must first extract text and tables with a declared parser/OCR pipeline,
then send that content and the paired JSON Schema to Phi. The report must name
both the extraction pipeline and the model, because the score measures the
combined system.

A vision-capable Ollama model can instead receive rendered document pages, but
non-image formats still need deterministic conversion. Do not compare a
text-only Phi pipeline with a vision system as though only the language models
differed.

On the initial local validation machine, `ministral-3:latest` is vision-capable
and `phi3.5:latest` is text-only. FieldKit therefore includes two adapters:

- `examples/docubench/fieldkit.json` — Ministral-3 vision subset;
- `examples/docubench/fieldkit-phi35.json` — Phi 3.5 native-text subset.

`examples/docubench/starter-suite.json` names eight documents selected from the
unchanged 72-document DocuBench corpus. It covers a photographed receipt, a PDF
table, handwriting, Hebrew RTL, a rotated PNG, EDI text, XML, and HTML. This is
a fast integration profile; published comparisons must use the complete corpus
or clearly state that they are subset results.

## Environment setup

Keep FieldKit and DocuBench in separate environments:

```bash
cd /Users/shivam.singh/Documents/FieldKit
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .

git clone https://github.com/DocuPipe/DocuBench.git ../DocuBench
cd ../DocuBench
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
docubench validate
```

Confirm the local service and model separately:

```bash
ollama serve
ollama pull ministral-3
ollama pull phi3.5
ollama run ministral-3 "Return only JSON: {\"ready\": true}"
```

## Runner contract

DocuBench does not currently ship an Ollama runner. The integration therefore
needs a small external runner—not code inside FieldKit—that:

- iterates over `documents/` and loads the matching `schemas/<doc_id>.json`;
- converts each source into model-readable text or ordered page images;
- calls `http://localhost:11434/api/chat` with `stream: false`, the model tag,
  and the DocuBench schema in Ollama's structured-output `format` field;
- writes `results/<engine>/<doc_id>.json` with `data` and `meta` fields;
- writes failures with `status: "failed"` and `data: {}` rather than omitting
  them;
- records model tag/digest, Ollama version, conversion/OCR identity, prompt
  hash, generation settings, latency, and token counts in `meta`.

For example, use an engine name that describes the whole system:
`ollama-phi2-pymupdf-tesseract-v1`, not merely `phi`.

After the runner has produced all outputs, DocuBench remains authoritative:

```bash
docubench validate
docubench score --engine ollama-phi2-pymupdf-tesseract-v1
docubench report
```

## FieldKit adapter

The FieldKit adapter should execute one orchestration script that runs the
external model runner followed by DocuBench validation, scoring, and reporting.
It should preserve:

- `results/<engine>/` as native per-document outputs;
- `results/summary.json` and `results/summary.csv` as DocuBench outputs;
- the runner's own execution metadata.

It can then map DocuBench's actual aggregate field from `results/summary.json`
to `quality.aggregate`, alongside gates such as runtime, memory, result
completeness, and isolation evidence. The final metric path must be confirmed
against the installed DocuBench version instead of being assumed.

Run the supplied adapters after exporting both checkout paths:

```bash
export FIELDKIT_HOME=/Users/shivam.singh/Documents/FieldKit
export DOCUBENCH_HOME=/Users/shivam.singh/Documents/DocuBench

cd "$FIELDKIT_HOME"
source .venv/bin/activate
python3 -m fieldkit run examples/docubench/fieldkit.json --output runs/ministral-subset
python3 -m fieldkit run examples/docubench/fieldkit-phi35.json --output runs/phi35-subset
```

Each output directory is immutable per run; choose a new output name when
repeating an evaluation.

## Resource evidence scope

FieldKit's generic runner measures its root adapter process. Ollama is a
separately running service, so the adapter also queries Ollama after inference
and records its reported loaded model size and VRAM allocation. The two scopes
remain separate. Neither is described as whole-machine peak memory; a system
collector for that stronger claim remains on the roadmap.

## What a passing run means

A pass means the complete declared system—document conversion, Ollama, the
selected model, prompt, and generation settings—met both DocuBench quality and
FieldKit deployment gates. It does not prove an air gap unless isolation was
independently enforced and observed during that run.
