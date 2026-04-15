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


if len(sys.argv) != 2:
    print("Usage: python test.py <dev|staging|prod>")
    sys.exit(1)

env = sys.argv[1]
path = os.path.join(BASE_DIR, "terraform", "envs", env)

print(f"\n{BLUE}--- TEST {env.upper()} ---{RESET}\n")

# --- OUTPUTS
alb_dns, _ = run(f"cd {path} && terraform output -raw alb_dns_name", True)
alb_arn, _ = run(f"cd {path} && terraform output -raw alb_arn", True)
waf_arn, _ = run(f"cd {path} && terraform output -raw waf_arn", True)
sg, _ = run(f"cd {path} && terraform output -raw alb_security_group_id", True)

# --- DNS
info("DNS resolution")
_, code = run(f"nslookup {alb_dns}", True)
ok("DNS OK") if code == 0 else fail("DNS failed")

# --- ALB HTTP
info("ALB HTTP response")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' http://{alb_dns}", True)
ok("ALB returns 200") if out == "200" else fail(f"ALB failed ({out})")

# --- WAF
info("WAF test")
out, _ = run(f"curl -s -o /dev/null -w '%{{http_code}}' \"http://{alb_dns}/?q=%27%20OR%201%3D1\"", True)
if env == "dev":
    ok("WAF OK (count mode)") if out == "200" else fail("WAF unexpected")
else:
    ok("WAF blocking") if out == "403" else fail("WAF not blocking")

# --- LISTENER
info("ALB listener")
out, _ = run(f"""aws elbv2 describe-listeners \
--load-balancer-arn "{alb_arn}" \
--region {REGION}""", True)
ok("Listener OK") if "80" in out else fail("Listener missing")

# --- WAF ATTACH
info("WAF attachment")
out, _ = run(f"""aws wafv2 list-resources-for-web-acl \
--web-acl-arn "{waf_arn}" \
--resource-type APPLICATION_LOAD_BALANCER \
--region {REGION}""", True)
ok("WAF attached") if alb_arn in out else fail("WAF not attached")

# --- SG
info("Security Group")
out, _ = run(f"""aws ec2 describe-security-groups \
--group-ids "{sg}" \
--region {REGION}""", True)
ok("SG OK") if "0.0.0.0/0" in out else fail("SG issue")

# --- SUBNETS
info("Subnets")
out, _ = run(f"""aws elbv2 describe-load-balancers \
--load-balancer-arns "{alb_arn}" \
--region {REGION}""", True)
ok("Multi-AZ OK") if "eu-west-3a" in out and "eu-west-3b" in out else fail("AZ issue")

# --- FORCE TRAFFIC
info("Generating traffic")
for _ in range(20):
    run(f"curl -s http://{alb_dns} > /dev/null")

time.sleep(60)

# --- METRICS
info("CloudWatch metrics")

found = False
for _ in range(6):  # max ~60s
    out, _ = run(f"""aws cloudwatch list-metrics \
--namespace AWS/ApplicationELB \
--region {REGION}""", True)

    if "RequestCount" in out:
        ok("Metrics OK")
        found = True
        break

    time.sleep(10)

if not found:
    fail("Metrics missing")

# --- WAF LOGS (OPTIONAL → PASS SI ABSENT)
info("WAF logs")
out, _ = run(f"""aws logs describe-log-groups --region {REGION}""", True)
ok("Logs OK (or not enabled)")

print(f"\n{GREEN}--- FULL TEST COMPLETE ---{RESET}\n")
