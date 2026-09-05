# FieldKit

FieldKit turns an independent AI benchmark run into a deployment evidence bundle.
It does **not** replace, fork, or redefine the benchmark. The benchmark owns its
datasets, execution, native outputs, and scoring. FieldKit adds the operational
context needed to answer a different question: *did this model and system satisfy
the declared requirements of this deployment?*

## Why it exists

A quality score alone is not a production decision. Regulated, sovereign, and
air-gapped deployments also need evidence about runtime, resources, isolation,
provenance, and explicit acceptance gates. FieldKit keeps those concerns outside
the benchmark while packaging them into one reviewable run record.

## Current status

This is a private v0.1 prototype. It provides:

- a benchmark-agnostic command adapter;
- JSON metric mapping from native benchmark results;
- runtime, root-process memory, host, disk-delta, and isolation evidence;
- `pass`, `fail`, `unknown`, and `invalid` gate decisions;
- SHA-256 integrity records and a self-contained HTML report;
- a runnable fixture and a DocuBench integration template.

FieldKit does not presently inspect child-process memory, observe every network
attempt, sign attestations, or prove that a declared air gap exists. Its evidence
states those limits rather than converting an unverified declaration into a claim.

## Quick start

Requires Python 3.9 or newer and no runtime dependencies.

```bash
python3 -m pip install -e .
fieldkit validate examples/fixture_benchmark/fieldkit.json
fieldkit run examples/fixture_benchmark/fieldkit.json --output runs/fixture-001
```

Open `runs/fixture-001/report.html`. The bundle also contains the benchmark's
native result, stdout/stderr, evidence records, `manifest.json`, and
`decision.json`.

## Adapter contract

An adapter declares an argv command, its external working directory, native
result files, and explicit JSON paths for metrics. Commands are executed without
a shell. Result paths must remain inside the benchmark working directory.

See [`docs/adapter-contract.md`](docs/adapter-contract.md) and the runnable
[`examples/fixture_benchmark/fieldkit.json`](examples/fixture_benchmark/fieldkit.json).

## DocuBench boundary

The example under `examples/docubench` is configuration only. It expects a
separate DocuBench checkout and deliberately includes none of DocuBench's source,
datasets, labels, schemas, or scoring logic. The exact command, result filename,
and metric path must be aligned to the version installed by the operator.

FieldKit is not affiliated with DocuPipe or DocuBench.

## License

FieldKit is MIT licensed. External benchmarks and their data retain their own
licenses and terms.
