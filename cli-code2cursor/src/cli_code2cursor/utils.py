import os

from pathlib import Path


def is_remote() -> bool:
    """
    Check if the current environment is a remote connection (e.g., SSH) in vscode/cursor.

    Returns:
        bool: True if the environment is remote, False otherwise.
    """
    return 'SSH_CONNECTION' in os.environ or 'SSH_CLIENT' in os.environ


def find_user_config_dir(app: str = 'vscode', local: bool = True) -> Path:
    """
    Get the user configuration directory for vscode or cursor.

    Args:
        app (str): The application name, either 'vscode' or 'cursor'. Defaults to 'vscode'.
        local (bool): Whether to get the local configuration directory. Defaults to True.

    Returns:
        Path: The path to the user configuration directory.
    """
    home_dir = Path.home()
    assert app in ('vscode', 'cursor')
    if local:
        config_dir = home_dir / f".{app}"
    else:
        config_dir = home_dir / f".{app}-server"
    
    return config_dir
