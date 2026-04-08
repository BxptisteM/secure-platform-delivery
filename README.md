Secure, production-grade cloud platform designed to rebuild and harden a legacy application environment.

This repository contains a complete Infrastructure as Code (IaC) implementation using Terraform, targeting AWS with a strong focus on security, scalability, and compliance. The platform is structured around isolated environments (development, staging, production) and follows best practices in cloud architecture and DevSecOps.

Key features include:

* Fully automated infrastructure provisioning (VPCs, subnets, IAM, RDS, S3, monitoring)
* Strict network isolation with multi-VPC architecture
* End-to-end encryption (at rest via KMS, in transit via TLS)
* Centralized logging, auditing, and threat detection (CloudTrail, CloudWatch, Security Hub)
* Zero hardcoded secrets, with secure secret management
* CI/CD pipeline with integrated security scanning (Checkov, Trivy, Gitleaks)
* Infrastructure compliance aligned with GDPR and cloud security standards

The project aims to provide a secure, auditable, and reproducible cloud foundation suitable for modern applications operating in regulated environments.
