# Changelog

## 0.1.0 — 2026-09-06

- Added benchmark-agnostic command execution and JSON metric mapping.
- Added evidence manifests, integrity hashes, deployment gates, and HTML reports.
- Added explicit benchmark virtual-environment support.
- Added external DocuBench adapters for local Ollama vision and text models.
- Added a named eight-document DocuBench starter smoke profile.
- Added Ollama model identity, digest, inference metrics, and model-allocation evidence.
- Added mocked adapter tests that require neither Ollama nor DocuBench.

FieldKit does not vendor DocuBench code or data. Example gates are integration
examples and are not recommended production policies.
