# Changelog

## Unreleased

- Add the experimental `runwitness.aws-evidence/v0.1` JSON Schema and offline
  `runwitness aws-evaluate` policy evaluator.
- Add sanitized pass, fail, unavailable, permission-denied, and stale AWS evidence
  fixtures with traceable four-state decisions.
- Add an import-only AWS collector for saved CLI/SDK responses, with path
  containment, raw-source preservation, source hashes, and no AWS dependency.
- Add a three-phase, disposable AWS L40S Terraform reference environment with
  account guards, frozen inputs, restricted transfer paths, runtime isolation,
  evidence logging, a compute watchdog, and protected teardown semantics.

## 0.2.1 — 2026-09-06

- Add reproducible Ministral-3 vision and Phi 3.5 text DocuBench case-study manifests and an evidence-bounded report.
- Fix `runwitness verify` for valid bundles that omit the optional Rust collector.

## 0.2.0 — 2026-09-06

- Rename FieldKit to **RunWitness** across the repository, Python package, CLI,
  Rust collector, configuration examples, and documentation. The original
  `v0.1.0` release was published under the FieldKit name.
- Reserve canonical distribution identities in project metadata and add CI plus
  tokenless PyPI trusted-publishing automation for the v0.2 release.
- Add an optional Rust descendant-process collector that records process-tree peak RSS, peak process count, and explicit evidence boundaries.
- Add Python orchestration and gate metrics for collector-produced `evidence/system.json`.
- Add fail-closed Linux network namespace isolation with separate requested, enforced, and attempt-observation evidence.
- Exercise the successful Linux namespace path in CI and validate the emitted isolation evidence before release.
- Added evidence-bundle integrity verification with `runwitness verify`.
- Added metric comparison with `runwitness compare`, including comparability warnings.
- Added a project icon, architecture visual, and evidence-backed benchmark graphic.
- Reworked the README around the benchmark-boundary and deployment-evidence proposition.

## 0.1.0 — 2026-09-06 (released as FieldKit)

- Added benchmark-agnostic command execution and JSON metric mapping.
- Added evidence manifests, integrity hashes, deployment gates, and HTML reports.
- Added explicit benchmark virtual-environment support.
- Added external DocuBench adapters for local Ollama vision and text models.
- Added a named eight-document DocuBench starter smoke profile.
- Added Ollama model identity, digest, inference metrics, and model-allocation evidence.
- Added mocked adapter tests that require neither Ollama nor DocuBench.

RunWitness does not vendor DocuBench code or data. Example gates are integration
examples and are not recommended production policies.
