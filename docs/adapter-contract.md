# Adapter contract (schema 0.1)

RunWitness accepts a JSON document with `benchmark` and `deployment` sections.

The benchmark section declares:

- `name` and optional `version`;
- `workdir`, relative to the configuration file or supplied through an
  environment variable;
- optional `venv`, resolved relative to `workdir`; it replaces a leading
  `python` or `python3` command with that environment's interpreter;
- optional `validate` and required `run` argv arrays;
- `native_results`, copied unchanged into the evidence bundle;
- `metrics`, mapping RunWitness metric names to a native JSON file and dot path.

The deployment section declares:

- a deployment `name` and timeout;
- network intent, which is recorded but not treated as proof;
- optional `execution.command_prefix` and `execution.mechanism` for an external
  isolation wrapper controlled by the operator;
- acceptance `gates` using `==`, `!=`, `>`, `>=`, `<`, `<=`, or `exists`.

Missing metrics yield `unknown`. A failed or timed-out benchmark yields `invalid`.
A completed run fails if any known gate fails, is unknown if no gate fails but a
metric is missing, and passes only when every gate passes.

## Isolation semantics

`network.mode` is a declaration. RunWitness v0.1 marks `isolation.enforced` true
only when the operator supplies a command prefix, and records that mechanism.
This means the wrapper was configured, not that RunWitness observed zero outbound
attempts. A future collector can add OS-specific enforcement and network-event
evidence without changing the benchmark adapter.
