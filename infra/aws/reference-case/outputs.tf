output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "region" {
  value = var.region
}

output "case_id" {
  value = var.case_id
}

output "phase" {
  value = var.phase
}

output "evidence_bucket" {
  value = aws_s3_bucket.case.id
}

output "evidence_prefix" {
  value = local.evidence_key
}

output "instance_id" {
  value = try(aws_instance.evaluation[0].id, null)
}

output "network_interface_id" {
  value = try(aws_instance.evaluation[0].primary_network_interface_id, null)
}

output "subnet_id" {
  value = aws_subnet.evaluation.id
}

output "route_table_id" {
  value = aws_route_table.evaluation.id
}

output "security_group_id" {
  value = aws_security_group.evaluation.id
}

output "network_acl_id" {
  value = aws_network_acl.evaluation.id
}

output "kms_key_arn" {
  value = aws_kms_key.case.arn
}
