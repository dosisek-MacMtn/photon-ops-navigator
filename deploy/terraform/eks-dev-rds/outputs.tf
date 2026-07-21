output "db_endpoint" {
  description = "RDS connection endpoint (host:port)."
  value       = aws_db_instance.this.endpoint
}

output "db_address" {
  description = "RDS host name, without the port."
  value       = aws_db_instance.this.address
}

output "db_port" {
  value = aws_db_instance.this.port
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

output "security_group_id" {
  description = "Security group attached to the RDS instance. Add more ingress rules here if another client (e.g. a bastion) needs direct access."
  value       = aws_security_group.rds.id
}

output "db_subnet_group_name" {
  value = aws_db_subnet_group.this.name
}

output "runtime_secret_arn" {
  description = "Secrets Manager ARN holding {\"database_url\": \"...\"}. Point External Secrets at this, or read it with `aws secretsmanager get-secret-value` for a manual Kubernetes Secret."
  value       = aws_secretsmanager_secret.runtime.arn
}

output "database_url" {
  description = "Full DATABASE_URL for the API. Sensitive -- avoid printing this in CI logs; prefer the runtime_secret_arn output plus ESO/manual secret creation."
  value       = "postgresql+asyncpg://${var.master_username}:${random_password.master.result}@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.db_name}"
  sensitive   = true
}
