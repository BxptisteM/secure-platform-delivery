# Secure Platform Delivery – Infrastructure

Infrastructure provisioning on AWS using Terraform, with dynamic configuration generation via Jinja.

---

## Stack

* Terraform
* AWS
* Jinja (`jinja4config`)
* GitHub Actions

---

## Project Structure

```
terraform/
  modules/
  envs/
    devs/
      terraform.tfvars.j2
    staging/
      terraform.tfvars.j2
    prod/
      terraform.tfvars.j2

config.yaml
generate_configs.py
```

---

## Overview

* `terraform.tfvars` files are NOT committed
* They are generated from `.j2` templates
* Sensitive values (CIDR, subnets, etc.) are injected via environment variables

---

## config.yaml

Contains:

* global non-sensitive values
* references to environment variables using Jinja

Example:

```yaml
shared:
  aws_region: "eu-west-3"
  project_name: "secure-platform"
  availability_zones:
    - "eu-west-3a"
    - "eu-west-3b"
  allowed_ingress_cidr_blocks:
    - "0.0.0.0/0"

environments:
  dev:
    environment: "dev"
    vpc_cidr: "{{ 'VPC_CIDR' | env }}"
    public_subnet_cidrs:
      - "{{ 'PUBLIC_SUBNET_CIDR_1' | env }}"
      - "{{ 'PUBLIC_SUBNET_CIDR_2' | env }}"
    private_app_subnet_cidrs:
      - "{{ 'PRIVATE_APP_SUBNET_CIDR_1' | env }}"
      - "{{ 'PRIVATE_APP_SUBNET_CIDR_2' | env }}"
    private_db_subnet_cidrs:
      - "{{ 'PRIVATE_DB_SUBNET_CIDR_1' | env }}"
      - "{{ 'PRIVATE_DB_SUBNET_CIDR_2' | env }}"
```

---

## Generate tfvars

```bash
python3 generate_configs.py
```

---

## GitHub Secrets Strategy

Instead of many secrets, use ONE secret per environment.

### DEV secret

```
VPC_CIDR=
PUBLIC_SUBNET_CIDR_1=
PUBLIC_SUBNET_CIDR_2=
PRIVATE_APP_SUBNET_CIDR_1=
PRIVATE_APP_SUBNET_CIDR_2=
PRIVATE_DB_SUBNET_CIDR_1=
PRIVATE_DB_SUBNET_CIDR_2=
```

---

## GitHub Actions Example

```yaml
- name: Create .env
  run: |
    cat > .env <<EOF
    AWS_REGION=eu-west-3
    PROJECT_NAME=secure-platform
    AWS_AZ_1=eu-west-3a
    AWS_AZ_2=eu-west-3b
    ALLOWED_INGRESS_CIDR_1=0.0.0.0/0
    ${{ secrets.DEV }}
    EOF

- name: Generate tfvars
  run: python3 generate_configs.py
```

---

## Terraform Commands

```bash
cd terraform/envs/devs

terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

---

## .gitignore

```gitignore
.env
output/
.jinja4config-output/
**/terraform.tfvars
```

---

## Security

* No secrets stored in the repository
* `terraform.tfvars` are ignored
* Network configuration stored only in GitHub Secrets
* Injected at runtime

---

## Summary

* Templates `.j2` are versioned
* `config.yaml` is versioned
* `.env` is generated locally or in CI
* Secrets are handled via GitHub
