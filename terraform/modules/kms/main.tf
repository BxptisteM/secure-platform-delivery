resource "aws_kms_key" "this" {
  description             = "${var.name}-${var.environment}-kms-key"
  deletion_window_in_days = var.deletion_window_in_days
  enable_key_rotation     = var.enable_key_rotation

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootPermissions"
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "kms:*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:PrincipalAccount" = "${data.aws_caller_identity.current.account_id}"
          }
        }
      }
    ]
  })
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.name}-${var.environment}"
  target_key_id = aws_kms_key.this.key_id
}

data "aws_caller_identity" "current" {}
