# RunWitness roadmap

This roadmap communicates direction, not guarantees. A capability is available
only when it appears in a tagged release and its evidence boundary is documented.

## v0.3 — Portable evidence contracts

The next milestone focuses on making evidence easier to consume and extend across
tools and environments.

- Publish a versioned JSON Schema for manifests, decisions, and collector evidence.
- Add a plugin interface for external evidence collectors without coupling them to
  the benchmark adapter.
- Produce a controlled document-extraction comparison in which models receive the
  same documents through the same input modality.
- Export a compact, machine-readable verification summary for CI and policy tools.
- Document a stable compatibility policy for evidence bundles.

## Assurance track

These items require explicit threat models and may land over several releases:

- Signed evidence bundles with offline signature verification.
- Network-attempt observation distinct from network-isolation enforcement.
- GPU and accelerator telemetry with vendor and platform-specific scope.
- Kubernetes and private-cloud collectors.
- Reproducible environment and artifact provenance, including SBOM references.

## Non-goals

RunWitness will not:

- vendor or redefine third-party benchmark datasets and scoring logic;
- treat configuration declarations as proof of runtime properties;
- claim whole-machine, GPU, or network visibility when instrumentation is scoped
  to a process tree or local service;
- become a hosted control plane required to run or verify a benchmark.

Feature proposals are welcome as GitHub issues. Please describe the deployment
claim being evaluated, the evidence source, its observation boundary, and how an
offline reviewer could verify it.
