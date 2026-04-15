module "kms" {
  source = "../../modules/kms"

  name        = var.project_name
  environment = var.environment
}

module "environment" {
  source = "../../modules/environment"

  project_name                   = var.project_name
  environment                    = var.environment
  vpc_cidr                       = var.vpc_cidr
  availability_zones             = var.availability_zones
  public_subnet_cidrs            = var.public_subnet_cidrs
  private_app_subnet_cidrs       = var.private_app_subnet_cidrs
  private_db_subnet_cidrs        = var.private_db_subnet_cidrs
  allowed_ingress_cidr_blocks    = var.allowed_ingress_cidr_blocks
  alb_internal                   = var.alb_internal
  alb_enable_deletion_protection = var.alb_enable_deletion_protection
  alb_idle_timeout               = var.alb_idle_timeout
  enable_waf                     = var.enable_waf
  waf_default_action             = var.waf_default_action
  waf_managed_rule_groups        = var.waf_managed_rule_groups
}

output "kms_key_id" {
  value       = module.kms.kms_key_id
  description = "KMS Key ID for dev environment"
}

output "kms_key_arn" {
  value       = module.kms.kms_key_arn
  description = "KMS Key ARN for dev environment"
}

output "vpc_id" {
  value       = module.environment.vpc_id
  description = "VPC ID for dev environment"
}

output "public_subnet_ids" {
  value       = module.environment.public_subnet_ids
  description = "Public subnet IDs for dev environment"
}

output "private_app_subnet_ids" {
  value       = module.environment.private_app_subnet_ids
  description = "Private application subnet IDs for dev environment"
}

output "private_db_subnet_ids" {
  value       = module.environment.private_db_subnet_ids
  description = "Private database subnet IDs for dev environment"
}

output "alb_security_group_id" {
  value       = module.environment.alb_security_group_id
  description = "ALB security group ID for dev environment"
}

output "app_security_group_id" {
  value       = module.environment.app_security_group_id
  description = "Application security group ID for dev environment"
}

output "db_security_group_id" {
  value       = module.environment.db_security_group_id
  description = "Database security group ID for dev environment"
}

output "db_subnet_group_name" {
  value       = module.environment.db_subnet_group_name
  description = "DB subnet group name for dev environment"
}

output "alb_id" {
  value       = module.environment.alb_id
  description = "ALB ID for dev environment"
}

output "alb_arn" {
  value       = module.environment.alb_arn
  description = "ALB ARN for dev environment"
}

output "alb_dns_name" {
  value       = module.environment.alb_dns_name
  description = "ALB DNS name for dev environment"
}

output "alb_zone_id" {
  value       = module.environment.alb_zone_id
  description = "ALB hosted zone ID for dev environment"
}

output "waf_id" {
  value       = module.environment.waf_id
  description = "WAF ID for dev environment"
}

output "waf_arn" {
  value       = module.environment.waf_arn
  description = "WAF ARN for dev environment"
}

output "waf_name" {
  value       = module.environment.waf_name
  description = "WAF name for dev environment"
}
