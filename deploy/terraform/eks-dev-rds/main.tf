# Dev RDS PostgreSQL/PostGIS for Photon-Ops Navigator, placed inside the
# existing macmtn-dev-cluster VPC. This module does not create the EKS
# cluster, ECR repositories, ALB Controller, or DNS/ACM records -- those are
# separate prerequisites tracked in deploy/eks/dev-runbook.md.

data "aws_eks_cluster" "this" {
  name = var.eks_cluster_name
}

locals {
  vpc_id             = data.aws_eks_cluster.this.vpc_config[0].vpc_id
  subnet_ids         = data.aws_eks_cluster.this.vpc_config[0].subnet_ids
  cluster_sg_id      = data.aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
  ingress_source_sgs = concat([local.cluster_sg_id], var.additional_ingress_security_group_ids)

  tags = merge(
    {
      Project     = "photon-ops-navigator"
      Environment = "dev"
      ManagedBy   = "terraform"
    },
    var.tags,
  )
}

resource "random_password" "master" {
  length  = 24
  special = true
  # Excluded so the generated password never needs URL-encoding inside the
  # postgresql+asyncpg:// connection string the API reads from DATABASE_URL.
  override_special = "-_."
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.db_identifier}-subnet-group"
  subnet_ids = local.subnet_ids
  tags       = local.tags
}

resource "aws_security_group" "rds" {
  name        = "${var.db_identifier}-rds"
  description = "Allow PostgreSQL access from the ${var.eks_cluster_name} EKS cluster"
  vpc_id      = local.vpc_id
  tags        = local.tags

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "rds_ingress" {
  for_each                 = toset(local.ingress_source_sgs)
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = each.value
  description               = "PostgreSQL from ${each.value}"
}

resource "aws_db_instance" "this" {
  identifier     = var.db_identifier
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.master_username
  password = random_password.master.result
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  backup_retention_period = var.backup_retention_period
  deletion_protection     = var.deletion_protection
  skip_final_snapshot     = var.skip_final_snapshot
  apply_immediately       = true
  auto_minor_version_upgrade = true

  tags = local.tags
}

# The chart's externalSecrets.enabled=true path (see values-dev.yaml) syncs
# this secret into the photonops-runtime Kubernetes Secret via the External
# Secrets Operator. If ESO is not installed on macmtn-dev-cluster, read this
# secret's value with `aws secretsmanager get-secret-value` and create the
# Kubernetes Secret directly instead -- see deploy/eks/dev-runbook.md.
resource "aws_secretsmanager_secret" "runtime" {
  name        = "photonops/dev/runtime"
  description = "Photon-Ops Navigator Dev runtime secret (database_url, optional bedrock_api_key)"
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "runtime" {
  secret_id = aws_secretsmanager_secret.runtime.id
  secret_string = jsonencode({
    database_url = "postgresql+asyncpg://${var.master_username}:${random_password.master.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}"
  })
}
