variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_app_subnet_cidrs" {
  description = "CIDR blocks for private application subnets"
  type        = list(string)
}

variable "private_db_subnet_cidrs" {
  description = "CIDR blocks for private database subnets"
  type        = list(string)
}

variable "allowed_ingress_cidr_blocks" {
  description = "CIDR blocks allowed to access public resources"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "alb_internal" {
  description = "Whether the ALB is internal"
  type        = bool
  default     = false
}

variable "alb_enable_deletion_protection" {
  description = "Enable deletion protection on the ALB"
  type        = bool
  default     = false
}

variable "alb_idle_timeout" {
  description = "Idle timeout for the ALB in seconds"
  type        = number
  default     = 60
}

variable "enable_waf" {
  description = "Enable WAF for the ALB"
  type        = bool
  default     = true
}

variable "waf_default_action" {
  description = "Default action for WAF: allow or block"
  type        = string
  default     = "allow"

  validation {
    condition     = contains(["allow", "block"], var.waf_default_action)
    error_message = "waf_default_action must be either 'allow' or 'block'."
  }
}

variable "waf_managed_rule_groups" {
  description = "Managed rule groups attached to the WAF"
  type = list(object({
    name            = string
    priority        = number
    vendor_name     = optional(string, "AWS")
    override_action = optional(string, "none")
  }))
  default = [
    {
      name            = "AWSManagedRulesCommonRuleSet"
      priority        = 10
      vendor_name     = "AWS"
      override_action = "none"
    },
    {
      name            = "AWSManagedRulesKnownBadInputsRuleSet"
      priority        = 20
      vendor_name     = "AWS"
      override_action = "none"
    }
  ]
}

variable "kms_key_arn" {
  description = "KMS key ARN used for encryption"
  type        = string
}

variable "db_username" {
  description = "RDS master username"
  type        = string
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}
