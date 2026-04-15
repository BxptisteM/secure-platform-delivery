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

output "alb_id" {
  description = "ALB ID"
  value       = aws_lb.this.id
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.this.arn
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.this.dns_name
}

output "alb_zone_id" {
  description = "ALB hosted zone ID"
  value       = aws_lb.this.zone_id
}

output "waf_id" {
  description = "WAF ID"
  value       = try(aws_wafv2_web_acl.this[0].id, null)
}

output "waf_arn" {
  description = "WAF ARN"
  value       = try(aws_wafv2_web_acl.this[0].arn, null)
}

output "waf_name" {
  description = "WAF name"
  value       = try(aws_wafv2_web_acl.this[0].name, null)
}

output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.this.identifier
}

output "db_instance_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.this.endpoint
}

output "secure_bucket_name" {
  description = "Encrypted S3 bucket name"
  value       = aws_s3_bucket.secure.bucket
}


