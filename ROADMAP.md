# RunWitness roadmap

RunWitness is being built toward an independent deployment-evidence layer for AI
systems: from a laptop running local weights to sovereign, disconnected, and
regulated enterprise environments.

The long-term goal is not another model leaderboard. It is a portable way to test
a deployment claim, preserve the evidence behind it, expose what was not proven,
and produce a reviewable acceptance record around any benchmark.

This roadmap communicates direction, not guarantees. A capability is available
only when it appears in a tagged release and its evidence boundary is documented.
RunWitness is not a certification body, and provider names do not imply
affiliation, endorsement, or validation by those providers.

## The evidence model

Every RunWitness profile should keep four states separate:

1. **Declared** — the architecture, policy, and controls the operator says exist.
2. **Enforced** — restrictions actively applied during the evaluated run.
3. **Observed** — facts captured by instruments within a stated scope.
4. **Unavailable** — properties the evidence cannot establish.

This distinction is central to future cloud work. A private endpoint, disabled
public access, a provider policy, or a diagram labelled “air-gapped” is not by
itself proof that a workload was isolated. Evidence must connect documented intent,
deployed configuration, runtime observation, and independently verifiable artifacts.

## v0.3 — Portable evidence contracts

The next milestone makes evidence stable enough for other tools and environments
to produce and consume.

- Publish versioned JSON Schemas for manifests, decisions, and collector evidence.
- Add a plugin interface for external evidence collectors without coupling them to
  the benchmark adapter.
- Export compact machine-readable verification summaries for CI and policy tools.
- Define compatibility and migration rules for evidence bundles.
- Produce a controlled document-extraction comparison in which models receive the
  same documents through the same input modality.
- Add reference examples for signed metadata and external artifact references.

## v0.4 — Attestation and offline review

- Sign evidence bundles and verify signatures without a RunWitness service.
- Record tool, model, container, and configuration identities through content
  digests rather than mutable names alone.
- Reference SBOMs, container provenance, and software supply-chain attestations.
- Generate a portable reviewer pack containing the claim, evidence, limitations,
  integrity status, and decision rationale.
- Introduce policy profiles that can be versioned, compared, and reviewed without
  silently changing acceptance thresholds.

## v0.5 — Infrastructure evidence collectors

- Observe network attempts separately from network-isolation enforcement.
- Add GPU and accelerator telemetry with vendor-specific scope declarations.
- Add Kubernetes evidence for workload identity, images, policies, nodes, storage,
  services, and relevant admission decisions.
- Add private-cloud and on-premises collectors for hosts, clusters, and inference
  services.
- Support external evidence gathered from infrastructure-as-code plans, cloud
  configuration APIs, audit logs, and policy engines.
- Preserve unavailable and permission-denied observations instead of converting
  them into passing results.

## Cloud deployment assurance program

RunWitness will develop cloud-specific evidence profiles for enterprises that run
their own AI weights on infrastructure they control. Candidate environments include
Amazon Web Services, Oracle Cloud Infrastructure, Microsoft Azure, Google Cloud,
and compatible sovereign or dedicated-cloud offerings.

Each provider profile is expected to evaluate a common claim set while respecting
provider-specific control semantics:

- model artifact identity, origin, license, and integrity;
- compute, accelerator, container, and orchestration identity;
- ingress, egress, DNS, endpoint, routing, and tenancy boundaries;
- storage encryption, key ownership, secret handling, and artifact retention;
- identity, role, policy, and administrative access paths;
- telemetry destinations and operational dependencies;
- software update, image import, and offline transfer procedures;
- evidence of runtime enforcement, not only configured intent;
- residual risks, unobserved paths, and controls that require manual review.

“Air-gapped,” “disconnected,” “sovereign,” “private,” and “dedicated” will not be
treated as interchangeable labels. Every profile must define the claim being tested,
the applicable threat model, the services in scope, the evidence sources used, and
the conditions under which the result is unknown or fails.

### Public reference cases

The program will begin with one narrow, reproducible public reference case on one
cloud provider. It will include:

- a documented architecture and threat model;
- infrastructure and RunWitness policy definitions that can be reviewed publicly;
- an open-weight AI workload and an independent benchmark;
- sanitized evidence artifacts with integrity verification;
- a control-by-control account of what was declared, enforced, observed, and not
  established;
- costs, operational constraints, and reproducibility limitations;
- an explicit statement that the result applies to the evaluated configuration,
  not to an entire provider or product family.

Additional providers and architectures can follow as evidence collection becomes
repeatable. Public cases will favor depth and reproducibility over broad checklists.
The initial proposal is the
[AWS restricted-egress AI deployment reference case](docs/AWS-REFERENCE-CASE.md).

### Enterprise assessment reports

RunWitness can also support paid, environment-specific assessments for enterprises
deploying their own model weights. These reports are intended to apply the public
methodology to a defined customer system and may include:

- deployment-claim and threat-model definition;
- benchmark and acceptance-policy design;
- evidence-source mapping and collection planning;
- execution of approved evaluation runs;
- configuration and runtime evidence analysis;
- gaps, unknowns, compensating controls, and prioritized remediation;
- a signed or integrity-verifiable evidence pack where supported;
- an executive decision brief and a technical reviewer report.

Customer configurations, results, and evidence remain private unless the customer
explicitly authorizes publication. A paid report is an evidence-based technical
assessment of a stated scope; it is not a legal, regulatory, or provider-wide
certification. The open-source engine and public evidence contracts remain distinct
from private customer findings and advisory work.

## Research questions

Several hard problems require investigation rather than premature claims:

- How can a disconnected environment demonstrate isolation without depending on a
  connected verification service?
- Which cloud control-plane facts can be preserved for later offline verification?
- How should absence-of-egress evidence be expressed when observation is incomplete?
- How can evidence survive provider API, policy, and service-version changes?
- Which measurements are comparable across accelerators and serving stacks?
- How should human approvals and manual controls enter a machine-verifiable record?
- What minimum evidence should an enterprise require before accepting a privately
  deployed model for a consequential workflow?

## Open-source and commercial boundary

The project intends to keep these foundations open:

- evidence schemas and verification semantics;
- the benchmark adapter and collector interfaces;
- local and community-maintained collectors;
- reproducible public reference cases;
- integrity verification and offline review primitives.

Commercial work may include private deployment profiles, customer-specific evidence
collection, assessment execution, confidential findings, remediation guidance, and
ongoing assurance programs. Commercial reports must not claim stronger assurance
than the underlying open evidence model supports.

## Non-goals

RunWitness will not:

- vendor or redefine third-party benchmark datasets and scoring logic;
- treat configuration declarations or provider marketing language as runtime proof;
- claim whole-machine, GPU, network, or control-plane visibility when the available
  instrumentation is narrower;
- describe a provider, service, or organization as certified based on one workload;
- require a hosted RunWitness control plane to run or verify a benchmark;
- publish customer evidence, identifiers, architecture, or results without explicit
  authorization.

## How to participate

Feature and provider-profile proposals are welcome as GitHub issues. A useful
proposal describes:

1. the exact deployment claim and threat model;
2. the workload, benchmark, and infrastructure in scope;
3. the evidence sources and permissions required;
4. what can be enforced, observed, inferred, and not established;
5. how an independent or offline reviewer could verify the result.

The roadmap will evolve through public evidence, not feature-count ambition.
