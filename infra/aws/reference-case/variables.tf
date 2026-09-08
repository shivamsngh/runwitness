variable "region" {
  description = "AWS Region for the bounded reference case."
  type        = string
  default     = "us-east-1"
}

variable "case_id" {
  description = "Unique identifier used on every resource and in teardown checks."
  type        = string
  validation {
    condition     = can(regex("^rw-[a-z0-9-]{3,32}$", var.case_id))
    error_message = "case_id must match rw-[a-z0-9-]{3,32}."
  }
}

variable "expected_account_id" {
  description = "Fail planning if credentials point at a different AWS account."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must be a 12-digit AWS account ID."
  }
}

variable "expires_at" {
  description = "Human-readable UTC expiry tag, reviewed before apply."
  type        = string
}

variable "phase" {
  description = "Preparation permits only the case S3 bucket; evaluation removes every egress rule and endpoint; export restores the bounded S3 path."
  type        = string
  default     = "preparation"
  validation {
    condition     = contains(["preparation", "evaluation", "export"], var.phase)
    error_message = "phase must be preparation, evaluation, or export."
  }
}

variable "launch_instance" {
  description = "Keep false for the first apply; upload frozen artifacts before enabling."
  type        = bool
  default     = false
}

variable "ami_id" {
  description = "Reviewed x86_64 GPU AMI with an L40S-compatible driver, AWS CLI, curl, tar, and sha256sum preinstalled."
  type        = string
  default     = ""
}

variable "instance_type" {
  description = "GPU instance used for the bounded run."
  type        = string
  default     = "g6e.xlarge"
}

variable "runner_bundle_key" {
  description = "S3 key of the frozen runner tar archive."
  type        = string
  default     = "inputs/runner.tar.gz"
}

variable "runner_bundle_sha256" {
  description = "Expected lowercase SHA-256 of the runner archive."
  type        = string
  default     = ""
}

variable "model_bundle_key" {
  description = "S3 key of the frozen model archive or file."
  type        = string
  default     = "inputs/model.bundle"
}

variable "model_bundle_sha256" {
  description = "Expected lowercase SHA-256 of the model artifact."
  type        = string
  default     = ""
}

variable "root_volume_gib" {
  description = "Encrypted root volume size."
  type        = number
  default     = 100
  validation {
    condition     = var.root_volume_gib >= 40 && var.root_volume_gib <= 250
    error_message = "root_volume_gib must be between 40 and 250 GiB."
  }
}

variable "max_instance_minutes" {
  description = "Guest watchdog stops the instance after this many minutes."
  type        = number
  default     = 45
  validation {
    condition     = var.max_instance_minutes >= 10 && var.max_instance_minutes <= 120
    error_message = "max_instance_minutes must be between 10 and 120."
  }
}
