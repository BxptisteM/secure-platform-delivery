import subprocess
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REGION         = "eu-west-3"
TFSTATE_BUCKET = "secure-platform-tfstate"
LOCK_TABLE     = "secure-platform-tfstate-lock"

BLUE   = "\033[94m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"


def run(cmd, cwd=None, silent=False):
    if not silent:
        print(f"{BLUE}> {cmd}{RESET}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=silent, text=True)
    if not silent and result.returncode != 0:
        print(f"{RED}Command failed with exit code {result.returncode}{RESET}")
        if result.stderr:
            print(result.stderr)
    return result


def get_aws_id(command):
    res = run(command, silent=True)
    if res.returncode == 0 and res.stdout.strip():
        val = res.stdout.strip().replace('"', '').replace("'", "")
        return val if val not in ("None", "") else None
    return None


def bootstrap_backend():
    """Create S3 bucket + DynamoDB lock table if they don't already exist.
    No state migration — S3 becomes the backend for all future runs.
    """
    print(f"\n{YELLOW}--- BOOTSTRAPPING TERRAFORM BACKEND ---{RESET}")

    # ── S3 bucket ──────────────────────────────────────────────────────────
    res = run(f"aws s3api head-bucket --bucket {TFSTATE_BUCKET} --region {REGION}", silent=True)
    if res.returncode != 0:
        print(f"  Creating S3 bucket: {TFSTATE_BUCKET}")
        run(
            f"aws s3api create-bucket --bucket {TFSTATE_BUCKET} --region {REGION}"
            f" --create-bucket-configuration LocationConstraint={REGION}",
        )
        run(f"aws s3api put-bucket-versioning --bucket {TFSTATE_BUCKET}"
            f" --versioning-configuration Status=Enabled", silent=True)
        run(
            f"aws s3api put-bucket-encryption --bucket {TFSTATE_BUCKET}"
            f" --server-side-encryption-configuration"
            r' "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"AES256\"},\"BucketKeyEnabled\":true}]}"',
            silent=True,
        )
        run(
            f"aws s3api put-public-access-block --bucket {TFSTATE_BUCKET}"
            f" --public-access-block-configuration"
            f" BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
            silent=True,
        )
        print(f"  {GREEN}✔ S3 bucket created{RESET}")
    else:
        print(f"  {GREEN}✔ S3 bucket already exists{RESET}")

    # ── DynamoDB lock table ────────────────────────────────────────────────
    res = run(f"aws dynamodb describe-table --table-name {LOCK_TABLE} --region {REGION}", silent=True)
    if res.returncode != 0:
        print(f"  Creating DynamoDB lock table: {LOCK_TABLE}")
        run(
            f"aws dynamodb create-table --table-name {LOCK_TABLE} --region {REGION}"
            f" --attribute-definitions AttributeName=LockID,AttributeType=S"
            f" --key-schema AttributeName=LockID,KeyType=HASH"
            f" --billing-mode PAY_PER_REQUEST",
        )
        run(f"aws dynamodb wait table-exists --table-name {LOCK_TABLE} --region {REGION}", silent=True)
        print(f"  {GREEN}✔ DynamoDB lock table created{RESET}")
    else:
        print(f"  {GREEN}✔ DynamoDB lock table already exists{RESET}")

    print(f"{GREEN}Backend ready — s3://{TFSTATE_BUCKET}{RESET}\n")


def auto_repair(env, path):
    print(f"\n{YELLOW}--- INTELLIGENT AUTO-REPAIR (Syncing AWS -> Terraform) ---{RESET}")

    project  = "secure-platform"
    region   = "eu-west-3"
    db_id    = f"{project}-{env}-db"
    alb_name = f"{project}-{env}-alb"

    # 1. VPC
    vpc_id = get_aws_id(
        f"aws ec2 describe-vpcs --filters Name=tag:Name,Values={project}-{env}-vpc"
        f" --query \"Vpcs[0].VpcId\" --output text --region {region}"
    )
    if vpc_id:
        print(f"  Found VPC: {vpc_id}")
        run(f"terraform import -var-file=terraform.tfvars module.environment.aws_vpc.this {vpc_id}", cwd=path, silent=True)

        # SG ALB
        alb_sg = get_aws_id(f"aws elbv2 describe-load-balancers --names {alb_name} --query \"LoadBalancers[0].SecurityGroups[0]\" --output text --region {region}")
        if alb_sg:
            run(f"terraform import -var-file=terraform.tfvars module.environment.aws_security_group.alb {alb_sg}", cwd=path, silent=True)

        # SG DB
        db_sg = get_aws_id(f"aws rds describe-db-instances --db-instance-identifier {db_id} --query \"DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId\" --output text --region {region}")
        if db_sg:
            run(f"terraform import -var-file=terraform.tfvars module.environment.aws_security_group.db {db_sg}", cwd=path, silent=True)

        # SG App
        app_sg = get_aws_id(f"aws ec2 describe-instances --filters Name=vpc-id,Values={vpc_id} Name=tag:Project,Values={project} Name=instance-state-name,Values=running,stopped --query \"Reservations[0].Instances[0].SecurityGroups[0].GroupId\" --output text --region {region}")
        if app_sg:
            run(f"terraform import -var-file=terraform.tfvars module.environment.aws_security_group.app {app_sg}", cwd=path, silent=True)

    # 2. DB Subnet Group + private subnets
    dsg = f"{project}-{env}-db-subnet-group"
    run(f"terraform import -var-file=terraform.tfvars module.environment.aws_db_subnet_group.this {dsg}", cwd=path, silent=True)
    sub_data = run(f"aws rds describe-db-subnet-groups --db-subnet-group-name {dsg} --query \"DBSubnetGroups[0].Subnets[*].SubnetIdentifier\" --output json --region {region}", silent=True)
    if sub_data.stdout:
        try:
            for i, s_id in enumerate(json.loads(sub_data.stdout)):
                run(f"terraform import -var-file=terraform.tfvars module.environment.aws_subnet.private_db[{i}] {s_id}", cwd=path, silent=True)
        except Exception:
            pass

    # 3. ALB + Target Group
    alb_arn = get_aws_id(f"aws elbv2 describe-load-balancers --names {alb_name} --query \"LoadBalancers[0].LoadBalancerArn\" --output text --region {region}")
    if alb_arn:
        run(f"terraform import -var-file=terraform.tfvars module.environment.aws_lb.this {alb_arn}", cwd=path, silent=True)

    tg_arn = get_aws_id(f"aws elbv2 describe-target-groups --names {project}-{env}-tg --query \"TargetGroups[0].TargetGroupArn\" --output text --region {region}")
    if tg_arn:
        run(f"terraform import -var-file=terraform.tfvars module.environment.aws_lb_target_group.this {tg_arn}", cwd=path, silent=True)

    # 4. WAF
    waf_name = f"{project}-{env}-waf"
    waf_id = get_aws_id(f"aws wafv2 list-web-acls --scope REGIONAL --region {region} --query \"WebACLs[?Name=='{waf_name}'].Id\" --output text")
    if waf_id:
        run(f"terraform import -var-file=terraform.tfvars module.environment.aws_wafv2_web_acl.this[0] {waf_id}/{waf_name}/REGIONAL", cwd=path, silent=True)

    # 5. RDS + S3
    run(f"terraform import -var-file=terraform.tfvars module.environment.aws_db_instance.this {db_id}", cwd=path, silent=True)
    run(f"terraform import -var-file=terraform.tfvars module.environment.aws_s3_bucket.secure {project}-{env}-secure-bucket", cwd=path, silent=True)

    print(f"{GREEN}Sync complete.{RESET}\n")


if __name__ == "__main__":
    plan_only = "--plan-only" in sys.argv
    if plan_only:
        sys.argv.remove("--plan-only")

    if len(sys.argv) < 2:
        print("Usage: python launch.py <dev|staging|prod> [--plan-only]")
        exit(1)

    env  = sys.argv[1]
    path = os.path.join(BASE_DIR, "terraform", "envs", env)

    if not os.path.exists(path):
        print(f"{RED}Environment directory not found: {path}{RESET}")
        exit(1)

    print(f"\n{BLUE}--- DEPLOYING {env.upper()} (Plan Only: {plan_only}) ---{RESET}\n")

    # 0. Generate tfvars from templates
    print(f"{YELLOW}--- GENERATING TFVARS FROM TEMPLATES ---{RESET}")
    run("python generate_tfvars.py")

    bootstrap_backend()                                      # 1. S3 bucket + DynamoDB si pas encore créés
    run("terraform init", cwd=path)                          # 2. Init avec le backend S3
    if not plan_only:
        auto_repair(env, path)                               # 3. Sync AWS -> state

    run("terraform plan -var-file=terraform.tfvars", cwd=path)
    if not plan_only:
        run("terraform apply -var-file=terraform.tfvars -auto-approve", cwd=path)

    print(f"\n{GREEN}--- DEPLOYMENT FINISHED ---{RESET}\n")
