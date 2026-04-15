#!/usr/bin/env python3

import subprocess
import json
import sys
import time

REGION = "eu-west-3"
PROJECT = "secure-platform"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}✔ {msg}{RESET}")


def warn(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")


def err(msg):
    print(f"{RED}✘ {msg}{RESET}")


def cmd(command, capture=False, check=False):
    print(f"{BLUE}> {command}{RESET}")
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=capture,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"Command failed: {command}")
    if capture:
        return result.stdout.strip(), result.returncode
    return "", result.returncode


def j(command):
    out, rc = cmd(command, capture=True)
    if rc != 0 or not out:
        return None
    try:
        return json.loads(out)
    except Exception:
        return None


def matches(tags, env=None):
    tag_map = {t["Key"]: t["Value"] for t in tags or []}
    if tag_map.get("Project") != PROJECT:
        return False
    if env and tag_map.get("Environment") != env:
        return False
    return True


def wait_until(fn, attempts=60, delay=5):
    for _ in range(attempts):
        if fn():
            return True
        time.sleep(delay)
    return False


def delete_rds_instances(env=None):
    data = j(f"aws rds describe-db-instances --region {REGION}")
    if not data:
        return

    found = False
    for db in data.get("DBInstances", []):
        arn = db["DBInstanceArn"]
        tags_data = j(f"aws rds list-tags-for-resource --resource-name {arn} --region {REGION}")
        if not tags_data:
            continue
        if not matches(tags_data.get("TagList", []), env):
            continue

        found = True
        identifier = db["DBInstanceIdentifier"]
        cmd(
            f"aws rds delete-db-instance "
            f"--db-instance-identifier {identifier} "
            f"--skip-final-snapshot "
            f"--delete-automated-backups "
            f"--region {REGION}"
        )

    if found:
        ok("RDS delete requested")
        def all_gone():
            current = j(f"aws rds describe-db-instances --region {REGION}") or {"DBInstances": []}
            for db in current.get("DBInstances", []):
                arn = db["DBInstanceArn"]
                tags_data = j(f"aws rds list-tags-for-resource --resource-name {arn} --region {REGION}")
                if tags_data and matches(tags_data.get("TagList", []), env):
                    return False
            return True
        wait_until(all_gone, attempts=80, delay=15)
        ok("RDS deleted")
    else:
        ok("No RDS to delete")


def delete_ec2_instances(env=None):
    data = j(
        f"aws ec2 describe-instances --region {REGION} "
        f"--filters Name=instance-state-name,Values=pending,running,stopping,stopped"
    )
    if not data:
        return

    ids = []
    for res in data.get("Reservations", []):
        for inst in res.get("Instances", []):
            if matches(inst.get("Tags", []), env):
                ids.append(inst["InstanceId"])

    if not ids:
        ok("No EC2 to delete")
        return

    cmd(
        f"aws ec2 terminate-instances "
        f"--instance-ids {' '.join(ids)} "
        f"--region {REGION}"
    )
    cmd(
        f"aws ec2 wait instance-terminated "
        f"--instance-ids {' '.join(ids)} "
        f"--region {REGION}"
    )
    ok("EC2 deleted")


def delete_albs(env=None):
    data = j(f"aws elbv2 describe-load-balancers --region {REGION}")
    if not data:
        return

    arns = []
    for lb in data.get("LoadBalancers", []):
        tags_data = j(
            f"aws elbv2 describe-tags "
            f"--resource-arns {lb['LoadBalancerArn']} "
            f"--region {REGION}"
        )
        if not tags_data:
            continue
        tag_desc = tags_data.get("TagDescriptions", [])
        tags = tag_desc[0]["Tags"] if tag_desc else []
        if matches(tags, env):
            arns.append(lb["LoadBalancerArn"])

    if not arns:
        ok("No ALB to delete")
        return

    for arn in arns:
        cmd(f"aws elbv2 delete-load-balancer --load-balancer-arn {arn} --region {REGION}")

    def gone():
        current = j(f"aws elbv2 describe-load-balancers --region {REGION}") or {"LoadBalancers": []}
        existing = {lb["LoadBalancerArn"] for lb in current.get("LoadBalancers", [])}
        return all(arn not in existing for arn in arns)

    wait_until(gone, attempts=60, delay=10)
    ok("ALB deleted")


def delete_target_groups(env=None):
    data = j(f"aws elbv2 describe-target-groups --region {REGION}")
    if not data:
        return

    tgs = []
    for tg in data.get("TargetGroups", []):
        tags_data = j(
            f"aws elbv2 describe-tags "
            f"--resource-arns {tg['TargetGroupArn']} "
            f"--region {REGION}"
        )
        if not tags_data:
            continue
        tag_desc = tags_data.get("TagDescriptions", [])
        tags = tag_desc[0]["Tags"] if tag_desc else []
        if matches(tags, env):
            tgs.append(tg["TargetGroupArn"])

    if not tgs:
        ok("No target group to delete")
        return

    for arn in tgs:
        for _ in range(30):
            _, rc = cmd(f"aws elbv2 delete-target-group --target-group-arn {arn} --region {REGION}")
            if rc == 0:
                break
            time.sleep(10)

    ok("Target groups deleted")


def delete_wafs(env=None):
    data = j(f"aws wafv2 list-web-acls --scope REGIONAL --region {REGION}")
    if not data:
        return

    found = False
    for acl in data.get("WebACLs", []):
        detail = j(
            f"aws wafv2 get-web-acl "
            f"--name {acl['Name']} "
            f"--scope REGIONAL "
            f"--id {acl['Id']} "
            f"--region {REGION}"
        )
        if not detail:
            continue
        tags_data = j(
            f"aws wafv2 list-tags-for-resource "
            f"--resource-arn {detail['WebACL']['ARN']} "
            f"--region {REGION}"
        )
        tags = tags_data.get("TagInfoForResource", {}).get("TagList", []) if tags_data else []
        if not matches(tags, env):
            continue

        found = True
        cmd(
            f"aws wafv2 delete-web-acl "
            f"--name {acl['Name']} "
            f"--scope REGIONAL "
            f"--id {acl['Id']} "
            f"--lock-token {detail['LockToken']} "
            f"--region {REGION}"
        )

    ok("WAF deleted" if found else "No WAF to delete")


def delete_db_subnet_groups(env=None):
    data = j(f"aws rds describe-db-subnet-groups --region {REGION}")
    if not data:
        return

    found = False
    for group in data.get("DBSubnetGroups", []):
        arn = group["DBSubnetGroupArn"]
        tags_data = j(f"aws rds list-tags-for-resource --resource-name {arn} --region {REGION}")
        if not tags_data:
            continue
        if not matches(tags_data.get("TagList", []), env):
            continue

        found = True
        for _ in range(30):
            _, rc = cmd(
                f"aws rds delete-db-subnet-group "
                f"--db-subnet-group-name {group['DBSubnetGroupName']} "
                f"--region {REGION}"
            )
            if rc == 0:
                break
            time.sleep(10)

    ok("DB subnet groups deleted" if found else "No DB subnet group to delete")


def delete_s3(env=None):
    data = j(f"aws s3api list-buckets")
    if not data:
        return

    found = False
    for bucket in data.get("Buckets", []):
        name = bucket["Name"]
        tags_data = j(f"aws s3api get-bucket-tagging --bucket {name}")
        tags = tags_data.get("TagSet", []) if tags_data else []
        if not matches(tags, env):
            continue

        found = True
        cmd(f"aws s3 rm s3://{name} --recursive")
        cmd(f"aws s3api delete-bucket --bucket {name} --region {REGION}")

    ok("S3 deleted" if found else "No S3 to delete")


def delete_kms_aliases(env=None):
    data = j(f"aws kms list-aliases --region {REGION}")
    if not data:
        return

    aliases = []
    for alias in data.get("Aliases", []):
        name = alias.get("AliasName", "")
        if not name.startswith("alias/"):
            continue
        if PROJECT not in name:
            continue
        if env and f"-{env}" not in name:
            continue
        aliases.append(name)

    for name in aliases:
        cmd(f"aws kms delete-alias --alias-name {name} --region {REGION}")

    ok("KMS aliases deleted" if aliases else "No KMS alias to delete")


def delete_vpcs(env=None):
    data = j(f"aws ec2 describe-vpcs --region {REGION}")
    if not data:
        return

    for vpc in data.get("Vpcs", []):
        if vpc.get("IsDefault"):
            continue
        if not matches(vpc.get("Tags", []), env):
            continue

        vpc_id = vpc["VpcId"]
        warn(f"Deleting VPC {vpc_id}")

        data_ep = j(f"aws ec2 describe-vpc-endpoints --region {REGION}")
        if data_ep:
            ids = [ep["VpcEndpointId"] for ep in data_ep.get("VpcEndpoints", []) if ep["VpcId"] == vpc_id]
            if ids:
                cmd(f"aws ec2 delete-vpc-endpoints --vpc-endpoint-ids {' '.join(ids)} --region {REGION}")

        data_nat = j(f"aws ec2 describe-nat-gateways --region {REGION}")
        if data_nat:
            nat_ids = [ng["NatGatewayId"] for ng in data_nat.get("NatGateways", []) if ng["VpcId"] == vpc_id]
            for nat_id in nat_ids:
                cmd(f"aws ec2 delete-nat-gateway --nat-gateway-id {nat_id} --region {REGION}")
            if nat_ids:
                time.sleep(20)

        data_igw = j(f"aws ec2 describe-internet-gateways --region {REGION}")
        if data_igw:
            for igw in data_igw.get("InternetGateways", []):
                attached = any(att["VpcId"] == vpc_id for att in igw.get("Attachments", []))
                if attached:
                    cmd(
                        f"aws ec2 detach-internet-gateway "
                        f"--internet-gateway-id {igw['InternetGatewayId']} "
                        f"--vpc-id {vpc_id} "
                        f"--region {REGION}"
                    )
                    cmd(
                        f"aws ec2 delete-internet-gateway "
                        f"--internet-gateway-id {igw['InternetGatewayId']} "
                        f"--region {REGION}"
                    )

        data_eni = j(f"aws ec2 describe-network-interfaces --region {REGION}")
        if data_eni:
            for eni in data_eni.get("NetworkInterfaces", []):
                if eni["VpcId"] != vpc_id:
                    continue
                attachment = eni.get("Attachment")
                if attachment and attachment.get("AttachmentId") and attachment.get("Status") == "attached":
                    cmd(
                        f"aws ec2 detach-network-interface "
                        f"--attachment-id {attachment['AttachmentId']} "
                        f"--force "
                        f"--region {REGION}"
                    )
                    time.sleep(3)
                cmd(
                    f"aws ec2 delete-network-interface "
                    f"--network-interface-id {eni['NetworkInterfaceId']} "
                    f"--region {REGION}"
                )

        data_sub = j(f"aws ec2 describe-subnets --region {REGION}")
        if data_sub:
            for subnet in data_sub.get("Subnets", []):
                if subnet["VpcId"] == vpc_id:
                    cmd(f"aws ec2 delete-subnet --subnet-id {subnet['SubnetId']} --region {REGION}")

        data_rta = j(f"aws ec2 describe-route-tables --region {REGION}")
        if data_rta:
            for rt in data_rta.get("RouteTables", []):
                if rt["VpcId"] != vpc_id:
                    continue
                for assoc in rt.get("Associations", []):
                    if not assoc.get("Main") and assoc.get("RouteTableAssociationId"):
                        cmd(
                            f"aws ec2 disassociate-route-table "
                            f"--association-id {assoc['RouteTableAssociationId']} "
                            f"--region {REGION}"
                        )
                main = any(a.get("Main") for a in rt.get("Associations", []))
                if not main:
                    cmd(f"aws ec2 delete-route-table --route-table-id {rt['RouteTableId']} --region {REGION}")

        data_sg = j(f"aws ec2 describe-security-groups --region {REGION}")
        if data_sg:
            for sg in data_sg.get("SecurityGroups", []):
                if sg["VpcId"] == vpc_id and sg["GroupName"] != "default":
                    cmd(f"aws ec2 delete-security-group --group-id {sg['GroupId']} --region {REGION}")

        for _ in range(30):
            _, rc = cmd(f"aws ec2 delete-vpc --vpc-id {vpc_id} --region {REGION}")
            if rc == 0:
                break
            time.sleep(10)

    ok("VPCs deleted")


def terraform_destroy(env=None):
    if env:
        path = f"terraform/envs/{env}"
        _, rc = cmd(f"test -d {path}")
        if rc == 0:
            cmd(f"cd {path} && terraform init")
            cmd(f"cd {path} && terraform destroy -var-file=terraform.tfvars -auto-approve")
    else:
        for name in ("dev", "staging", "prod"):
            path = f"terraform/envs/{name}"
            _, rc = cmd(f"test -d {path}")
            if rc == 0:
                cmd(f"cd {path} && terraform init")
                cmd(f"cd {path} && terraform destroy -var-file=terraform.tfvars -auto-approve")


def main():
    env = sys.argv[1] if len(sys.argv) == 2 else None

    print(f"\n{RED}--- HARD RESET {'(' + env.upper() + ')' if env else '(ALL)'} ---{RESET}\n")

    terraform_destroy(env)
    delete_albs(env)
    time.sleep(20)
    delete_target_groups(env)
    delete_wafs(env)
    delete_rds_instances(env)
    delete_db_subnet_groups(env)
    delete_ec2_instances(env)
    delete_s3(env)
    delete_kms_aliases(env)
    delete_vpcs(env)

    print(f"\n{GREEN}--- DONE ---{RESET}\n")


if __name__ == "__main__":
    main()
