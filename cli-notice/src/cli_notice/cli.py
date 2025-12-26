import click
import yaml

from .bot import FeishuBot
from appdirs import user_config_dir
from pathlib import Path

config_home = Path(user_config_dir('cli-notice'))
config_home.mkdir(parents=True, exist_ok=True)
config_file = config_home / 'config.yaml'


def _configure(suffix: str = ''):
    config = {}
    while not (webhook_url := click.prompt(
        f'Webhook url{suffix}').strip()).startswith('https://'):
        click.echo('Invalid webhook url', err = True)
    
    config['webhook_url'] = webhook_url

    if (signature_secret := click.prompt(
        f'Signature secret{suffix}, [optional]',
        hide_input=True,
        default='').strip()):
        config['signature_secret'] = signature_secret

    return config


def flush_config(config: dict):
    with open(config_file, 'wt') as f:
        yaml.dump(config, f)


@click.command()
@click.argument('message', nargs=-1, required=True)
@click.option('--bot-type', '-b',
              default='feishu',
              type=click.Choice(['feishu']),
              help='Bot type',
              show_default=True)
@click.option('--at', '-a',
              multiple=True,
              help='User id to at')
@click.option('--update-config', '-u',
              is_flag=True,
              help='Force update config')
def notice(
    message: tuple[str],
    bot_type: str = 'feishu',
    at: tuple[str] = tuple(),
    update_config: bool = False):
    message = ' '.join(message)
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    bot_config:dict = config.setdefault('bots', {}).setdefault(bot_type, {})
    if not bot_config.get('webhook_url') or update_config:
        bot_config.update(_configure(f' for {bot_type} Bot'))
        flush_config(config)

    if bot_type == 'feishu':
        bot = FeishuBot(**bot_config)
    else:
        click.echo(f'Unsupport bot type {bot_type}', err=True)
        exit(1)
    try:
        bot.send_message(message, at=at)
    except Exception as e:
        click.echo(f'Failed to send message: {e}', err=True)
        exit(1)
    click.echo('Message sent')

