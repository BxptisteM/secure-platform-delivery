#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
IMAGE = "ghcr.io/flavien-chenu/jinja4config:latest"

TEMPLATE_DIRS = [
    "terraform/envs/dev",
    "terraform/envs/staging",
    "terraform/envs/prod",
]

_DESCRIPTION = """\
Terraform tfvars Generation Script
=================================
Generates all terraform.tfvars files from terraform.tfvars.j2 templates using
the Docker image ghcr.io/flavien-chenu/jinja4config:latest.

How it works
------------
  Step 1  Search for every terraform.tfvars.j2 template in known Terraform env folders
  Step 2  Mount the repository in a jinja4config Docker container
  Step 3  Render each template independently with config.yaml from the repository root
  Step 4  Write generated files either:
            - directly into each env folder as terraform.tfvars
            - or inside ./output with the same folder structure

Reset mode
----------
With --reset, the script deletes only the terraform.tfvars files located in the
folders listed in TEMPLATE_DIRS.

Default behavior
----------------
Without --output, generated files overwrite the existing terraform.tfvars files
in their respective folders.

Output mode
-----------
With --output, files are generated under ./output while preserving the normal
directory tree, for example:
  output/terraform/envs/devs/terraform.tfvars
  output/terraform/envs/staging/terraform.tfvars
  output/terraform/envs/prod/terraform.tfvars

Environment variables
---------------------
  DOCKER_PLATFORM   Optional Docker platform override
                    Examples:
                      DOCKER_PLATFORM=linux/amd64
                      DOCKER_PLATFORM=linux/arm64

Root environment file
---------------------
A root .env file placed next to this script is automatically passed to the
Docker container with --env-file.

Requirements
------------
  - docker must be installed and available in PATH
  - config.yaml must exist at the repository root
  - terraform.tfvars.j2 templates must exist in the relevant folders
"""

_EXAMPLES = """\
examples:
  python3 generate_configs.py
      Generate all terraform.tfvars files in place and overwrite existing ones

  python3 generate_configs.py --output
      Generate all terraform.tfvars files inside ./output

  python3 generate_configs.py --reset
      Delete existing terraform.tfvars files only in known Terraform env folders
"""


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{RESET}    {msg}")


def success(msg: str) -> None:
    print(f"{GREEN}[SUCCESS]{RESET} {msg}")


def warning(msg: str) -> None:
    print(f"{YELLOW}[WARNING]{RESET} {msg}")


def detail(msg: str) -> None:
    print(f"    {msg}")


def fail(msg: str, code: int = 1) -> None:
    print(f"{RED}[ERROR]{RESET}   {msg}")
    sys.exit(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="generate_configs.py",
        description=_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_EXAMPLES,
    )
    parser.add_argument(
        "--output",
        action="store_true",
        help="Generate files inside ./output instead of overwriting terraform.tfvars in place.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only the terraform.tfvars files present in TEMPLATE_DIRS.",
    )
    return parser.parse_args()


def ensure_docker() -> None:
    if shutil.which("docker") is None:
        fail("docker is required but was not found in PATH")


def run(cmd: list[str], cwd: Path) -> None:
    info(f"Running command: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = (proc.stdout or "").strip()
    if output:
        detail(output)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")


def find_templates(repo_root: Path) -> list[Path]:
    info("Searching for terraform.tfvars.j2 templates")
    templates: list[Path] = []

    for directory in TEMPLATE_DIRS:
        template = repo_root / directory / "terraform.tfvars.j2"
        if template.exists():
            templates.append(template)
            detail(f"Found {template.relative_to(repo_root)}")
        else:
            warning(f"Missing template: {template.relative_to(repo_root)}")

    if not templates:
        fail("No terraform.tfvars.j2 templates found")

    success(f"{len(templates)} template(s) found")
    return templates


def cleanup_dir(path: Path) -> None:
    if path.exists():
        info(f"Cleaning directory: {path}")
        shutil.rmtree(path)


def build_docker_command(
    repo_root: Path,
    config_path: Path,
    output_dir: Path,
    template: Path,
    docker_platform: str | None,
    root_env_file: Path | None,
) -> list[str]:
    cmd = ["docker", "run", "--rm"]

    if docker_platform:
        cmd.extend(["--platform", docker_platform])

    if root_env_file is not None and root_env_file.exists():
        cmd.extend(["--env-file", str(root_env_file.resolve())])

    cmd.extend([
        "-v", f"{repo_root.resolve()}:/workspace",
        IMAGE,
        "--config", config_path.as_posix(),
        "--output-dir", output_dir.as_posix(),
        template.relative_to(repo_root).as_posix(),
    ])

    return cmd


def render_template(
    repo_root: Path,
    config_path: Path,
    temp_root: Path,
    template: Path,
    docker_platform: str | None,
    root_env_file: Path | None,
) -> Path:
    relative_template = template.relative_to(repo_root)
    isolated_output_dir = temp_root / relative_template.parent

    isolated_output_dir.mkdir(parents=True, exist_ok=True)

    docker_cmd = build_docker_command(
        repo_root=repo_root,
        config_path=config_path.relative_to(repo_root),
        output_dir=isolated_output_dir.relative_to(repo_root),
        template=template,
        docker_platform=docker_platform,
        root_env_file=root_env_file,
    )
    run(docker_cmd, repo_root)

    generated_file = isolated_output_dir / "terraform.tfvars"
    if not generated_file.exists():
        raise FileNotFoundError(f"Generated file not found: {generated_file}")

    return generated_file


def copy_generated_file(
    repo_root: Path,
    generated_file: Path,
    template: Path,
    use_output_dir: bool,
) -> None:
    relative_template = template.relative_to(repo_root)
    target_root = repo_root / "output" if use_output_dir else repo_root
    target_file = target_root / relative_template.parent / "terraform.tfvars"

    target_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generated_file, target_file)

    if use_output_dir:
        detail(f"Generated {target_file.relative_to(repo_root)}")
    else:
        detail(f"Overwritten {target_file.relative_to(repo_root)}")


def reset_tfvars_files(repo_root: Path) -> None:
    info("Reset mode enabled: deleting known terraform.tfvars files only")

    deleted_count = 0
    missing_count = 0

    for directory in TEMPLATE_DIRS:
        tfvars_file = repo_root / directory / "terraform.tfvars"
        if tfvars_file.exists():
            tfvars_file.unlink()
            detail(f"Deleted {tfvars_file.relative_to(repo_root)}")
            deleted_count += 1
        else:
            detail(f"Not found {tfvars_file.relative_to(repo_root)}")
            missing_count += 1

    success("Reset completed ✓")
    detail(f"Deleted    : {deleted_count}")
    detail(f"Not found  : {missing_count}")


def main() -> None:
    args = parse_args()
    repo_root = SCRIPT_DIR

    if args.reset:
        if args.output:
            warning("--output ignored when used with --reset")
        reset_tfvars_files(repo_root)
        return

    config_path = repo_root / "config.yaml"
    root_env_file = repo_root / ".env"
    temp_output_root = repo_root / ".jinja4config-output"
    docker_platform = os.getenv("DOCKER_PLATFORM")

    info("Terraform tfvars generation")
    ensure_docker()

    if not config_path.exists():
        fail(f"config.yaml not found: {config_path}")

    success(f"Using config file: {config_path.relative_to(repo_root)}")

    if root_env_file.exists():
        success(f"Using root environment file: {root_env_file.relative_to(repo_root)}")
    else:
        warning("Root .env not found, only host environment variables will be available inside Docker")

    if docker_platform:
        info(f"Using Docker platform from environment: {docker_platform}")
    else:
        info("No DOCKER_PLATFORM provided, using Docker default platform")

    templates = find_templates(repo_root)

    cleanup_dir(temp_output_root)
    temp_output_root.mkdir(parents=True, exist_ok=True)

    output_root = repo_root / "output"
    if args.output:
        cleanup_dir(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        info("Output mode enabled: files will be written under output")

    info("Rendering templates with jinja4config")

    for index, template in enumerate(templates, start=1):
        relative_template = template.relative_to(repo_root)
        info(f"[{index}/{len(templates)}] Rendering {relative_template}")
        generated_file = render_template(
            repo_root=repo_root,
            config_path=config_path,
            temp_root=temp_output_root,
            template=template,
            docker_platform=docker_platform,
            root_env_file=root_env_file if root_env_file.exists() else None,
        )
        copy_generated_file(
            repo_root=repo_root,
            generated_file=generated_file,
            template=template,
            use_output_dir=args.output,
        )

    cleanup_dir(temp_output_root)

    success("Config generation completed ✓")
    if args.output:
        detail("Mode       : output")
        detail("Directory  : output/")
    else:
        detail("Mode       : in-place")
        detail("Behavior   : existing terraform.tfvars overwritten")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        warning("Interrupted")
        sys.exit(130)
    except Exception as exc:
        fail(str(exc))
