# Import saved AWS evidence offline

`runwitness aws-import` converts saved AWS CLI or SDK responses into the versioned
AWS evidence profile. The command performs no network calls, imports no AWS SDK,
and reads no ambient AWS credentials.

```bash
runwitness aws-import \
  examples/aws_import/pass/capture.json \
  --output runs/aws-import-001

runwitness aws-evaluate runs/aws-import-001/evidence.json
runwitness aws-import-verify runs/aws-import-001
```

The output contains `capture.json`, `evidence.json`, `decision.json`,
`source-manifest.json`, and a `raw/` directory. The source manifest records a
SHA-256 digest for the preserved capture
manifest and every copied input. Existing outputs are never overwritten. Input
paths must remain inside the capture directory, and a failed import removes its
new partial directory.

## Capture contract

The capture manifest uses `runwitness.aws-import/v0.1`, documented by
[`schemas/aws-import-v0.1.schema.json`](../schemas/aws-import-v0.1.schema.json).
Each input is either `observed`, with a relative path and capture timestamp;
`permission_denied`; or `unavailable`. Missing or inaccessible required inputs
become `unknown`, never `pass`.

The importer understands saved response shapes for EC2 instances, route tables,
VPC endpoints, security groups, network ACLs, EBS volumes, and S3 public-access
blocking. Artifact digests use a small RunWitness input document.

Audit configuration does not prove log delivery. The importer therefore does not
derive a successful audit result from `describe-trails` or `describe-flow-logs`.
It requires a separate `logging_observation` document describing whether relevant
CloudTrail events and VPC Flow Log records arrived and whether skipped records were
reported. This document is preserved and hashed, but not authenticated.

## Sanitization and evidence boundary

Committed examples use synthetic `sanitized:` identifiers and contain no account
IDs, ARNs, addresses, credentials, or customer data. Private assessments may use
real identifiers locally; they require a separate sanitization step before
publication.

This is an import adapter, not a live AWS collector. It does not establish who
captured a response, whether the caller had complete visibility, or whether a file
was altered before import. Source hashes protect later review of the imported copy;
signed capture provenance is planned separately.
