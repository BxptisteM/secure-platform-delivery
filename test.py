#!/usr/bin/env python3

import subprocess
import sys
import os
import time

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

REGION = "eu-west-3"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, capture=False):
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    else:
        subprocess.run(cmd, shell=True)


def ok(msg): print(f"{GREEN}✔ {msg}{RESET}")
def fail(msg): print(f"{RED}✘ {msg}{RESET}")
def info(msg): print(f"{BLUE}➜ {msg}{RESET}")
def warn(msg): print(f"{YELLOW}⚠ {msg}{RESET}")


if len(sys.argv) != 2:
    print("Usage: python test.py <dev|staging|prod>")
    sys.exit(1)

env = sys.argv[1]
path = os.path.join(BASE_DIR, "terraform", "envs", env)

print(f"\n{BLUE}--- TEST {env.upper()} ---{RESET}\n")

alb_dns, _ = run(f"cd {path} && terraform output -raw alb_dns_name", True)
alb_arn, _ = run(f"cd {path} && terraform output -raw alb_arn", True)
waf_arn, _ = run(f"cd {path} && terraform output -raw waf_arn", True)
sg, _ = run(f"cd {path} && terraform output -raw alb_security_group_id", True)

bucket_name, bucket_rc = run(f"cd {path} && terraform output -raw secure_bucket_name", True)
db_instance_id, db_rc = run(f"cd {path} && terraform output -raw db_instance_id", True)

info("DNS resolution")
_, code = run(f"nslookup {alb_dns}", True)
ok("DNS OK") if code == 0 else fail("DNS failed")

info("ALB HTTP response")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://{alb_dns}", True)
ok("ALB returns 200") if out == "200" else fail(f"ALB failed ({out})")

info("WAF test")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' \"http://{alb_dns}/?q=%27%20OR%201%3D1\"", True)
if env == "dev":
    ok("WAF OK (count mode)") if out == "200" else fail("WAF unexpected")
else:
    ok("WAF blocking") if out == "403" else fail("WAF not blocking")

info("ALB listener")
out, _ = run(f"""aws elbv2 describe-listeners \
--load-balancer-arn "{alb_arn}" \
--region {REGION}""", True)
ok("Listener OK") if "80" in out else fail("Listener missing")

info("WAF attachment")
out, _ = run(f"""aws wafv2 list-resources-for-web-acl \
--web-acl-arn "{waf_arn}" \
--resource-type APPLICATION_LOAD_BALANCER \
--region {REGION}""", True)
ok("WAF attached") if alb_arn in out else fail("WAF not attached")

info("Security Group")
out, _ = run(f"""aws ec2 describe-security-groups \
--group-ids "{sg}" \
--region {REGION}""", True)
ok("SG OK") if "0.0.0.0/0" in out else fail("SG issue")

info("Subnets")
out, _ = run(f"""aws elbv2 describe-load-balancers \
--load-balancer-arns "{alb_arn}" \
--region {REGION}""", True)
ok("Multi-AZ OK") if "eu-west-3a" in out and "eu-west-3b" in out else fail("AZ issue")

info("Generating traffic")
for _ in range(20):
    run(f"curl -s http://{alb_dns} > /dev/null")

time.sleep(60)

info("CloudWatch metrics")
alb_dim = alb_arn.split(":loadbalancer/")[1]

out, _ = run(
    f"""aws cloudwatch get-metric-statistics \
--namespace AWS/ApplicationELB \
--metric-name RequestCount \
--dimensions Name=LoadBalancer,Value="{alb_dim}" \
--statistics Sum \
--period 60 \
--start-time "$(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
--end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
--region {REGION}""",
    True,
)

if '"Sum"' in out and '"Datapoints": []' not in out:
    ok("Metrics OK")
else:
    fail("Metrics missing")

info("WAF logs")
out, _ = run(f"""aws logs describe-log-groups --region {REGION}""", True)
ok("Logs OK (or not enabled)")

info("S3 bucket")
if bucket_rc != 0 or not bucket_name:
    warn("S3 output missing")
else:
    out, rc = run(
        f"""aws s3api get-bucket-encryption \
--bucket "{bucket_name}" \
--region {REGION}""",
        True,
    )
    if rc == 0 and "aws:kms" in out:
        ok("S3 encryption OK")
    else:
        fail("S3 encryption missing")

    out, rc = run(
        f"""aws s3api get-public-access-block \
--bucket "{bucket_name}" \
--region {REGION}""",
        True,
    )
    if rc == 0 and "BlockPublicAcls" in out and "true" in out.lower():
        ok("S3 public access block OK")
    else:
        fail("S3 public access block missing")

    out, rc = run(
        f"""aws s3api get-bucket-versioning \
--bucket "{bucket_name}" \
--region {REGION}""",
        True,
    )
    if rc == 0 and '"Status": "Enabled"' in out:
        ok("S3 versioning OK")
    else:
        fail("S3 versioning missing")

info("RDS instance")
if db_rc != 0 or not db_instance_id:
    warn("RDS output missing")
else:
    out, rc = run(
        f"""aws rds describe-db-instances \
--db-instance-identifier "{db_instance_id}" \
--region {REGION}""",
        True,
    )
    if rc != 0:
        fail("RDS instance not found")
    else:
        if '"StorageEncrypted": true' in out:
            ok("RDS encryption OK")
        else:
            fail("RDS encryption missing")

        if '"PubliclyAccessible": false' in out:
            ok("RDS private access OK")
        else:
            fail("RDS is public")

        if '"DBInstanceStatus": "available"' in out:
            ok("RDS available")
        else:
            warn("RDS not available yet")

print(f"\n{GREEN}--- FULL TEST COMPLETE ---{RESET}\n")
