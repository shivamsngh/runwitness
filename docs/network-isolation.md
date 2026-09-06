# Linux network isolation (v0.2 preview)

RunWitness can ask the Rust collector to launch a benchmark in a new Linux network namespace. A newly created namespace has no inherited physical or virtual network devices, routes, firewall rules, or listening ports. RunWitness treats the namespace as enforced only after the Linux `unshare(CLONE_NEWNET)` operation succeeds.

```json
"deployment": {
  "network": {"mode": "deny"},
  "collector": {
    "command": ["./collector/target/release/runwitness-collector"],
    "sample_interval_ms": 100
  }
}
```

If the host is not Linux, network namespaces are disabled in the kernel, or the process lacks the required capability, the collector fails closed and the benchmark does not run. The evidence records `enforced: false`; it never upgrades the requested policy into a claim.

## What this proves

Successful evidence proves that the benchmark process started after entering a new Linux network namespace. It does not prove physical air-gapping, inspect the host outside that namespace, or identify every attempted connection. Attempt observation is recorded as `unavailable` in this preview.

Linux ordinarily requires `CAP_SYS_ADMIN` for `CLONE_NEWNET`. Run RunWitness through an appropriately constrained container or service account; do not grant broader host privileges solely for convenience.

The continuous-integration release gate exercises the successful Linux path inside an ephemeral privileged test container where namespace creation is intentionally permitted. It first confirms that the parent namespace reports an `eth0` interface through `/proc/net/dev`, then confirms the benchmark cannot see that interface after RunWitness creates the new namespace, and validates the resulting enforcement fields. This is an implementation regression test, not product guidance and not proof about a user's deployment environment.

The kernel behavior and privilege requirement are documented in [`unshare(2)`](https://man7.org/linux/man-pages/man2/unshare.2.html) and [`network_namespaces(7)`](https://man7.org/linux/man-pages/man7/network_namespaces.7.html).
