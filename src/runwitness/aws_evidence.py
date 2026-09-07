"""Offline evaluation for the versioned RunWitness AWS evidence profile."""

import json
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "runwitness.aws-evidence/v0.1"
EVALUATOR_VERSION = "runwitness.aws-policy/v0.1"
SOURCE_NAMES = (
    "ec2",
    "routes",
    "endpoints",
    "packet_controls",
    "storage",
    "logging",
    "artifacts",
)


class AwsEvidenceError(ValueError):
    pass


def _parse_time(value, pointer):
    if not isinstance(value, str):
        raise AwsEvidenceError(f"{pointer} must be an RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AwsEvidenceError(f"{pointer} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise AwsEvidenceError(f"{pointer} must include a timezone")
    return parsed.astimezone(timezone.utc)


def load_aws_evidence(path):
    source = Path(path).resolve()
    try:
        evidence = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AwsEvidenceError(str(exc)) from exc
    if not isinstance(evidence, dict):
        raise AwsEvidenceError("AWS evidence must be a JSON object")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise AwsEvidenceError(f"schema_version must be {SCHEMA_VERSION!r}")
    return evidence, source


def _decision(control, status, reason, references):
    return {
        "control": control,
        "status": status,
        "reason": reason,
        "evidence_references": references,
    }


def _source(evidence, name, decisions, evaluation_end):
    pointer = f"/sources/{name}"
    source = evidence.get("sources", {}).get(name)
    if source is None:
        decisions.append(_decision(name, "unknown", "required evidence source is missing", [pointer]))
        return None
    if not isinstance(source, dict):
        decisions.append(_decision(name, "invalid", "evidence source must be an object", [pointer]))
        return None
    status = source.get("status")
    if status in {"unavailable", "permission_denied"}:
        decisions.append(_decision(name, "unknown", f"source status is {status}", [f"{pointer}/status"]))
        return None
    if status != "observed":
        decisions.append(_decision(name, "invalid", "source status must be observed, unavailable, or permission_denied", [f"{pointer}/status"]))
        return None
    try:
        captured = _parse_time(source.get("captured_at"), f"{pointer}/captured_at")
    except AwsEvidenceError as exc:
        decisions.append(_decision(name, "invalid", str(exc), [f"{pointer}/captured_at"]))
        return None
    freshness = evidence.get("profile", {}).get("max_evidence_age_seconds", 900)
    if not isinstance(freshness, int) or isinstance(freshness, bool) or freshness < 0:
        decisions.append(_decision(name, "invalid", "max_evidence_age_seconds must be a non-negative integer", ["/profile/max_evidence_age_seconds"]))
        return None
    age = (evaluation_end - captured).total_seconds()
    if age < 0 or age > freshness:
        decisions.append(_decision(name, "unknown", "observed evidence is outside the permitted freshness window", [f"{pointer}/captured_at", "/evaluation_window/end", "/profile/max_evidence_age_seconds"]))
        return None
    data = source.get("data")
    if not isinstance(data, dict):
        decisions.append(_decision(name, "invalid", "observed source requires an object in data", [f"{pointer}/data"]))
        return None
    return data


def evaluate_aws_evidence(evidence):
    """Evaluate caller-supplied evidence without AWS credentials or network access."""
    if not isinstance(evidence, dict) or evidence.get("schema_version") != SCHEMA_VERSION:
        raise AwsEvidenceError(f"schema_version must be {SCHEMA_VERSION!r}")
    decisions = []
    profile = evidence.get("profile")
    if not isinstance(profile, dict):
        raise AwsEvidenceError("profile is required")
    profile_refs = ["/profile/id", "/profile/network_variant", "/profile/allowed_endpoint_services"]
    profile_id = profile.get("id")
    variant = profile.get("network_variant")
    allowed = profile.get("allowed_endpoint_services")
    profile_valid = (
        profile_id == "aws-restricted-egress/v0.1"
        and variant in {"strict", "restricted_egress"}
        and isinstance(allowed, list)
        and all(isinstance(item, str) for item in allowed)
        and len(allowed) == len(set(allowed))
        and not (variant == "strict" and allowed)
    )
    decisions.append(_decision(
        "profile_contract",
        "pass" if profile_valid else "invalid",
        "profile identifier and network variant are valid" if profile_valid else "profile identifier, network variant, or endpoint policy is invalid; strict mode permits no endpoints",
        profile_refs,
    ))
    scope = evidence.get("scope")
    scope_fields = ("account_ref", "region", "instance_ref", "subnet_ref")
    scope_valid = isinstance(scope, dict) and all(isinstance(scope.get(key), str) and scope.get(key) for key in scope_fields)
    decisions.append(_decision(
        "scope_contract",
        "pass" if scope_valid else "invalid",
        "scope contains account, Region, instance, and subnet references" if scope_valid else "scope is incomplete",
        [f"/scope/{key}" for key in scope_fields],
    ))
    window = evidence.get("evaluation_window")
    if not isinstance(window, dict):
        raise AwsEvidenceError("evaluation_window is required")
    start = _parse_time(window.get("start"), "/evaluation_window/start")
    end = _parse_time(window.get("end"), "/evaluation_window/end")
    if end <= start:
        decisions.append(_decision("evaluation_window", "invalid", "evaluation window end must be after start", ["/evaluation_window/start", "/evaluation_window/end"]))

    sources = {name: _source(evidence, name, decisions, end) for name in SOURCE_NAMES}

    ec2 = sources["ec2"]
    if ec2 is not None:
        public_ipv4 = ec2.get("public_ipv4")
        ipv6 = ec2.get("ipv6_addresses")
        if not isinstance(ipv6, list):
            decisions.append(_decision("public_addressing", "invalid", "ipv6_addresses must be an array", ["/sources/ec2/data/ipv6_addresses"]))
        elif public_ipv4 is not None or ipv6:
            decisions.append(_decision("public_addressing", "fail", "the evaluated instance has a public IPv4 or IPv6 address", ["/sources/ec2/data/public_ipv4", "/sources/ec2/data/ipv6_addresses"]))
        else:
            decisions.append(_decision("public_addressing", "pass", "no public IPv4 or IPv6 address is recorded", ["/sources/ec2/data/public_ipv4", "/sources/ec2/data/ipv6_addresses"]))

    routes = sources["routes"]
    if routes is not None:
        forbidden = {"internet_gateway", "nat_gateway", "egress_only_internet_gateway", "transit_gateway", "vpc_peering", "vpn", "direct_connect"}
        entries = routes.get("entries")
        if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
            decisions.append(_decision("public_routes", "invalid", "route entries must be an array of objects", ["/sources/routes/data/entries"]))
        else:
            found = [item.get("target_type") for item in entries if item.get("state") == "active" and item.get("target_type") in forbidden]
            decisions.append(_decision("public_routes", "fail" if found else "pass", "forbidden active route types: " + ", ".join(sorted(set(found))) if found else "no forbidden active route is recorded", ["/sources/routes/data/entries"]))

    endpoints = sources["endpoints"]
    if endpoints is not None:
        actual = endpoints.get("service_names")
        expected = profile.get("allowed_endpoint_services", [])
        if not isinstance(actual, list) or not isinstance(expected, list):
            decisions.append(_decision("endpoint_allowlist", "invalid", "endpoint service lists must be arrays", ["/sources/endpoints/data/service_names", "/profile/allowed_endpoint_services"]))
        else:
            extra, missing = sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual))
            ok = not extra and not missing
            reason = "endpoint inventory exactly matches the phase allowlist" if ok else f"unexpected={extra}; missing={missing}"
            decisions.append(_decision("endpoint_allowlist", "pass" if ok else "fail", reason, ["/sources/endpoints/data/service_names", "/profile/allowed_endpoint_services"]))

    packet = sources["packet_controls"]
    if packet is not None:
        sg, nacl = packet.get("security_group_egress_closed"), packet.get("network_acl_egress_closed")
        if not isinstance(sg, bool) or not isinstance(nacl, bool):
            decisions.append(_decision("packet_controls", "invalid", "packet-control results must be booleans", ["/sources/packet_controls/data/security_group_egress_closed", "/sources/packet_controls/data/network_acl_egress_closed"]))
        else:
            decisions.append(_decision("packet_controls", "pass" if sg and nacl else "fail", "security-group and network-ACL egress controls are closed" if sg and nacl else "one or more required egress controls are open", ["/sources/packet_controls/data/security_group_egress_closed", "/sources/packet_controls/data/network_acl_egress_closed"]))

    storage = sources["storage"]
    if storage is not None:
        encrypted = storage.get("encrypted")
        customer_key = storage.get("customer_managed_key")
        public_block = storage.get("s3_public_access_block")
        if not isinstance(encrypted, bool) or not isinstance(customer_key, bool) or not isinstance(public_block, bool):
            decisions.append(_decision("storage_encryption", "invalid", "storage and public-access-block results must be booleans", ["/sources/storage/data/encrypted", "/sources/storage/data/customer_managed_key", "/sources/storage/data/s3_public_access_block"]))
        else:
            ok = encrypted and customer_key and public_block
            decisions.append(_decision("storage_encryption", "pass" if ok else "fail", "storage is encrypted with a customer-managed key and S3 public access is blocked" if ok else "required storage encryption, key ownership, or S3 public-access blocking is absent", ["/sources/storage/data/encrypted", "/sources/storage/data/customer_managed_key", "/sources/storage/data/s3_public_access_block"]))

    logging = sources["logging"]
    if logging is not None:
        trail, flow, skipped = logging.get("cloudtrail_delivered"), logging.get("flow_logs_delivered"), logging.get("flow_logs_skipped_records")
        if not isinstance(trail, bool) or not isinstance(flow, bool) or not isinstance(skipped, int) or isinstance(skipped, bool) or skipped < 0:
            decisions.append(_decision("audit_completeness", "invalid", "logging fields have invalid types or values", ["/sources/logging/data"]))
        else:
            ok = trail and flow and skipped == 0
            decisions.append(_decision("audit_completeness", "pass" if ok else "fail", "required audit sources were delivered with no skipped flow records" if ok else "audit delivery is incomplete or flow records were skipped", ["/sources/logging/data/cloudtrail_delivered", "/sources/logging/data/flow_logs_delivered", "/sources/logging/data/flow_logs_skipped_records"]))

    artifacts = sources["artifacts"]
    if artifacts is not None:
        expected = artifacts.get("expected_digests")
        observed = artifacts.get("observed_digests")
        if not isinstance(expected, dict) or not isinstance(observed, dict) or not expected:
            decisions.append(_decision("artifact_identity", "invalid", "non-empty expected and observed digest objects are required", ["/sources/artifacts/data/expected_digests", "/sources/artifacts/data/observed_digests"]))
        else:
            ok = expected == observed
            decisions.append(_decision("artifact_identity", "pass" if ok else "fail", "all observed artifact digests match the frozen plan" if ok else "observed artifact digests do not match the frozen plan", ["/sources/artifacts/data/expected_digests", "/sources/artifacts/data/observed_digests"]))

    statuses = {item["status"] for item in decisions}
    if "invalid" in statuses:
        overall = "invalid"
    elif "fail" in statuses:
        overall = "fail"
    elif "unknown" in statuses:
        overall = "unknown"
    else:
        overall = "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "profile_id": profile.get("id"),
        "evidence_id": evidence.get("evidence_id"),
        "overall": overall,
        "decisions": decisions,
        "limitations": [
            "This evaluates supplied evidence; it does not query AWS or prove the evidence is complete.",
            "Configuration snapshots, audit logs, and negative tests do not individually prove an air gap.",
            "A result applies only to the declared resources and evaluation window.",
        ],
    }


def evaluate_aws_evidence_file(path):
    evidence, _ = load_aws_evidence(path)
    return evaluate_aws_evidence(evidence)
