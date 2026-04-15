#!/usr/bin/env python3

import subprocess
import json
import time

REGION = "eu-west-3"
PROJECT = "secure-platform"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def run(cmd):
    print(f"{BLUE}> {cmd}{RESET}")
    subprocess.run(cmd, shell=True)


def get_json(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def ok(msg): print(f"{GREEN}✔ {msg}{RESET}")
def warn(msg): print(f"{YELLOW}⚠ {msg}{RESET}")


# ---------------- ALB + TG ----------------
def delete_alb():
    data = get_json(f"aws elbv2 describe-load-balancers --region {REGION}")
    if data:
        for lb in data["LoadBalancers"]:
            if PROJECT in lb["LoadBalancerName"]:
                run(f"aws elbv2 delete-load-balancer --load-balancer-arn {lb['LoadBalancerArn']} --region {REGION}")

    data = get_json(f"aws elbv2 describe-target-groups --region {REGION}")
    if data:
        for tg in data["TargetGroups"]:
            if PROJECT in tg["TargetGroupName"]:
                run(f"aws elbv2 delete-target-group --target-group-arn {tg['TargetGroupArn']} --region {REGION}")

    ok("ALB cleaned")


# ---------------- WAF ----------------
def delete_waf():
    data = get_json(f"aws wafv2 list-web-acls --scope REGIONAL --region {REGION}")
    if data:
        for acl in data["WebACLs"]:
            if PROJECT in acl["Name"]:
                detail = get_json(
                    f"aws wafv2 get-web-acl --name {acl['Name']} "
                    f"--scope REGIONAL --id {acl['Id']} --region {REGION}"
                )
                if not detail:
                    continue

                token = detail["LockToken"]

                run(
                    f"aws wafv2 delete-web-acl "
                    f"--name {acl['Name']} "
                    f"--scope REGIONAL "
                    f"--id {acl['Id']} "
                    f"--lock-token {token} "
                    f"--region {REGION}"
                )

    ok("WAF cleaned")


# ---------------- DB SUBNET ----------------
def delete_db_subnet():
    data = get_json(f"aws rds describe-db-subnet-groups --region {REGION}")
    if data:
        for g in data["DBSubnetGroups"]:
            if PROJECT in g["DBSubnetGroupName"]:
                run(f"aws rds delete-db-subnet-group --db-subnet-group-name {g['DBSubnetGroupName']} --region {REGION}")

    ok("DB subnet cleaned")


# ---------------- KMS ----------------
def delete_kms():
    data = get_json(f"aws kms list-aliases --region {REGION}")
    if data:
        for a in data["Aliases"]:
            name = a.get("AliasName", "")
            if PROJECT in name:
                run(f"aws kms delete-alias --alias-name {name} --region {REGION}")

    ok("KMS cleaned")


# ---------------- VPC FULL CLEAN ----------------
def delete_vpcs():
    data = get_json(f"aws ec2 describe-vpcs --region {REGION}")
    if not data:
        return

    for vpc in data["Vpcs"]:
        vpc_id = vpc["VpcId"]

        if vpc.get("IsDefault"):
            continue

        tags = {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}
        if tags.get("Project") != PROJECT:
            continue

        warn(f"Deleting VPC {vpc_id}")

        # --- DELETE VPC ENDPOINTS ---
        endpoints = get_json(f"aws ec2 describe-vpc-endpoints --region {REGION}")
        if endpoints:
            for ep in endpoints["VpcEndpoints"]:
                if ep["VpcId"] == vpc_id:
                    run(f"aws ec2 delete-vpc-endpoints --vpc-endpoint-ids {ep['VpcEndpointId']} --region {REGION}")

        # --- DELETE NETWORK INTERFACES ---
        enis = get_json(f"aws ec2 describe-network-interfaces --region {REGION}")
        if enis:
            for eni in enis["NetworkInterfaces"]:
                if eni["VpcId"] == vpc_id:
                    eni_id = eni["NetworkInterfaceId"]

                    if eni.get("Attachment"):
                        att = eni["Attachment"]
                        if not att.get("DeleteOnTermination"):
                            run(f"aws ec2 detach-network-interface --attachment-id {att['AttachmentId']} --force --region {REGION}")

                    run(f"aws ec2 delete-network-interface --network-interface-id {eni_id} --region {REGION}")

        # --- IGW ---
        igws = get_json(f"aws ec2 describe-internet-gateways --region {REGION}")
        if igws:
            for igw in igws["InternetGateways"]:
                for att in igw.get("Attachments", []):
                    if att["VpcId"] == vpc_id:
                        run(f"aws ec2 detach-internet-gateway --internet-gateway-id {igw['InternetGatewayId']} --vpc-id {vpc_id} --region {REGION}")
                        run(f"aws ec2 delete-internet-gateway --internet-gateway-id {igw['InternetGatewayId']} --region {REGION}")

        # --- SUBNETS ---
        subs = get_json(f"aws ec2 describe-subnets --region {REGION}")
        if subs:
            for s in subs["Subnets"]:
                if s["VpcId"] == vpc_id:
                    run(f"aws ec2 delete-subnet --subnet-id {s['SubnetId']} --region {REGION}")

        # --- ROUTE TABLES ---
        rts = get_json(f"aws ec2 describe-route-tables --region {REGION}")
        if rts:
            for rt in rts["RouteTables"]:
                if rt["VpcId"] == vpc_id:
                    main = any(a.get("Main") for a in rt.get("Associations", []))
                    if not main:
                        run(f"aws ec2 delete-route-table --route-table-id {rt['RouteTableId']} --region {REGION}")

        # --- SECURITY GROUPS ---
        sgs = get_json(f"aws ec2 describe-security-groups --region {REGION}")
        if sgs:
            for sg in sgs["SecurityGroups"]:
                if sg["VpcId"] == vpc_id and sg["GroupName"] != "default":
                    run(f"aws ec2 delete-security-group --group-id {sg['GroupId']} --region {REGION}")

        # --- FINAL DELETE ---
        run(f"aws ec2 delete-vpc --vpc-id {vpc_id} --region {REGION}")

    ok("VPC cleaned")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    print(f"\n{RED}--- HARD RESET ---{RESET}\n")

    delete_alb()
    delete_waf()
    delete_db_subnet()
    delete_kms()

    time.sleep(10)

    delete_vpcs()

    print(f"\n{GREEN}--- DONE ---{RESET}\n")
