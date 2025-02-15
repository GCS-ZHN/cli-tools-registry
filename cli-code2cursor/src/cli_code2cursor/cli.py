# -*- coding: utf-8 -*-
# @Author  : Honi Zhang
# @Email   : zhang.h.n@foxmail.com
# @Time    : 2025-02-15 10:48:40

"""
This module provides a CLI for migrating VSCode to Cursor.
"""

import click
import json5 as json
import appdirs
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional

from cli_code2cursor import utils
from questionary import checkbox
from dataclasses import dataclass, fields


@click.group()
def main():
    """CLI for migrating VSCode extensions to Cursor"""
    pass


def get_extension_dir(app: str) -> Path:
    """Get extensions directory for specified editor"""
    is_remote = utils.is_remote()
    config_dir = utils.find_user_config_dir(app, local=not is_remote)
    return config_dir / "extensions"


def load_extensions(config_dir: Path) -> List[Dict]:
    """Load extensions.json from config directory"""
    extensions_file = config_dir / "extensions.json"
    if not extensions_file.exists():
        return []
    try:
        with open(extensions_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        click.echo(f"⚠️  Error loading extensions: {str(e)}")
        return []


def locate_extension(ext_dir: Path, ext_id: str, version: str) -> Optional[Path]:
    """Find extension installation directory"""
    for entry in ext_dir.iterdir():
        if entry.is_dir() and entry.name.startswith(ext_id):
            if entry.name == f"{ext_id}-{version}" or entry.name.startswith(f"{ext_id}-"):
                return entry
    return None


def save_extensions(config_dir: Path, extensions: List[Dict]) -> bool:
    """Save extensions.json to config directory"""
    extensions_file = config_dir / "extensions.json"
    try:
        with open(extensions_file, 'w', encoding='utf-8') as f:
            json.dump(
                extensions, f, indent=2, 
                ensure_ascii=False, quote_keys=True)
        return True
    except Exception as e:
        click.echo(f"⚠️  Failed to save extensions.json: {str(e)}")
        return False


@main.command()
@click.option('--reverse', '-r', is_flag=True, help='Reverse the migration (Cursor to VSCode)')
def extensions(reverse: bool = False):
    """Migrate extensions from VSCode to Cursor"""
    try:
        # Initialize directories
        if reverse:
            source_app = "cursor"
            target_app = "vscode"
        else:
            source_app = "vscode"
            target_app = "cursor"

        source_dir = get_extension_dir(source_app)
        target_dir = get_extension_dir(target_app)
        target_dir.mkdir(parents=True, exist_ok=True)

        # Load extension manifests
        source_extensions = load_extensions(source_dir)
        target_extensions = load_extensions(target_dir)

        # Filter migratable extensions
        cursor_ids = {e['identifier']['id'] for e in target_extensions}
        migratable = [
            e for e in source_extensions
            if e['identifier']['id'] not in cursor_ids
            and not e['metadata'].get('isBuiltin', False)
        ]

        if not migratable:
            click.echo(f"✅ All extensions already exist in {target_app}")
            return

        # Prepare checklist items
        choices = [
            {
                'name': f"{ext['identifier']['id']} ({ext['version']})",
                'value': ext,
                'checked': True  # Default all selected
            }
            for ext in migratable
        ]

        # Show interactive checklist
        selected = checkbox(
            f"Select extensions to migrate {source_app} to {target_app}:",
            choices=choices,
            instruction="(↑/↓ to move, space to toggle, enter to confirm)"
        ).ask()

        if not selected:
            click.echo(
                f"🚫 Migration canceled for {source_app} to {target_app}")
            return

        # Process selected extensions
        migrated_count = 0
        skipped_count = 0

        for ext in selected:
            ext_id = ext['identifier']['id']
            version = ext['version']

            # Locate source extension
            src_path = locate_extension(source_dir, ext_id, version)
            if not src_path:
                click.echo(f"⚠️  Extension not found: {ext_id} ({version})")
                skipped_count += 1
                continue

            dest_path = target_dir / src_path.name

            # Perform migration
            try:
                if dest_path.exists():
                    click.echo(f"⏩ Already exists: {dest_path.name}")
                    skipped_count += 1
                else:
                    shutil.copytree(src_path, dest_path, symlinks=True)

                    # Create new extension entry
                    new_entry = {
                        "identifier": ext['identifier'],
                        "version": ext['version'],
                        "location": {
                            "$mid": 1,
                            "path": str(dest_path),
                            "scheme": "file"
                        },
                        "relativeLocation": dest_path.name,
                        "metadata": {
                            **ext.get('metadata', {}),
                            "installedTimestamp": int(time.time() * 1000),
                            "updated": False,
                            "pinned": False,
                            "source": "migrated"
                        }
                    }

                    # Update extensions.json
                    target_extensions.append(new_entry)
                    if save_extensions(target_dir, target_extensions):
                        click.echo(f"✅ Success: {dest_path.name}")
                        migrated_count += 1
                    else:
                        click.echo(
                            f"✅ Copied but failed to update registry: {dest_path.name}")
                        skipped_count += 1

            except Exception as e:
                click.echo(f"❌ Failed: {str(e)}")
                skipped_count += 1

        click.echo(
            f"\nMigration result: {migrated_count} succeeded, {skipped_count} skipped")

    except Exception as e:
        click.echo(f"🔥 Critical error: {str(e)}")
        raise click.Abort()


@dataclass
class Snippet:
    group: str
    name: str
    scope: str
    # a list of strings, separated by commas
    prefix: str
    body: List[str]
    description: Optional[str]

    def __eq__(self, other: 'Snippet'):
        if not isinstance(other, Snippet):
            return False
        return all(getattr(self, field.name) == getattr(other, field.name) for field in fields(self))

    def items(self):
        """Return a dictionary of snippet items"""
        data = {
            'scope': self.scope,
            'prefix': self.prefix,
            'body': self.body
        }
        if self.description:
            data['description'] = self.description
        return self.name, self.group, data

    def __repr__(self):
        """Enhanced multi-line representation for conflict resolution"""
        return (
            f"Group: {self.group}\n"
            f"Name:  {self.name}\n"
            f"Scope: {self.scope}\n"
            f"Prefixes: {self.prefix}\n"
            f"Description: {self.description}\n"
            f"Body:\n    " + '\n    '.join(self.body)
        )


def load_snippets(data_dir: Path) -> List[Snippet]:
    snippets = []
    for entry in data_dir.glob("User/snippets/*.code-snippets"):
        with open(entry, 'r', encoding='utf-8') as f:
            click.echo(f"Loading snippets from {entry}")
            data: dict[str, dict] = json.load(f)
            for name, snippet in data.items():
                snippets.append(
                    Snippet(
                        name=name,
                        group=entry.stem,
                        scope=snippet['scope'],
                        prefix=snippet['prefix'],
                        body=snippet['body'],
                        description=snippet.get('description', None),
                    )
                )
    return snippets


def save_snippets(data_dir: Path, snippets: List[Snippet]):
    grouped_snippets = {}
    for snippet in snippets:
        if snippet.group not in grouped_snippets:
            grouped_snippets[snippet.group] = {}
        grouped_snippets[snippet.group][snippet.name] = snippet.items()[2]

    for group, snippets in grouped_snippets.items():
        snippet_file = data_dir / "User/snippets" / f"{group}.code-snippets"
        with open(snippet_file, 'w', encoding='utf-8') as f:
            json.dump(snippets, f, indent=2,
                      ensure_ascii=False, quote_keys=True)


@main.command('snippets')
@click.option('--reverse', '-r', is_flag=True, help='Reverse the migration (Cursor to VSCode)')
def user_snippets(reverse: bool = False):
    """Migrate user snippets from VSCode to Cursor"""
    try:
        # Initialize directories
        if reverse:
            source_app = "cursor"
            source_app_data_dir = "Cursor"
            target_app = "vscode"
            target_app_data_dir = "Code"
        else:
            source_app = "vscode"
            source_app_data_dir = "Code"
            target_app = "cursor"
            target_app_data_dir = "Cursor"

        source_data_dir = Path(appdirs.user_data_dir(
            source_app_data_dir, roaming=True))
        target_data_dir = Path(appdirs.user_data_dir(
            target_app_data_dir, roaming=True))

        # Load snippets from User/snippets
        source_snippets = load_snippets(source_data_dir)
        target_snippets = load_snippets(target_data_dir)

        # Find migratable snippets (not existing in target)
        migratable = [s for s in source_snippets if s not in target_snippets]

        if not migratable:
            click.echo(f"✅ All snippets already exist in {target_app}")
            return

        # Let user select snippets to migrate
        choices = [
            {
                'name': f"{s.group}/{s.name}",
                'value': s,
                'checked': True
            }
            for s in migratable
        ]
        selected = checkbox(
            f"Select snippets to migrate from {source_app} to {target_app}:",
            choices=choices,
            instruction="(↑/↓ to move, space to toggle, enter to confirm)"
        ).ask()

        if not selected:
            click.echo("🚫 Snippet migration canceled")
            return

        # Initialize merged snippets with target's existing snippets
        merged_snippets = target_snippets.copy()
        existing_map = {(s.group, s.name): s for s in merged_snippets}

        # Collect conflict candidates
        conflict_candidates = []
        for s in selected:
            key = (s.group, s.name)
            if key in existing_map:
                conflict_candidates.append({
                    'new': s,
                    'old': existing_map[key],
                    'key': key
                })

        # Batch process conflicts
        to_replace = []
        if conflict_candidates:
            choices = []
            for item in conflict_candidates:
                new = item['new']
                diff = f"[Conflict] {new.group}/{new.name}\n"
                choices.append({
                    'name': diff,
                    'value': item,
                    'checked': False
                })

            to_replace = checkbox(
                "Found conflicts - Select items to overwrite:",
                choices=choices,
                instruction="(Space to toggle, Enter to confirm)"
            ).ask() or []  # Ensure list type

            # Remove selected conflicts from merged list
            for item in to_replace:
                merged_snippets[:] = [s for s in merged_snippets
                                      if (s.group, s.name) != item['key']]

        # Add new snippets (both selected replacements and non-conflict items)
        for s in selected:
            key = (s.group, s.name)
            # Add if:
            # 1. Not in target at all, OR
            # 2. Was selected to be replaced
            if key not in existing_map or key in {x['key'] for x in to_replace}:
                if s not in merged_snippets:
                    merged_snippets.append(s)

        # Save merged snippets
        save_snippets(target_data_dir, merged_snippets)
        click.echo(
            f"✅ Successfully migrated {len(selected)} snippets to {target_app}")

    except Exception as e:
        click.echo(f"🔥 Critical error: {str(e)}")
        raise click.Abort()
