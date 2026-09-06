# Changelog

## Unreleased

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
