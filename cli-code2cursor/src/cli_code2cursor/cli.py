import click
import json
import shutil
import time
from pathlib import Path
from typing import List, Dict, Optional

from cli_code2cursor import utils


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
            json.dump(extensions, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        click.echo(f"⚠️  Failed to save extensions.json: {str(e)}")
        return False


@main.command()
def extensions():
    """Migrate extensions from VSCode to Cursor"""
    try:
        # Initialize directories
        vscode_dir = get_extension_dir("vscode")
        cursor_dir = get_extension_dir("cursor")
        cursor_dir.mkdir(parents=True, exist_ok=True)

        # Load extension manifests
        vscode_extensions = load_extensions(vscode_dir)
        cursor_extensions = load_extensions(cursor_dir)
        
        # Filter migratable extensions
        cursor_ids = {e['identifier']['id'] for e in cursor_extensions}
        migratable = [
            e for e in vscode_extensions
            if e['identifier']['id'] not in cursor_ids
            and not e['metadata'].get('isBuiltin', False)
        ]

        if not migratable:
            click.echo("✅ All extensions already exist in Cursor")
            return

        click.echo(f"🔍 Found {len(migratable)} migratable extensions")
        migrated_count = 0
        skipped_count = 0

        for ext in migratable:
            ext_id = ext['identifier']['id']
            version = ext['version']
            
            # Locate source extension
            src_path = locate_extension(vscode_dir, ext_id, version)
            if not src_path:
                click.echo(f"⚠️  Extension not found: {ext_id} ({version})")
                skipped_count += 1
                continue

            dest_path = cursor_dir / src_path.name
            
            # Interactive prompt
            choice = click.prompt(
                f"\nMigrate {ext_id} ({version})?",
                type=click.Choice(['y', 'n', 'a', 'q'], case_sensitive=False),
                default='y',
                show_choices=True,
                prompt_suffix=" (Y)es/(N)o/(A)ll/(Q)uit "
            ).lower()

            if choice == 'q':
                break
            if choice == 'n':
                skipped_count += 1
                continue
            if choice == 'a':
                auto_migrate = True

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
                    cursor_extensions.append(new_entry)
                    if save_extensions(cursor_dir, cursor_extensions):
                        click.echo(f"✅ Success: {dest_path.name}")
                        migrated_count += 1
                    else:
                        click.echo(f"✅ Copied but failed to update registry: {dest_path.name}")
                        skipped_count += 1

            except Exception as e:
                click.echo(f"❌ Failed: {str(e)}")
                skipped_count += 1

        click.echo(f"\nMigration result: {migrated_count} succeeded, {skipped_count} skipped")

    except Exception as e:
        click.echo(f"🔥 Critical error: {str(e)}")
        raise click.Abort()


if __name__ == "__main__":
    main()
