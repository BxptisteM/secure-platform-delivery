variable "name" {
  description = "Name of the KMS key"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "enable_key_rotation" {
  description = "Enable automatic key rotation"
  type        = bool
  default     = true
}

variable "deletion_window_in_days" {
  description = "Number of days before KMS key deletion"
  type        = number
  default     = 7
}
