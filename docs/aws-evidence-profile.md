# AWS evidence profile v0.1

This experimental profile evaluates sanitized, caller-supplied AWS evidence without
AWS credentials, SDK calls, network access, or infrastructure provisioning. It is
the first offline contract for the proposed
[AWS restricted-egress reference case](AWS-REFERENCE-CASE.md).

The JSON Schema is [`schemas/aws-evidence-v0.1.schema.json`](../schemas/aws-evidence-v0.1.schema.json).
Its identifier is `runwitness.aws-evidence/v0.1`; the policy evaluator identifies
itself as `runwitness.aws-policy/v0.1`. Changes that alter meaning require a new
version rather than silently changing these contracts.

## Evaluate a document

```bash
runwitness aws-evaluate examples/aws_evidence/pass.json
runwitness aws-evaluate examples/aws_evidence/fail-public-path.json --output decision.json
```

Exit code `0` means every control passed. Exit code `2` represents `fail`,
`unknown`, or `invalid`. Input and operational errors use exit code `1`.

## Evidence outcomes

- `pass`: every required observed fact satisfies the profile.
- `fail`: sufficient evidence demonstrates a policy violation.
- `unknown`: required evidence is missing, unavailable, permission-denied, or stale.
- `invalid`: the document, timestamps, or observed values cannot be interpreted.

Failure takes precedence over unknown, while invalid takes precedence over all
other outcomes. Every decision contains JSON Pointer-style evidence references.
Missing evidence and denied permissions never become a pass.

## Current control set

The evaluator checks public IPv4/IPv6 addressing; forbidden active route target
types; exact endpoint allowlists; closed security-group and network-ACL egress;
storage encryption and customer-managed key use; CloudTrail and VPC Flow Log
delivery; skipped flow records; artifact digests; and evidence freshness relative
to the declared evaluation window.

The fixtures are deliberately synthetic and use `sanitized:` references. They
contain no AWS account IDs, ARNs, credentials, live network identifiers, or
customer data.

## Evidence boundary

This evaluator trusts the supplied document as input. It does not authenticate the
collector, query AWS, prove that the evidence set is complete, observe guest
traffic, or certify an air gap. Configuration, logs, negative probes, and runtime
observations need to be combined in a future executed reference case. The output
applies only to the declared scope and evaluation window.
