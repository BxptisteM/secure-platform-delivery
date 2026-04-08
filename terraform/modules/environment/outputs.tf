output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs"
  value       = aws_subnet.private_app[*].id
}

output "private_db_subnet_ids" {
  description = "Private database subnet IDs"
  value       = aws_subnet.private_db[*].id
}

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "app_security_group_id" {
  description = "Application security group ID"
  value       = aws_security_group.app.id
}

output "db_security_group_id" {
  description = "Database security group ID"
  value       = aws_security_group.db.id
}

output "db_subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.this.name
}
