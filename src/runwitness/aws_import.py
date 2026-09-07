"""Import saved AWS responses into an offline-reviewable evidence bundle."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from .aws_evidence import SCHEMA_VERSION, AwsEvidenceError, evaluate_aws_evidence
from .evidence import sha256


IMPORT_VERSION = "runwitness.aws-import/v0.1"
COLLECTOR_VERSION = "runwitness.aws-importer/v0.1"
INPUT_GROUPS = {
    "ec2": ("ec2",),
    "routes": ("routes",),
    "endpoints": ("endpoints",),
    "packet_controls": ("security_groups", "network_acls"),
    "storage": ("volumes", "s3_public_access_block"),
    "logging": ("logging_observation",),
    "artifacts": ("artifacts",),
}


class IncompleteAwsEvidence(ValueError):
    """A readable response does not contain enough scoped evidence to decide."""


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AwsEvidenceError(f"cannot read {path}: {exc}") from exc


def _safe_input(root, relative):
    if not isinstance(relative, str) or not relative:
        raise AwsEvidenceError("observed inputs require a relative path")
    target = (root / relative).resolve()
    if target == root or root not in target.parents:
        raise AwsEvidenceError(f"input path escapes capture directory: {relative}")
    if not target.is_file():
        raise AwsEvidenceError(f"input file does not exist: {relative}")
    return target


def _load_capture(path):
    source = Path(path).resolve()
    capture = _json(source)
    if not isinstance(capture, dict) or capture.get("schema_version") != IMPORT_VERSION:
        raise AwsEvidenceError(f"schema_version must be {IMPORT_VERSION!r}")
    for field in ("evidence_id", "profile", "scope", "evaluation_window", "inputs"):
        if field not in capture:
            raise AwsEvidenceError(f"{field} is required")
    if not isinstance(capture["inputs"], dict):
        raise AwsEvidenceError("inputs must be an object")
    return capture, source


def _timestamp_min(values):
    def parsed(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    try:
        return min(values, key=parsed)
    except (TypeError, ValueError) as exc:
        raise AwsEvidenceError("captured_at values must be RFC 3339 timestamps") from exc


def _input_state(capture, names):
    records = []
    for name in names:
        record = capture["inputs"].get(name)
        if not isinstance(record, dict):
            return "unavailable", f"required import input is missing: {name}", []
        status = record.get("status")
        if status == "permission_denied":
            return "permission_denied", record.get("reason") or f"access denied for {name}", []
        if status == "unavailable":
            return "unavailable", record.get("reason") or f"input unavailable: {name}", []
        if status != "observed":
            raise AwsEvidenceError(f"inputs.{name}.status is invalid")
        if not isinstance(record.get("captured_at"), str):
            raise AwsEvidenceError(f"inputs.{name}.captured_at is required")
        records.append((name, record))
    return "observed", None, records


def _route_target(route):
    keys = (
        ("NatGatewayId", "nat_gateway"),
        ("EgressOnlyInternetGatewayId", "egress_only_internet_gateway"),
        ("TransitGatewayId", "transit_gateway"),
        ("VpcPeeringConnectionId", "vpc_peering"),
        ("NetworkInterfaceId", "network_interface"),
    )
    gateway = route.get("GatewayId")
    if gateway == "local":
        return "local"
    if isinstance(gateway, str) and gateway.startswith("igw-"):
        return "internet_gateway"
    if isinstance(gateway, str) and gateway.startswith("vgw-"):
        return "vpn"
    for key, target in keys:
        if route.get(key):
            return target
    return "other"


def _transform(name, documents):
    if name == "ec2":
        instances = [instance for reservation in documents["ec2"].get("Reservations", []) for instance in reservation.get("Instances", [])]
        if not instances:
            raise IncompleteAwsEvidence("EC2 response contains no instance")
        if len(instances) != 1:
            raise AwsEvidenceError("EC2 import must contain exactly one instance")
        instance = instances[0]
        interfaces = instance.get("NetworkInterfaces", [])
        ipv6 = [address.get("Ipv6Address") for interface in interfaces for address in interface.get("Ipv6Addresses", []) if address.get("Ipv6Address")]
        return {"public_ipv4": instance.get("PublicIpAddress"), "ipv6_addresses": ipv6}
    if name == "routes":
        tables = documents["routes"].get("RouteTables", [])
        if not tables:
            raise IncompleteAwsEvidence("route-table response contains no route table")
        routes = [route for table in tables for route in table.get("Routes", [])]
        return {"entries": [{"destination": route.get("DestinationCidrBlock") or route.get("DestinationIpv6CidrBlock") or "unknown", "target_type": _route_target(route), "state": route.get("State", "active")} for route in routes]}
    if name == "endpoints":
        endpoints = documents["endpoints"].get("VpcEndpoints", [])
        return {"service_names": sorted({item["ServiceName"] for item in endpoints if item.get("State") not in {"deleted", "deleting", "failed"} and item.get("ServiceName")})}
    if name == "packet_controls":
        groups = documents["security_groups"].get("SecurityGroups", [])
        nacls = documents["network_acls"].get("NetworkAcls", [])
        if not groups or not nacls:
            raise IncompleteAwsEvidence("packet-control responses contain no security group or network ACL")
        sg_closed = bool(groups) and all(not group.get("IpPermissionsEgress", []) for group in groups)
        outbound_allows = [entry for nacl in nacls for entry in nacl.get("Entries", []) if entry.get("Egress") is True and entry.get("RuleAction") == "allow"]
        return {"security_group_egress_closed": sg_closed, "network_acl_egress_closed": bool(nacls) and not outbound_allows}
    if name == "storage":
        volumes = documents["volumes"].get("Volumes", [])
        block = documents["s3_public_access_block"].get("PublicAccessBlockConfiguration", {})
        if not volumes or not block:
            raise IncompleteAwsEvidence("storage responses contain no volume or S3 public-access-block configuration")
        encrypted = bool(volumes) and all(volume.get("Encrypted") is True for volume in volumes)
        customer_key = bool(volumes) and all(volume.get("KmsKeyId") and "alias/aws/ebs" not in volume.get("KmsKeyId", "") for volume in volumes)
        public_block = all(block.get(key) is True for key in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"))
        return {"encrypted": encrypted, "customer_managed_key": customer_key, "s3_public_access_block": public_block}
    if name == "logging":
        observation = documents["logging_observation"]
        if any(key not in observation for key in ("cloudtrail_delivered", "flow_logs_delivered", "flow_logs_skipped_records")):
            raise IncompleteAwsEvidence("logging observation is incomplete")
        return {key: observation.get(key) for key in ("cloudtrail_delivered", "flow_logs_delivered", "flow_logs_skipped_records")}
    if name == "artifacts":
        artifacts = documents["artifacts"]
        if not artifacts.get("expected_digests") or not artifacts.get("observed_digests"):
            raise IncompleteAwsEvidence("artifact digest observation is incomplete")
        return {"expected_digests": artifacts.get("expected_digests"), "observed_digests": artifacts.get("observed_digests")}
    raise AwsEvidenceError(f"unsupported source group: {name}")


def import_aws_capture(capture_path, output_path):
    """Create evidence.json, decision.json, and a hashed raw-source manifest."""
    capture, capture_source = _load_capture(capture_path)
    root = capture_source.parent
    output = Path(output_path).resolve()
    if output.exists():
        raise AwsEvidenceError(f"output already exists: {output}")
    output.mkdir(parents=True)
    raw_dir = output / "raw"
    raw_dir.mkdir()
    artifacts = []
    evidence_sources = {}
    try:
        shutil.copyfile(capture_source, output / "capture.json")
        for group, names in INPUT_GROUPS.items():
            status, reason, records = _input_state(capture, names)
            if status != "observed":
                evidence_sources[group] = {"status": status, "reason": reason}
                continue
            documents = {}
            times = []
            for name, record in records:
                source = _safe_input(root, record.get("path"))
                destination = raw_dir / f"{name}.json"
                shutil.copyfile(source, destination)
                documents[name] = _json(destination)
                times.append(record["captured_at"])
                artifacts.append({"name": name, "path": f"raw/{destination.name}", "sha256": sha256(destination), "captured_at": record["captured_at"]})
            try:
                data = _transform(group, documents)
            except IncompleteAwsEvidence as exc:
                evidence_sources[group] = {"status": "unavailable", "reason": str(exc)}
            else:
                evidence_sources[group] = {
                    "status": "observed",
                    "captured_at": _timestamp_min(times),
                    "collector": COLLECTOR_VERSION,
                    "data": data,
                }
        evidence = {
            "schema_version": SCHEMA_VERSION,
            "evidence_id": capture["evidence_id"],
            "profile": capture["profile"],
            "scope": capture["scope"],
            "evaluation_window": capture["evaluation_window"],
            "sources": evidence_sources,
        }
        decision = evaluate_aws_evidence(evidence)
        source_manifest = {"schema_version": IMPORT_VERSION, "collector_version": COLLECTOR_VERSION, "capture_manifest_sha256": sha256(capture_source), "artifacts": artifacts}
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output / "decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (output / "source-manifest.json").write_text(json.dumps(source_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return output, decision
    except Exception:
        # Leave no partial evidence bundle that could be mistaken for a completed import.
        shutil.rmtree(output)
        raise


def verify_aws_import_bundle(bundle_path):
    """Recalculate every preserved import hash without following paths outside the bundle."""
    root = Path(bundle_path).resolve()
    manifest_path = root / "source-manifest.json"
    checks = []
    if not manifest_path.is_file():
        return {"bundle": str(root), "overall": "fail", "checks": [{"name": "source_manifest", "status": "fail"}]}
    manifest = _json(manifest_path)
    capture = root / "capture.json"
    capture_actual = sha256(capture) if capture.is_file() else None
    checks.append({"name": "capture_manifest", "path": "capture.json", "expected_sha256": manifest.get("capture_manifest_sha256"), "actual_sha256": capture_actual, "status": "pass" if capture_actual == manifest.get("capture_manifest_sha256") else "fail"})
    for artifact in manifest.get("artifacts", []):
        relative = artifact.get("path", "") if isinstance(artifact, dict) else ""
        target = (root / relative).resolve()
        safe = target != root and root in target.parents
        actual = sha256(target) if safe and target.is_file() else None
        expected = artifact.get("sha256") if isinstance(artifact, dict) else None
        checks.append({"name": "raw_source", "path": relative, "expected_sha256": expected, "actual_sha256": actual, "status": "pass" if actual is not None and actual == expected else "fail"})
    for name in ("evidence.json", "decision.json"):
        checks.append({"name": name.removesuffix(".json"), "path": name, "status": "pass" if (root / name).is_file() else "fail"})
    return {"bundle": str(root), "overall": "pass" if checks and all(item["status"] == "pass" for item in checks) else "fail", "checks": checks}
