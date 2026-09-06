# AWS restricted-egress AI deployment reference case

Status: design proposal; no AWS environment has been created or evaluated yet.

## Decision statement

This reference case will test one bounded claim:

> A specified open-weight document-extraction workload ran on a named Amazon EC2
> instance with no public IP address and no internet or NAT route; during the
> evaluation window, its permitted network paths were limited to explicitly scoped
> AWS service endpoints, its model and software artifacts were identified by digest,
> and its benchmark and deployment evidence were preserved for later verification.

This is deliberately not called an AWS air-gap certification. AWS defines an
[isolated subnet](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html)
as one with no routes to destinations outside its VPC. A workload that reaches AWS
services through PrivateLink or an S3 gateway endpoint still has network paths and
should be described precisely. The result will apply only to the evaluated account,
Region, infrastructure revision, workload, and time window.

## Why this case

Enterprises increasingly run their own model weights on cloud infrastructure while
using terms such as private, sovereign, disconnected, or air-gapped. Those terms
describe different control objectives. This case demonstrates how RunWitness can
test a precise deployment claim without turning architecture intent or provider
documentation into runtime proof.

The first case prioritizes reproducibility and evidentiary depth over a complex
production topology. It uses one instance, one model, one independent benchmark
profile, and a deliberately small evidence surface.

## Reference workload

- **Workload:** document extraction using an open-weight model served locally on
  the evaluation instance.
- **Benchmark:** a fixed, named DocuBench subset, scored by DocuBench outside the
  RunWitness code boundary.
- **Model:** one model that fits a single 24 GiB accelerator; the exact repository,
  revision, files, license, and content digests must be frozen before provisioning.
- **Compute candidate:** `g5.xlarge` in `us-east-1`, subject to quota and current
  availability. AWS documents this family as suitable for ML inference and lists a
  single NVIDIA A10G GPU for `g5.xlarge`.
- **Orchestration:** a preinstalled system service launches the evaluation after an
  externally recorded isolation transition. No interactive shell is required during
  the evaluation window.
- **Output:** a RunWitness bundle plus separately exported AWS configuration and
  audit evidence.

The initial case will not compare clouds or models. A later controlled model study
must give every candidate the same documents, modality, prompt, serving stack, and
acceptance policy.

## Two-phase architecture

The design separates preparation from evaluation so that package installation and
model download do not occur inside the measured window.

### Phase A — controlled preparation

1. Build a pinned machine image containing the operating system, GPU driver,
   inference runtime, RunWitness, benchmark adapter, and test harness.
2. Import the model and benchmark inputs from a versioned, private S3 staging bucket.
3. Verify all expected artifact digests on the instance.
4. Write the immutable run plan and a delayed one-shot system service.
5. Capture the machine-image ID, EBS snapshot IDs, artifact inventory, IAM policies,
   endpoint policies, route tables, network ACLs, security groups, and instance
   metadata configuration.

Preparation may use private AWS service endpoints. It is outside the evaluation
claim and must be identified as such.

### Phase B — restricted-egress evaluation

1. Remove preparation-only endpoints and associate the evaluation route table and
   network controls.
2. Confirm that the instance has no public IPv4 address, no IPv6 address, no internet
   gateway route, no NAT route, no egress-only internet gateway, no transit-gateway
   route, no peering route, and no VPN or Direct Connect route in scope.
3. Permit only the private service paths explicitly required by the final design.
   The preferred strict variant permits no service endpoint during benchmark
   execution and writes results to encrypted EBS for later export.
4. Let the preinstalled one-shot service run connectivity probes, the benchmark,
   and RunWitness without an interactive control channel.
5. After the service has completed, capture a second infrastructure snapshot,
   restore the separately documented export path, and copy the evidence bundle to
   the evidence bucket.
6. Verify the bundle on a separate reviewer machine.

AWS documents that internet access requires an internet-gateway route and that
[PrivateLink can reach supported AWS services without an internet gateway or NAT](https://docs.aws.amazon.com/vpc/latest/privatelink/what-is-privatelink.html).
An [S3 gateway endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html)
also creates a private S3 path without an internet gateway or NAT. Every retained
endpoint therefore belongs in the evidence and limitation statement.

## Proposed AWS resources

| Resource | Purpose | Evidence to retain |
| --- | --- | --- |
| Dedicated VPC and evaluation subnet | Bound the experiment | IDs, CIDRs, DHCP/DNS settings, tags |
| Evaluation route table | Make reachable destinations explicit | All routes and association IDs before, during, and after the run |
| Network ACL and security group | Layered packet controls | Complete ingress/egress rules and attachment IDs |
| One `g5.xlarge` EC2 instance | Local model inference and benchmark | Instance identity, AMI, ENI, placement, state transitions |
| Encrypted gp3 EBS volume | Model, inputs, and local evidence staging | Volume, snapshot, KMS key, encryption and attachment metadata |
| Private S3 staging/evidence buckets | Controlled import and export | Bucket policy, public-access block, versioning, object digests |
| Customer-managed KMS key | Explicit key policy and encrypted storage | Key ARN, policy, state, rotation setting; never private key material |
| CloudTrail trail | Management-plane activity record | Trail configuration and relevant validated events |
| VPC Flow Logs | Network-flow observations | Configuration, delivery status, records, and skipped-record status |
| Optional interface endpoints | Preparation or export control plane | Endpoint IDs, policies, ENIs, DNS mode, and hourly lifetime |
| S3 gateway endpoint | Optional private artifact transfer | Endpoint policy and associated route tables |

Systems Manager may be used during preparation through private endpoints, following
the [AWS private-endpoint guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html).
It must not remain an undeclared control path in the strict evaluation window.

## Threat model

### In scope

- accidental or unauthorized public ingress to the evaluation instance;
- general internet egress from the workload subnet;
- an undeclared AWS service endpoint or route available during evaluation;
- use of a different model, image, benchmark profile, or policy than declared;
- post-run modification, deletion, or substitution of benchmark artifacts;
- acceptance of a run when a required observation is missing;
- confusion between preparation, evaluation, and evidence-export phases.

### Out of scope for the first public case

- malicious AWS control-plane or hypervisor operators;
- physical infrastructure inspection and national-jurisdiction guarantees;
- side channels, firmware compromise, and accelerator memory forensics;
- proof that every packet was observed;
- organizational processes outside the experiment account;
- legal or regulatory certification;
- provider-wide conclusions about AWS or any AWS service.

These exclusions are not assumed safe. They are recorded as untested.

## Acceptance gates

The run passes only if every required gate resolves to `pass`. Missing evidence
resolves to `unknown` or `invalid`, never to `pass`.

| Gate | Required evidence | Pass condition |
| --- | --- | --- |
| Artifact identity | Model, AMI, container/package, input, prompt, and policy digests | All equal the frozen run plan |
| Instance identity | Signed EC2 instance identity document | Signature verifies and fields match the declared instance |
| No public addressing | EC2 instance and ENI descriptions | No public IPv4 or IPv6 assignment |
| No public route | Route tables and associations | No IGW, NAT, egress-only IGW, TGW, peering, VPN, or DX path in scope |
| Declared private paths only | Endpoint inventory and policies | Exact match to the phase-specific allowlist |
| Packet-control posture | Security-group and NACL snapshots | Exact match to the frozen evaluation policy |
| Negative connectivity tests | Local probe output plus flow observations | All forbidden targets fail; expected local paths behave as declared |
| Benchmark completion | Native DocuBench result and exit state | Named profile completes successfully |
| Deployment thresholds | Versioned RunWitness policy | Every required quality, runtime, and resource gate passes |
| Artifact integrity | RunWitness verification on separate reviewer | Every recorded artifact hash verifies |
| Audit completeness | CloudTrail, flow-log, and collector status | Required sources delivered; gaps and skipped records are surfaced |
| Phase integrity | Timestamped control-plane events and local monotonic timeline | Preparation, evaluation, and export transitions are consistent |

AWS provides a signed instance identity document that can be
[verified with its regional public certificate](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/verify-iid.html).
That attests selected instance identity fields; it does not attest the entire guest
filesystem, network policy, or benchmark execution.

## Negative tests

At least these attempts should run before and after the benchmark:

- public IPv4 HTTPS destination;
- public IPv6 destination, if any IPv6 stack remains enabled;
- external DNS name through the configured resolver;
- an AWS public regional API hostname not backed by an allowed private endpoint;
- an S3 bucket and object outside the endpoint and bucket-policy allowlist;
- the expected local model endpoint;
- EC2 instance metadata through IMDSv2.

Failures are evidence only within the tested destination, protocol, time window, and
instrumentation scope. They do not prove that no other network path exists.

## Evidence bundle

The publishable case should contain:

- the RunWitness manifest, decision, report, verification summary, and native
  benchmark output;
- the frozen claim, threat model, policy profile, and run identifiers;
- signed EC2 instance identity document and offline verification result;
- sanitized JSON snapshots for EC2, VPC, IAM, KMS, S3, CloudTrail, and flow-log
  configuration;
- selected CloudTrail events covering infrastructure and policy transitions;
- VPC Flow Log records for the evaluation ENI and the log-delivery status;
- local process-tree, GPU, route, socket, DNS, and connectivity-probe observations;
- all relevant tool versions and artifact digests;
- an evidence index containing hashes for every retained file;
- a limitations statement listing unavailable evidence and excluded claims.

CloudTrail records AWS API activity and relevant request context. It does not prove
guest-runtime behavior. VPC Flow Logs add network observations, but AWS explicitly
documents that [they do not capture all IP traffic](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-limitations.html).
Both sources must therefore be combined with configuration snapshots and local
negative tests rather than treated as complete proofs alone.

## Implementation plan

### Milestone 1 — specification and fixtures

- Finalize the claim and strict versus private-endpoint variants.
- Add a versioned AWS evidence schema and sanitized fixtures.
- Implement offline evaluation of route, endpoint, address, security-group, NACL,
  public-access-block, encryption, and logging facts.
- Unit-test pass, fail, unknown, permission-denied, and stale-evidence cases.

### Milestone 2 — collector and infrastructure

- Implement an AWS collector using read-only SDK calls and caller-provided evidence.
- Add reproducible infrastructure as code with destructive teardown separated from
  normal apply operations.
- Add the preinstalled one-shot runner and local phase ledger.
- Add cost tags, a budget alarm, and automatic expiration metadata.

### Milestone 3 — dry runs

- Validate the workflow first on a CPU instance without a model workload.
- Exercise a deliberately failing route or endpoint-policy configuration.
- Verify that permissions denied to the collector become `unknown`, not `pass`.
- Rehearse evidence export and complete teardown.

### Milestone 4 — public GPU run

- Freeze every input and policy revision.
- Review the infrastructure plan and current cost estimate.
- Run once, preserve raw evidence privately, and build a sanitized publication set.
- Have a second reviewer reproduce integrity verification.
- Publish the architecture, evidence, results, limitations, and teardown receipt.

No cloud resource should be provisioned until Milestones 1–3 are complete and the
account owner explicitly approves the plan and maximum spend.

## Cost envelope

The design target is **USD 10–25 for one carefully rehearsed public run**, excluding
tax and any account-specific support or data-transfer charges. This is a budget,
not a quoted AWS price.

Planning assumptions for `us-east-1`:

- 2–6 total `g5.xlarge` instance-hours for final preparation and execution;
- 100 GiB gp3 EBS retained for less than one day, plus one short-lived snapshot;
- up to five interface endpoints retained for no more than six hours;
- one S3 gateway endpoint, which AWS currently documents as having no additional
  endpoint charge;
- less than 5 GiB of S3, log, and endpoint data processing;
- one customer-managed KMS key, deleted or scheduled for deletion after evidence
  handling is complete;
- modest CloudTrail, Flow Log, S3 request, and CloudWatch ingestion volume.

AWS bills interface endpoints per endpoint-hour per Availability Zone and per GB
processed; partial endpoint-hours count as full hours. Current rates must be checked
on the [AWS PrivateLink pricing page](https://aws.amazon.com/privatelink/pricing/)
immediately before provisioning. AWS lists customer-managed KMS keys at USD 1 per
month prorated hourly and documents gp3 storage as provisioned GB-month pricing.

The Terraform plan should expose estimated quantities, but the AWS Pricing
Calculator and service pricing pages remain the price authority. Stop conditions:

- do not launch if the selected instance on-demand price or quota differs materially
  from the reviewed plan;
- do not create a NAT gateway for this case;
- do not leave interface endpoints, EBS volumes, snapshots, public IPs, or log groups
  running beyond the planned retention window;
- stop and investigate if the forecast exceeds USD 25 before the public run.

## Teardown and retention

Teardown is part of the evidence, not housekeeping.

1. Verify the exported evidence bundle from a separate machine.
2. Retain only the explicitly approved sanitized publication set.
3. Terminate the EC2 instance and delete its non-retained volumes.
4. Delete interface and gateway endpoints, buckets, log groups, flow logs, roles,
   policies, security groups, NACLs, route tables, subnets, and VPC in dependency order.
5. Delete or schedule deletion of the customer-managed KMS key after its approved
   retention period.
6. Record resource-not-found or empty-inventory checks for every tagged resource.
7. Capture the final cost view when AWS billing data becomes available.

Destructive teardown must require a separate explicit approval and must target only
resources carrying the unique reference-case ID and expected account and Region.

## Publication package

The public output should be useful without becoming a provider endorsement:

- infrastructure source and exact revisions;
- architecture and threat-model diagram;
- evidence schema and sanitized bundle;
- benchmark results and deployment gate outcomes;
- negative-test observations;
- cost and teardown report;
- limitations and unresolved questions;
- independent reproduction instructions;
- a concise executive interpretation for `shivam.systems`.

Potential paid enterprise reports can reuse the public method while keeping customer
architecture, evidence, findings, and remediation confidential. Those reports should
state the assessed scope and avoid the terms certified or compliant unless an
appropriately authorized certification process exists.

## Open design decisions

1. Which open-weight model and serving runtime provide the most reproducible single-
   GPU case without model-license ambiguity?
2. Should the strict evaluation window remove all service endpoints, or retain a
   narrowly scoped evidence endpoint and describe the case as restricted egress?
3. Which configuration evidence should be collected independently from outside the
   workload account?
4. How should RunWitness bind delayed cloud log delivery to the local monotonic run
   timeline?
5. Which artifacts can be published without exposing account IDs, resource IDs,
   network structure, or reusable security details?

These decisions must be resolved in issues and fixtures before implementation.
