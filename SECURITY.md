# Security policy

## Supported versions

RunWitness is pre-1.0 software. Security fixes are applied to the latest tagged
minor release only.

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| 0.1.x | No |

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use the
[private vulnerability reporting form](https://github.com/shivamsngh/runwitness/security/advisories/new)
instead. Include the affected version, a minimal reproduction, impact, and any
suggested mitigation. Do not include customer data, proprietary models,
credentials, or production evidence bundles.

You should receive an acknowledgement within five business days. Confirmed issues
will be assessed for a coordinated fix and disclosure. Acknowledgement in release
notes is available when desired.

## Security boundaries

RunWitness records evidence about a declared scope; it is not a sandbox and does
not make an untrusted benchmark safe to execute. Benchmark commands and optional
collectors run with the permissions of their environment. Review benchmark code,
use a disposable least-privilege environment, and never expose production secrets
to an evaluation run.

An evidence bundle can show integrity and observations within its documented
boundary. It does not by itself prove benchmark correctness, host integrity,
network isolation, regulatory compliance, or the absence of compromise.
