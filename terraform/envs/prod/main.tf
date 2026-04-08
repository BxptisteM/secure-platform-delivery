module "kms" {
  source = "../../modules/kms"

  name        = var.project_name
  environment = var.environment
}

module "environment" {
  source = "../../modules/environment"

  project_name                = var.project_name
  environment                 = var.environment
  vpc_cidr                    = var.vpc_cidr
  availability_zones          = var.availability_zones
  public_subnet_cidrs         = var.public_subnet_cidrs
  private_app_subnet_cidrs    = var.private_app_subnet_cidrs
  private_db_subnet_cidrs     = var.private_db_subnet_cidrs
  allowed_ingress_cidr_blocks = var.allowed_ingress_cidr_blocks
}

output "kms_key_id" {
  value       = module.kms.kms_key_id
  description = "KMS Key ID for production environment"
}

output "kms_key_arn" {
  value       = module.kms.kms_key_arn
  description = "KMS Key ARN for production environment"
}

output "vpc_id" {
  value       = module.environment.vpc_id
  description = "VPC ID for production environment"
}

output "public_subnet_ids" {
  value       = module.environment.public_subnet_ids
  description = "Public subnet IDs for production environment"
}

output "private_app_subnet_ids" {
  value       = module.environment.private_app_subnet_ids
  description = "Private application subnet IDs for production environment"
}

output "private_db_subnet_ids" {
  value       = module.environment.private_db_subnet_ids
  description = "Private database subnet IDs for production environment"
}

output "alb_security_group_id" {
  value       = module.environment.alb_security_group_id
  description = "ALB security group ID for production environment"
}

output "app_security_group_id" {
  value       = module.environment.app_security_group_id
  description = "Application security group ID for production environment"
}

output "db_security_group_id" {
  value       = module.environment.db_security_group_id
  description = "Database security group ID for production environment"
}

output "db_subnet_group_name" {
  value       = module.environment.db_subnet_group_name
  description = "DB subnet group name for production environment"
}
