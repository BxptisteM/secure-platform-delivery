#!/usr/bin/env python3

import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd, cwd=None):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd)

if len(sys.argv) != 2:
    print("Usage: python launch.py <dev|staging|prod>")
    exit(1)

env = sys.argv[1]
path = os.path.join(BASE_DIR, "terraform", "envs", env)

print(f"\n--- DEPLOY {env.upper()} ---\n")

run("terraform init", cwd=path)
run("terraform validate", cwd=path)
run("terraform plan -var-file=terraform.tfvars", cwd=path)
run("terraform apply -var-file=terraform.tfvars -auto-approve", cwd=path)

print("\n--- DONE ---\n")
