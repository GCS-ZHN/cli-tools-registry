#!/usr/bin/env python
import subprocess
import yaml
from pathlib import Path
import toml
from typing import List, Dict
from packaging.version import InvalidVersion, parse as parse_version

REGISTRY_PATH = Path("registry.yaml")
CLI_PREFIX = "cli-"

def get_modified_clis() -> List[str]:
    """Detect modified CLI directories in the latest commit"""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
        capture_output=True,
        text=True
    )
    modified = set()
    for filepath in result.stdout.splitlines():
        if "/" in filepath:
            dir_name = filepath.split("/")[0]
            if dir_name.startswith(CLI_PREFIX):
                modified.add(dir_name)
    return list(modified)

def get_cli_version(cli_dir: str) -> str:
    """Extract version from pyproject.toml"""
    toml_path = Path(cli_dir) / "pyproject.toml"
    with open(toml_path) as f:
        data = toml.load(f)
    return data["project"]["version"]

def get_current_commit() -> str:
    """Get current commit hash"""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True
    ).strip()

def update_registry(cli_dirs: List[str]):
    """Update registry.yaml with new versions or add new entries"""
    with open(REGISTRY_PATH) as f:
        registry = yaml.safe_load(f) or {"commands": []}
    
    for cli_dir in cli_dirs:
        cli_name = cli_dir[len(CLI_PREFIX):]
        version_str = get_cli_version(cli_dir)
        commit = get_current_commit()
        
        try:
            current_version = parse_version(version_str)
        except InvalidVersion:
            print(f"Invalid version format: {version_str} for {cli_name}")
            continue

        # Find or create entry
        entry = next((c for c in registry["commands"] if c["name"] == cli_name), None)
        if not entry:
            # Create new entry for new CLI
            entry = {
                "name": cli_name,
                "description": "A new CLI tool",  # Default description
                "path": cli_dir,
                "author": "Unknown",  # Default author
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
            raise RuntimeError(f"Version {version_str} for {cli_name} already exists")
        
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

if __name__ == "__main__":
    modified_clis = get_modified_clis()
    try:
        if modified_clis:
            print(f"Updating registry for: {', '.join(modified_clis)}")
            update_registry(modified_clis)
        else:
            raise RuntimeError("No CLI directories modified")
    except Exception as e:
        print(e)
        exit(1)
