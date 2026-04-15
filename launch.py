#!/usr/bin/env python3

import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd=None):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

plan_only = "--plan-only" in sys.argv
if plan_only:
    sys.argv.remove("--plan-only")

if len(sys.argv) != 2:
    print("Usage: python launch.py <dev|staging|prod> [--plan-only]")
    exit(1)

env = sys.argv[1]
path = os.path.join(BASE_DIR, "terraform", "envs", env)

print(f"\n--- DEPLOY {env.upper()} ('Plan' Mode: {plan_only}) ---\n")

run("terraform init", cwd=path)
run("terraform validate", cwd=path)
run("terraform plan -var-file=terraform.tfvars", cwd=path)

if not plan_only:
    run("terraform apply -var-file=terraform.tfvars -auto-approve", cwd=path)

print("\n--- DONE ---\n")
