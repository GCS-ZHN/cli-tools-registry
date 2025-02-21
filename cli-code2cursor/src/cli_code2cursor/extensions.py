# -*- coding: utf-8 -*-
# @Author  : Honi Zhang
# @Email   : zhang.h.n@foxmail.com
# @Time    : 2025-02-18 16:12:42

"""
Extensions management
"""

import json5 as json

from dataclasses import dataclass, field
from dataclasses_json import DataClassJsonMixin, LetterCase, cfg, config
from pathlib import Path
from typing import List, Optional
from cli_code2cursor import utils

# make Path serializable globally
cfg.global_config.encoders[Path] = str
cfg.global_config.decoders[Path] = Path


# config as CamelCase, exclude None fields
class CustomDataClassJsonMixin(DataClassJsonMixin):
    dataclass_json_config = config(
        letter_case=LetterCase.CAMEL,
        exclude=lambda f: f is None)['dataclasses_json']


@dataclass
class ExtensionIdentifier(CustomDataClassJsonMixin):
    id: str
    uuid: Optional[str] = field(default=None)


@dataclass
class ExtensionLocation(CustomDataClassJsonMixin):
    mid: int = field(metadata=config(field_name='$mid'))
    path: Path
    scheme: str


@dataclass
class ExtensionMetadata(CustomDataClassJsonMixin):
    id: str
    publisher_id: str
    publisher_display_name: str
    target_platform: str
    updated: bool # is latest version
    is_pre_release_version: bool
    has_pre_release_version: bool
    installed_timestamp: int
    source: str
    pinned: bool = field(default=False) # is version pinned
    is_builtin: bool = field(default=False)


@dataclass
class Extension(CustomDataClassJsonMixin):
    identifier: ExtensionIdentifier
    version: str
    location: ExtensionLocation
    relative_location: str
    metadata: ExtensionMetadata


def get_extension_dir(app: str) -> Path:
    """Get extensions directory for specified editor"""
    is_remote = utils.is_remote()
    config_dir = utils.find_user_config_dir(app, local=not is_remote)
    return config_dir / "extensions"


def load_extensions(config_dir: Path) -> List[Extension]:
    """Load extensions.json from config directory"""
    extensions_file = config_dir / "extensions.json"
    if not extensions_file.exists():
        return []

    with open(extensions_file, 'r', encoding='utf-8') as f:
        return [Extension.from_dict(ext) for ext in json.load(f)]


def save_extensions(config_dir: Path, extensions: List[Extension]):
    """Save extensions.json to config directory"""
    extensions_file = config_dir / "extensions.json"
    with open(extensions_file, 'w', encoding='utf-8') as f:
        json.dump(
            [ext.to_dict() for ext in extensions], f,
            ensure_ascii=False,
            quote_keys=True,
            indent=None,
            separators=(',', ':')
        )


if __name__ == '__main__':
    extensions = load_extensions(get_extension_dir('vscode'))
    save_extensions(Path.cwd(), extensions)
