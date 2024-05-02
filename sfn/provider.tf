provider "aws" {
  region = "ap-southeast-2"
  assume_role {
    role_arn     = "arn:aws:iam::159851557642:role/dev_integration_terraform_role"
  }
}

provider "aws" {
  alias  = "peer"
  region = "ap-southeast-2"
  assume_role {
    role_arn     = "arn:aws:iam::159851557642:role/dev_integration_terraform_role"
  }
}

terraform {
  required_version = ">= 1.0.0,< 2.0.0"
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
    }
  }
}
