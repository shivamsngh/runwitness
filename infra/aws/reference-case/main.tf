locals {
  name           = var.case_id
  transfer_phase = var.phase != "evaluation"
  evidence_key   = "evidence/${var.case_id}"
}

resource "terraform_data" "account_guard" {
  lifecycle {
    precondition {
      condition     = data.aws_caller_identity.current.account_id == var.expected_account_id
      error_message = "Authenticated AWS account does not match expected_account_id."
    }
    precondition {
      condition     = !var.launch_instance || (can(regex("^ami-[0-9a-f]+$", var.ami_id)) && can(regex("^[0-9a-f]{64}$", var.runner_bundle_sha256)) && can(regex("^[0-9a-f]{64}$", var.model_bundle_sha256)))
      error_message = "Launching requires a valid AMI and frozen 64-character artifact hashes."
    }
  }
}

resource "aws_kms_key" "case" {
  description             = "RunWitness ${var.case_id} evidence and volume key"
  deletion_window_in_days = 7
  enable_key_rotation     = false

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AccountAdministration"
        Effect    = "Allow"
        Principal = { AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AWSLogDelivery"
        Effect    = "Allow"
        Principal = { Service = ["cloudtrail.amazonaws.com", "delivery.logs.amazonaws.com"] }
        Action    = ["kms:GenerateDataKey*", "kms:Decrypt", "kms:DescribeKey"]
        Resource  = "*"
        Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      }
    ]
  })
}

resource "aws_kms_alias" "case" {
  name          = "alias/runwitness-${var.case_id}"
  target_key_id = aws_kms_key.case.key_id
}

resource "aws_s3_bucket" "case" {
  bucket_prefix = "runwitness-${var.case_id}-"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "case" {
  bucket                  = aws_s3_bucket.case.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "case" {
  bucket = aws_s3_bucket.case.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "case" {
  bucket = aws_s3_bucket.case.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.case.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "case" {
  bucket = aws_s3_bucket.case.id
  rule {
    id     = "expire-temporary-case-data"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
    noncurrent_version_expiration { noncurrent_days = 7 }
  }
}

resource "aws_vpc" "case" {
  cidr_block           = "10.77.0.0/24"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = local.name }
}

resource "aws_subnet" "evaluation" {
  vpc_id                  = aws_vpc.case.id
  cidr_block              = "10.77.0.0/26"
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.name}-evaluation" }
}

resource "aws_route_table" "evaluation" {
  vpc_id = aws_vpc.case.id
  tags   = { Name = "${local.name}-evaluation" }
}

resource "aws_route_table_association" "evaluation" {
  subnet_id      = aws_subnet.evaluation.id
  route_table_id = aws_route_table.evaluation.id
}

resource "aws_network_acl" "evaluation" {
  vpc_id     = aws_vpc.case.id
  subnet_ids = [aws_subnet.evaluation.id]

  dynamic "egress" {
    for_each = local.transfer_phase ? [1] : []
    content {
      protocol   = "-1"
      rule_no    = 100
      action     = "allow"
      cidr_block = "0.0.0.0/0"
      from_port  = 0
      to_port    = 0
    }
  }

  dynamic "ingress" {
    for_each = local.transfer_phase ? [1] : []
    content {
      protocol   = "-1"
      rule_no    = 100
      action     = "allow"
      cidr_block = "0.0.0.0/0"
      from_port  = 0
      to_port    = 0
    }
  }

  tags = { Name = "${local.name}-evaluation" }
}

data "aws_prefix_list" "s3" {
  name = "com.amazonaws.${var.region}.s3"
}

resource "aws_security_group" "evaluation" {
  name_prefix = "${local.name}-"
  description = "No ingress; S3 HTTPS egress only outside the evaluation phase"
  vpc_id      = aws_vpc.case.id

  dynamic "egress" {
    for_each = local.transfer_phase ? [1] : []
    content {
      description     = "Case S3 endpoint only"
      from_port       = 443
      to_port         = 443
      protocol        = "tcp"
      prefix_list_ids = [data.aws_prefix_list.s3.id]
    }
  }

  tags = { Name = "${local.name}-evaluation" }
}

resource "aws_vpc_endpoint" "s3" {
  count             = local.transfer_phase ? 1 : 0
  vpc_id            = aws_vpc.case.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.evaluation.id]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource  = [aws_s3_bucket.case.arn, "${aws_s3_bucket.case.arn}/*"]
    }]
  })
}

resource "aws_iam_role" "instance" {
  name_prefix = "${local.name}-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "instance" {
  role = aws_iam_role.instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = aws_s3_bucket.case.arn },
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${aws_s3_bucket.case.arn}/${var.runner_bundle_key}", "${aws_s3_bucket.case.arn}/${var.model_bundle_key}"] },
      { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.case.arn}/${local.evidence_key}/*" },
      { Effect = "Allow", Action = ["kms:Decrypt", "kms:GenerateDataKey"], Resource = aws_kms_key.case.arn }
    ]
  })
}

resource "aws_iam_instance_profile" "instance" {
  name_prefix = "${local.name}-"
  role        = aws_iam_role.instance.name
}

resource "aws_instance" "evaluation" {
  count                                = var.launch_instance ? 1 : 0
  ami                                  = var.ami_id
  instance_type                        = var.instance_type
  subnet_id                            = aws_subnet.evaluation.id
  vpc_security_group_ids               = [aws_security_group.evaluation.id]
  iam_instance_profile                 = aws_iam_instance_profile.instance.name
  associate_public_ip_address          = false
  instance_initiated_shutdown_behavior = "stop"
  user_data_replace_on_change          = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_gib
    encrypted             = true
    kms_key_id            = aws_kms_key.case.arn
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/templates/runner.sh.tftpl", {
    bucket               = aws_s3_bucket.case.id
    case_id              = var.case_id
    runner_bundle_key    = var.runner_bundle_key
    runner_bundle_sha256 = var.runner_bundle_sha256
    model_bundle_key     = var.model_bundle_key
    model_bundle_sha256  = var.model_bundle_sha256
    evidence_key         = local.evidence_key
    max_instance_minutes = var.max_instance_minutes
  })

  tags = { Name = local.name }

  depends_on = [terraform_data.account_guard, aws_vpc_endpoint.s3]
}

resource "aws_ec2_tag" "phase" {
  count       = var.launch_instance ? 1 : 0
  resource_id = aws_instance.evaluation[0].id
  key         = "RunWitnessPhase"
  value       = var.phase
  depends_on  = [aws_network_acl.evaluation, aws_security_group.evaluation, aws_vpc_endpoint.s3]
}

resource "aws_flow_log" "evaluation" {
  count                    = var.launch_instance ? 1 : 0
  eni_id                   = aws_instance.evaluation[0].primary_network_interface_id
  log_destination          = aws_s3_bucket.case.arn
  log_destination_type     = "s3"
  traffic_type             = "ALL"
  max_aggregation_interval = 60
  log_format               = "$${version} $${account-id} $${interface-id} $${srcaddr} $${dstaddr} $${srcport} $${dstport} $${protocol} $${packets} $${bytes} $${start} $${end} $${action} $${log-status}"
  destination_options {
    file_format                = "plain-text"
    hive_compatible_partitions = false
    per_hour_partition         = true
  }
}

resource "aws_cloudtrail" "case" {
  name                          = local.name
  s3_bucket_name                = aws_s3_bucket.case.id
  include_global_service_events = false
  is_multi_region_trail         = false
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.case.arn
  depends_on                    = [aws_s3_bucket_policy.case]
}

resource "aws_s3_bucket_policy" "case" {
  bucket = aws_s3_bucket.case.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.case.arn, "${aws_s3_bucket.case.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "CloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.case.arn
        Condition = { StringEquals = { "AWS:SourceArn" = "arn:${data.aws_partition.current.partition}:cloudtrail:${var.region}:${data.aws_caller_identity.current.account_id}:trail/${local.name}" } }
      },
      {
        Sid       = "CloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.case.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control", "AWS:SourceArn" = "arn:${data.aws_partition.current.partition}:cloudtrail:${var.region}:${data.aws_caller_identity.current.account_id}:trail/${local.name}" } }
      },
      {
        Sid       = "FlowLogAclCheck"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = ["s3:GetBucketAcl", "s3:ListBucket"]
        Resource  = aws_s3_bucket.case.arn
        Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      },
      {
        Sid       = "FlowLogWrite"
        Effect    = "Allow"
        Principal = { Service = "delivery.logs.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.case.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = { StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control", "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
      }
    ]
  })
}
