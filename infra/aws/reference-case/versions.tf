terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project              = "RunWitness"
      RunWitnessCase       = var.case_id
      RunWitnessExpiration = var.expires_at
      ManagedBy            = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}
