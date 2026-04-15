variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used by the environment"
  type        = list(string)
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
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
  description = "Allowed ingress CIDR blocks for the load balancer"
  type        = list(string)
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
