# AWS L40S reference-case Terraform

This directory defines one disposable, bounded RunWitness experiment. It has not
been applied by the project and creates no resources until an account owner reviews
and runs `terraform apply`.

The default instance type is `g6e.xlarge` with one NVIDIA L40S GPU. The AMI is an
explicit input because an unreviewed “latest” image would weaken artifact identity.
Use a reviewed x86_64 GPU AMI containing an L40S-compatible NVIDIA driver, AWS CLI,
`curl`, `tar`, and `sha256sum`.

## Safety properties

- `expected_account_id` fails the plan if credentials target another account.
- Every resource carries a unique case and expiry tag.
- There is no internet gateway, NAT gateway, public address, SSH, or inbound rule.
- Preparation/export can reach only the case S3 bucket through a gateway endpoint.
- Evaluation removes the S3 endpoint and all security-group/NACL egress rules.
- The phase tag changes only after the corresponding network controls converge.
- IMDSv2 is required and its hop limit is one.
- Inputs are accepted only when their frozen SHA-256 values match.
- A guest watchdog stops the instance after `max_instance_minutes`.
- Root storage is encrypted with a case-specific customer-managed KMS key and is
  marked for deletion with the instance.
- The evidence bucket blocks public access, enables versioning and encryption, and
  refuses Terraform deletion while it contains evidence (`force_destroy = false`).
- CloudTrail log-file validation and one-minute ENI Flow Logs are enabled.

The broad NACL rules in preparation/export do not represent isolation; they permit
return traffic for the S3 transfer. The evaluation phase removes them completely.

## Three reviewed applies

1. Copy `terraform.tfvars.example` outside version control as `terraform.tfvars`.
2. Set the exact account, expiry, reviewed AMI and artifact hashes.
3. Apply with `launch_instance = false`, then upload the runner and model to the
   output bucket.
4. Set `launch_instance = true`, keep `phase = "preparation"`, review the plan and
   apply. Wait for `evidence/<case>/status/ready.json`.
5. Set `phase = "evaluation"`, review the removal of the endpoint and egress rules,
   then apply. The guest observes the phase only after those controls converge.
6. After the benchmark finishes, set `phase = "export"`, review restoration of the
   bounded S3 path, and apply. The guest uploads evidence and stops.
7. Download and verify all evidence, CloudTrail logs, Flow Logs, Terraform plans
   and state-derived configuration snapshots.
8. Empty the evidence bucket only after local verification, then run a separately
   approved `terraform destroy`. Verify tagged-resource absence and record the KMS
   key’s scheduled-deletion state.

Do not skip directly from preparation to export. Terraform cannot prove that an
operator followed the lifecycle merely because the final state looks correct;
retain every reviewed plan, apply output, timestamp and CloudTrail transition.

## Runner archive contract

The archive must expand to `/opt/runwitness/run.sh`. The script receives two
arguments: the frozen model path and an initially empty evidence directory. It must
write all benchmark and RunWitness outputs beneath that directory and must not
attempt package installation or model download.

## Cost controls

The target GPU window is 20–30 minutes. Set account-level budget alerts before the
first apply. This configuration intentionally contains no NAT gateway or paid
interface endpoint. The S3 gateway endpoint has no endpoint-hour charge. The bucket,
logs, EBS and prorated KMS key should add only small amounts at this scale, but the
account’s pricing page and plan-time estimate remain authoritative.

The watchdog stops compute; it does not destroy infrastructure. Only a human-reviewed
destroy should remove the uniquely tagged case after evidence is safely downloaded.
