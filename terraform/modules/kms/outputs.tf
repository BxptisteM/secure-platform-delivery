output "kms_key_id" {
  description = "KMS Key ID"
  value       = aws_kms_key.this.key_id
}

output "kms_key_arn" {
  description = "KMS Key ARN"
  value       = aws_kms_key.this.arn
}
