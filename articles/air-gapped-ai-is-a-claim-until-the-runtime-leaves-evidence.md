# Air-gapped AI is a claim until the runtime leaves evidence

*Draft for shivam.systems and LinkedIn. The AWS reference case described here is a design proposal; no AWS environment has yet been evaluated.*

Enterprise AI conversations often begin with a reassuring sentence: the model will run in a private, sovereign, or air-gapped environment.

That sentence may describe a serious architecture. It is not, by itself, evidence that the architecture existed during a particular inference run.

The useful question is more precise:

> What can an independent reviewer verify about the model, system, network boundary, and acceptance decision for this run?

That shift—from labels to evidence—is the idea behind RunWitness.

## Four states that should never be collapsed

An assurance report should keep four kinds of statement separate:

1. **Declared:** what the architecture, policy, or operator says should be true.
2. **Enforced:** what controls were actively applied during the run.
3. **Observed:** what the available instruments actually recorded.
4. **Unavailable:** what could not be established with the evidence and permissions available.

A subnet diagram is declared intent. A route table is configuration evidence. A failed probe is an observation for a particular destination, protocol, and time. None of them alone proves the absence of every possible network path.

This distinction matters because words such as *private*, *isolated*, *sovereign*, *disconnected*, and *air-gapped* are not interchangeable. They can refer to different threat models, administrative boundaries, dependencies, and legal requirements.

## A benchmark answers only part of the deployment question

Independent benchmarks should continue to own their datasets, execution, and scoring. For document extraction, for example, DocuBench can assess whether a model produced the expected structured result.

An enterprise deployment decision needs additional evidence:

- Which model artifacts and revisions ran?
- Which infrastructure and serving stack were used?
- Which network paths were available during the evaluation window?
- Were the benchmark results preserved unchanged?
- Which resource, latency, and quality thresholds were applied?
- Which facts could not be observed?

RunWitness is designed as an additive layer around the benchmark. It records operational context, hashes native results, evaluates explicit gates, and leaves the benchmark boundary intact.

## The first cloud reference case: a bounded AWS claim

The proposed public case uses one open-weight document-extraction workload on a named Amazon EC2 instance. The instance has no public address and no internet or NAT route. Preparation, evaluation, and evidence export are separate phases.

The intended claim is deliberately narrower than “AWS is air-gapped.” It applies only to a specified account, Region, infrastructure revision, workload, and evaluation window.

The case will retain multiple forms of evidence:

- model, image, input, prompt, package, and policy digests;
- EC2, VPC, route, endpoint, security-group, and network-ACL snapshots;
- a signed EC2 instance identity document;
- CloudTrail management-plane events;
- VPC Flow Logs, including delivery and skipped-record status;
- local process, route, socket, DNS, GPU, and connectivity observations;
- native benchmark output and RunWitness decisions;
- an integrity index for the complete reviewer bundle.

Each source has limits. CloudTrail records API activity, not guest-runtime behavior. VPC Flow Logs do not capture every kind of IP traffic. Negative tests cover only the destinations, protocols, and window exercised. The report must preserve those limitations instead of turning incomplete visibility into a pass.

## Why the evaluation has phases

Downloading a model or installing packages during the measured window would undermine a restricted-egress claim. The proposed design therefore separates the lifecycle:

### Preparation

A pinned machine image is built, artifacts are imported through explicitly documented paths, expected digests are verified, and the evaluation service is installed. Preparation paths are recorded but excluded from the restricted evaluation claim.

### Evaluation

Preparation-only paths are removed. The system snapshots the effective controls, executes negative connectivity tests, runs the benchmark and RunWitness, and stores evidence locally. A strict variant retains no cloud-service endpoint during execution.

### Export and review

Only after execution completes is the documented export path restored. A separate reviewer verifies the bundle hashes and examines the evidence, unknowns, and decision rationale.

The transitions matter as much as the steady-state diagram. A route removed too late, an endpoint retained unintentionally, or an interactive management path left available changes the claim.

## Passing must require evidence—not optimism

Every required gate should resolve to one of four outcomes: `pass`, `fail`, `unknown`, or `invalid`.

Missing evidence is not a pass. Permission denied is not a pass. A stale snapshot is not proof of runtime state. If the required observer did not run or a log source failed to deliver, the result should say so plainly.

The first AWS case will test artifact identity, instance identity, public addressing, routes, private endpoints, packet controls, negative probes, benchmark completion, deployment thresholds, artifact integrity, audit completeness, and phase consistency.

It will not certify AWS, establish national sovereignty, inspect provider hardware, prove that every packet was observed, or make a legal compliance determination.

## The commercial opportunity is trust, not another dashboard

Enterprises do not need more confident labels. They need a reviewable chain from deployment claim to evidence to decision.

The open-source foundation can define portable evidence contracts, verification semantics, collectors, and reproducible reference cases. Environment-specific work can then focus on the hard parts: threat-model definition, evidence access, policy design, controlled execution, gap analysis, remediation, and a reviewer-ready report.

That boundary is important. The engine and public methodology remain open. A customer assessment applies the method to a private system without publishing the customer’s architecture or pretending that one run proves more than it observed.

## What comes next

Before any paid cloud resources are provisioned, the reference case needs sanitized fixtures and offline policy evaluation for routes, endpoints, addresses, encryption, logging, and permission-denied states. It then needs a low-cost CPU dry run and a deliberately failing configuration.

Only after those controls fail correctly should the project spend money on a public GPU run.

The standard should be simple: a deployment claim becomes credible when another reviewer can inspect the evidence, reproduce the integrity checks, see the limits, and reach the same bounded conclusion.

That is a stronger foundation for enterprise AI than calling an architecture “air-gapped” and asking everyone to trust the diagram.

---

RunWitness is an independent open-source project and is not affiliated with or endorsed by AWS, DocuPipe, DocuBench, Ollama, Microsoft, or Mistral AI. The full [AWS reference-case design](../docs/AWS-REFERENCE-CASE.md) is maintained in the repository.
