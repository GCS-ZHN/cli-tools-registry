#!/usr/bin/env python
import subprocess
import yaml
from pathlib import Path
import toml
from typing import List
from packaging.version import InvalidVersion, parse as parse_version
import argparse
import tempfile
import os
import sys

REGISTRY_PATH = Path("registry.yaml")
CLI_PREFIX = "cli-"


def git_rev_parse(head: str) -> str:
    """Get commit hash"""
    return subprocess.check_output(
        ["git", "rev-parse", head],
        text=True
    ).strip()


def get_modified_clis(before_sha: str, after_sha: str) -> List[str]:
    """Detect modified CLI directories between two commits"""
    # Handle empty before_sha (fallback to HEAD~1)
    if not before_sha.strip():
        before_sha = git_rev_parse("HEAD~1")

    # Handle empty after_sha (use current HEAD)
    if not after_sha.strip():
        after_sha = git_rev_parse("HEAD")

    result = subprocess.run(
        ["git", "diff", "--name-only", before_sha, after_sha],
        capture_output=True,
        text=True,
    )
    try:
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        print(result.stderr)
        raise e

    modified = set()
    for filepath in result.stdout.splitlines():
        if "/" in filepath:
            dir_name = filepath.split("/")[0]
            if dir_name.startswith(CLI_PREFIX):
                modified.add(dir_name)
    return list(modified)


def get_cli_info(cli_dir: str) -> str:
    """Extract version from pyproject.toml"""
    toml_path = Path(cli_dir) / "pyproject.toml"
    with open(toml_path) as f:
        data = toml.load(f)
    return {
        'description': data["project"]["description"],
        'version': data["project"]["version"],
        'authors': [dict(a) for a in data["project"]["authors"]]
    }


def update_registry(cli_dirs: List[str], commit_sha: str):
    """Update registry.yaml with new versions or add new entries"""
    with open(REGISTRY_PATH) as f:
        registry = yaml.safe_load(f) or {"commands": []}
    
    for cli_dir in cli_dirs:
        cli_name = cli_dir[len(CLI_PREFIX):]
        cli_info = get_cli_info(cli_dir)
        version_str = cli_info['version']
        commit = commit_sha
        
        try:
            current_version = parse_version(version_str)
        except InvalidVersion:
            print(f"Invalid version format: {version_str} for {cli_name}")
            continue

        # Find or create entry
        if "commands" not in registry:
            registry['commands'] = []

        entry = next((c for c in registry["commands"] if c["name"] == cli_name), None)

        if not entry:
            # Create new entry for new CLI
            entry = {
                "name": cli_name,
                "description": cli_info['description'],
                "path": cli_dir,
                "authors": cli_info['authors'],
                "latest": version_str,
                "versions": []
            }
            registry["commands"].append(entry)
            print(f"Added new CLI entry: {cli_name}")
        
        # Add new version record
        new_version = {"version": version_str, "commit": commit}
        existing_versions = [parse_version(v["version"]) for v in entry["versions"]]
        
        if current_version not in existing_versions:
            entry["versions"].append(new_version)
            print(f"Added version {version_str} for {cli_name}")
            
            # Sort versions in descending order
            entry["versions"].sort(
                key=lambda x: parse_version(x["version"]),
                reverse=True
            )
        else:
            print(f"Version {version_str} for {cli_name} already exists")
            continue

        # Update latest version using proper version comparison
        latest_version = parse_version(entry["latest"])
        if current_version > latest_version:
            entry["latest"] = version_str
            print(f"Updated latest version to {version_str} for {cli_name}")

    with open(REGISTRY_PATH, "w") as f:
        yaml.dump(
            registry, 
            f, 
            sort_keys=False, 
            allow_unicode=True,
            indent=4)


def validate_cli_installation(cli_dirs: str):
    """Validate CLI installation via pipx with proper path handling"""
    
    with tempfile.TemporaryDirectory(prefix=f"pipx-home-") as pipx_dir:
        env = os.environ.copy()
        env['PIPX_HOME'] = pipx_dir
        env['PIPX_BIN_DIR'] = f'{pipx_dir}/bin'
        for cli_dir in cli_dirs:
            cli_name = cli_dir[len(CLI_PREFIX):]
            try:
                install_cmd = (
                    f"pipx install --python {sys.executable} --force ./{cli_dir} "
                    f" && "
                    f"pipx run --spec ./{cli_dir} {cli_name} --help"
                )
                result = subprocess.run(
                    install_cmd,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True,
                    executable="/bin/bash",
                    env=env
                )
                
                print(f"✅ Successfully validated {cli_name}\n{result.stdout}")
                
            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"Validation failed for {cli_name}\n"
                    f"Command: {e.cmd}\n"
                    f"Exit code: {e.returncode}\n"
                    f"STDOUT: {e.stdout}\n"
                    f"STDERR: {e.stderr}"
                )
                raise RuntimeError(error_msg) from e
            finally:
                # 确保清理安装
                subprocess.run(
                    f"pipx uninstall {cli_name}",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update CLI registry')
    parser.add_argument('--check-cli', action='store_true', help='Validate CLI installations')
    parser.add_argument(
        '--before',
        default=git_rev_parse("HEAD~1"),
        help='Previous commit SHA (default: HEAD~1)')
    parser.add_argument(
        '--after',
        default=git_rev_parse("HEAD"),
        help='Current commit SHA (default: HEAD)')
    args = parser.parse_args()

    try:
        modified_clis = get_modified_clis(args.before, args.after)
        if modified_clis:
            print(f"Updating registry for: {', '.join(modified_clis)}")
            
            if args.check_cli:
                print("Validating CLI installations...")
                validate_cli_installation(modified_clis)
            
            update_registry(modified_clis, args.after)
        else:
            print("No CLI directories modified")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
