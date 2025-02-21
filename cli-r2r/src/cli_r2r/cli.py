import os
import click
import paramiko
from typing import Tuple, Optional, Generator
from contextlib import contextmanager
from paramiko import SSHClient, SFTPClient
from paramiko.config import SSHConfig
from tqdm import tqdm


def resolve_host_config(host_alias: str) -> Tuple[str, Optional[str], int, Optional[str]]:
    """Resolve host configuration from SSH config with fallback"""
    config_path = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(config_path):
        return host_alias, None, 22, None

    with open(config_path) as f:
        config = SSHConfig()
        config.parse(f)
        host_config = config.lookup(host_alias)

    resolved_host = host_config.get('hostname', host_alias)
    user = host_config.get('user')
    port = int(host_config.get('port', 22))
    identity_files = host_config.get('identityfile', [])
    identity_file = identity_files[0] if identity_files else None
    
    return resolved_host, user, port, identity_file


@contextmanager
def sftp_connection(
    host_alias: str,
    username: Optional[str] = None,
    port: int = 22,
    identity_file: Optional[str] = None
) -> Generator[SFTPClient, None, None]:
    """Context manager for SFTP connection with authentication handling"""
    resolved_host, config_user, config_port, config_identity = resolve_host_config(host_alias)
    
    # Apply configuration precedence: CLI args > SSH config
    final_username = username or config_user
    final_port = port if port != 22 else config_port
    final_identity = identity_file or config_identity
    
    if not final_username:
        raise click.UsageError(f"Username required for {host_alias}")

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Handle authentication
        password = None
        used_identity = None
        
        if final_identity:
            expanded_identity = os.path.expanduser(final_identity)
            if os.path.exists(expanded_identity):
                used_identity = expanded_identity
            else:
                click.echo(f"⚠️ Identity file '{final_identity}' not found")
                password = click.prompt(
                    f"Enter password for {final_username}@{resolved_host}",
                    hide_input=True
                )
        else:
            password = click.prompt(
                f"Enter password for {final_username}@{resolved_host}",
                hide_input=True
            )

        ssh.connect(
            hostname=resolved_host,
            port=final_port,
            username=final_username,
            key_filename=used_identity,
            password=password,
            look_for_keys=False,
            timeout=10
        )
        
        sftp = ssh.open_sftp()
        yield sftp
        
    except paramiko.AuthenticationException as e:
        raise click.ClickException(f"Authentication failed: {str(e)}")
    except Exception as e:
        raise click.ClickException(f"Connection error: {str(e)}")
    finally:
        sftp.close() if 'sftp' in locals() else None
        ssh.close()


def transfer_stream(
    sftp_src: SFTPClient,
    sftp_dst: SFTPClient,
    src_path: str,
    dst_path: str
) -> None:
    """Stream data between SFTP connections with progress tracking"""
    with sftp_src.open(src_path, 'rb') as remote_file:
        file_size = sftp_src.stat(src_path).st_size
        with tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Transferring {os.path.basename(src_path)}"
        ) as bar:
            with sftp_dst.open(dst_path, 'wb') as remote_dst_file:
                while True:
                    data = remote_file.read(32768)  # 32KB chunks
                    if not data:
                        break
                    remote_dst_file.write(data)
                    bar.update(len(data))


@click.group()
def cli() -> None:
    """Secure file bridge between remote servers"""
    pass


@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
@click.option('--username-src', default=None, help='Override source username')
@click.option('--username-dst', default=None, help='Override destination username')
@click.option('--port-src', default=22, help='Source SSH port (default: 22)')
@click.option('--port-dst', default=22, help='Destination SSH port (default: 22)')
@click.option('--identity-src', default=None, help='Path to source private key')
@click.option('--identity-dst', default=None, help='Path to destination private key')
@click.option('--stream/--buffer', default=True, help='Transfer mode (default: stream)')
def bridge(
    src: str,
    dst: str,
    username_src: Optional[str],
    username_dst: Optional[str],
    port_src: int,
    port_dst: int,
    identity_src: Optional[str],
    identity_dst: Optional[str],
    stream: bool
) -> None:
    """Transfer files between remote hosts"""
    try:
        src_host, src_path = src.split(':', 1)
        dst_host, dst_path = dst.split(':', 1)
    except ValueError:
        raise click.UsageError("Invalid format, use HOST_ALIAS:/path/to/file")

    try:
        with sftp_connection(
            host_alias=src_host,
            username=username_src,
            port=port_src,
            identity_file=identity_src
        ) as sftp_src, \
        sftp_connection(
            host_alias=dst_host,
            username=username_dst,
            port=port_dst,
            identity_file=identity_dst
        ) as sftp_dst:

            if stream:
                transfer_stream(sftp_src, sftp_dst, src_path, dst_path)
            else:
                with sftp_src.open(src_path, 'rb') as f_src:
                    data = f_src.read()
                with sftp_dst.open(dst_path, 'wb') as f_dst:
                    f_dst.write(data)

            click.echo(f"✅ Transferred {src} ➔ {dst}")

    except Exception as e:
        click.echo(f"❌ Transfer failed: {e}")
        raise click.Abort()


@cli.command()
def version() -> None:
    """Show version information"""
    from cli_r2r import __version__
    click.echo(f"r2r {__version__}")


if __name__ == '__main__':
    cli()
