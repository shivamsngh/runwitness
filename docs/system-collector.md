# System collector (v0.2 preview)

The optional Rust collector launches a benchmark and samples its root process and descendants. It adds a stronger resource scope than the Python runner's root-process estimate without changing the benchmark itself.

Build it:

```console
cargo build --release --manifest-path collector/Cargo.toml
```

Configure it under `deployment`:

```json
"collector": {
  "command": ["./collector/target/release/runwitness-collector"],
  "sample_interval_ms": 100
}
```

Collector paths containing `/` are resolved relative to the RunWitness config file.
After building, try the complete fixture:

```console
python3 -m runwitness run examples/fixture_benchmark/runwitness-collector.json --output runs/collector-fixture
python3 -m runwitness verify runs/collector-fixture
```

The evidence bundle then includes `evidence/system.json` and the metrics `resources.process_tree_peak_rss_mb` and `resources.process_tree_peak_count`.

## Evidence boundary

The collector observes only processes that are descendants of the benchmark command at sampling time. It does not include pre-existing services such as Ollama, prove an air gap, inspect network attempts, measure GPU memory, or guarantee observation of processes shorter than the sampling interval. Adapter-native evidence remains necessary for external runtimes.
