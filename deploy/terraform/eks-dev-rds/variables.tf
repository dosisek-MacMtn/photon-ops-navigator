variable "aws_region" {
  description = "AWS region. Photon-Ops Navigator is region-pinned to us-east-1."
  type        = string
  default     = "us-east-1"
}

variable "eks_cluster_name" {
  description = "Name of the existing EKS cluster whose VPC/subnets/security group the RDS instance joins."
  type        = string
  default     = "macmtn-dev-cluster"
}

variable "db_identifier" {
  description = "RDS instance identifier."
  type        = string
  default     = "photonops-dev"
}

variable "db_name" {
  description = "Initial database name. Alembic migrations create the postgis extension and schema inside it."
  type        = string
  default     = "photonops"
}

variable "master_username" {
  description = "RDS master username."
  type        = string
  default     = "photonops"
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "engine_version" {
  description = "PostgreSQL engine version. Verify this minor version is still available in the target region before applying (`aws rds describe-db-engine-versions --engine postgres`)."
  type        = string
  default     = "16.4"
}

variable "allocated_storage" {
  description = "Allocated storage in GiB."
  type        = number
  default     = 20
}

variable "multi_az" {
  description = "Whether to run a standby replica in a second AZ. Not needed for a Dev/demo workload."
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Automated backup retention in days."
  type        = number
  default     = 1
}

variable "deletion_protection" {
  description = "RDS deletion protection. Left off for Dev so the instance can be torn down without an extra AWS console/CLI step."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "Skip the final snapshot on destroy. Left on for Dev; the fictional (DEV) seed dataset is reproducible from app.seed, so there is nothing irreplaceable to snapshot."
  type        = bool
  default     = true
}

variable "additional_ingress_security_group_ids" {
  description = "Extra security group IDs (beyond the EKS cluster security group) allowed to reach RDS on 5432, e.g. a bastion or CI runner security group."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
