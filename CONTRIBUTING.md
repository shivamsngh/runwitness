# Contributing to RunWitness

RunWitness is an early-stage project for preserving deployment evidence around
independent AI benchmarks. Contributions should strengthen the accuracy,
portability, or auditability of that evidence without absorbing a benchmark's
datasets, scoring logic, or identity.

## Before opening a change

- Search existing issues and discussions for related work.
- For a new evidence source, gate type, or manifest field, open an issue first.
- Keep claims within the evidence actually collected. A declaration is not an
  observation, and an observation is not necessarily an enforced control.
- Do not commit proprietary models, benchmark datasets, credentials, customer
  data, machine identifiers, or generated run bundles.

## Local setup

```bash
git clone https://github.com/shivamsngh/runwitness.git
cd runwitness
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

The optional Rust collector can be checked independently:

```bash
cargo fmt --manifest-path collector/Cargo.toml -- --check
cargo clippy --manifest-path collector/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path collector/Cargo.toml
```

## A useful pull request

1. Solves one focused problem and links its issue.
2. Includes tests for new or changed behavior.
3. Updates documentation when a contract, command, or evidence boundary changes.
4. Preserves backward readability of existing evidence bundles where practical.
5. States what the change observes, enforces, infers, and cannot establish.

Run the Python suite and relevant Rust checks before submitting. Pull requests
are reviewed for correctness, evidence semantics, security implications, and
whether the change keeps RunWitness benchmark-agnostic.

## Good first contributions

Issues labelled [`good first issue`](https://github.com/shivamsngh/runwitness/labels/good%20first%20issue)
are intentionally bounded. A maintainer can clarify the evidence contract before
implementation begins.

By contributing, you agree that your contribution is licensed under the project's
[MIT License](LICENSE).
