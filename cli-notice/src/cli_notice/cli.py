import click
import yaml
import ast

from .bot import FeishuBot, DingTalkBot
from appdirs import user_config_dir
from pathlib import Path

config_home = Path(user_config_dir('cli-notice'))
config_home.mkdir(parents=True, exist_ok=True)
config_file = config_home / 'config.yaml'


def _configure(suffix: str = ''):
    config = {}
    while not (webhook_url_or_token := click.prompt(
        f'Webhook url or access token{suffix}').strip()):
        click.echo('Webhook url or access token cannot be empty')
    if webhook_url_or_token.startswith('https://'):
        config['webhook_url'] = webhook_url_or_token
    else:
        config['access_token'] = webhook_url_or_token

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
              type=click.Choice(['feishu', 'dingtalk']),
              help='Bot type',
              show_default=True)
@click.option('--at', '-a',
              multiple=True,
              help='User id to at')
@click.option('--update-config', '-u',
              is_flag=True,
              help='Force update config')
@click.option('--escape', '-e',
              is_flag=True,
              help='Enable interpretation of backslash escapes')
def notice(
    message: tuple[str],
    bot_type: str = 'feishu',
    at: tuple[str] = tuple(),
    update_config: bool = False,
    escape: bool = False):
    message = ' '.join(message)
    if escape:
        message = ast.literal_eval('"' + message + '"')
    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    bot_config:dict = config.setdefault('bots', {}).setdefault(bot_type, {})
    if not (bot_config.get('webhook_url') or bot_config.get('access_token')) or update_config:
        bot_config.clear()
        bot_config.update(_configure(f' for {bot_type} Bot'))
        flush_config(config)

    print(config_file)
    if bot_type == 'feishu':
        bot = FeishuBot(**bot_config)
    elif bot_type == 'dingtalk':
        bot = DingTalkBot(**bot_config)
    else:
        click.echo(f'Unsupport bot type {bot_type}', err=True)
        exit(1)
    try:
        bot.send_message(message, at=at)
    except Exception as e:
        click.echo(f'Failed to send message: {e}', err=True)
        exit(1)
    click.echo('Message sent')

