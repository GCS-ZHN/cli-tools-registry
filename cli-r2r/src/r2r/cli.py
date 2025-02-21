import os
from paramiko.config import SSHConfig
import click

def load_ssh_config(hostname, use_ssh_config):
    if not use_ssh_config:
        return hostname, None, 22, None  # 添加第四个返回值用于密钥
    
    config_path = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(config_path):
        return hostname, None, 22, None
    
    with open(config_path) as f:
        config = SSHConfig()
        config.parse(f)
        host_config = config.lookup(hostname)
        
    hostname = host_config.get('hostname', hostname)
    user = host_config.get('user')
    port = int(host_config.get('port', 22))
    identity_file = host_config.get('identityfile', [None])[0]  # 获取第一个密钥文件
    if identity_file:
        identity_file = os.path.expanduser(identity_file)  # 处理~扩展
    return hostname, user, port, identity_file  # 返回密钥路径

@cli.command()
@click.argument('src', required=True)
@click.argument('dst', required=True)
@click.option('--username-src', default=None, help='Source host username (覆盖SSH配置)')
@click.option('--username-dst', default=None, help='Destination host username (覆盖SSH配置)')
@click.option('--port-src', default=22, help='Source host SSH port (默认22)')
@click.option('--port-dst', default=22, help='Destination host SSH port (默认22)')
@click.option('--key-src', default=None, help='手动指定源端密钥路径')  # 新增密钥选项
@click.option('--key-dst', default=None, help='手动指定目标端密钥路径')  # 新增密钥选项
@click.option('--use-ssh-config', is_flag=True, help='使用~/.ssh/config配置')
@click.option('--stream/--buffer', default=True, help='传输模式: 流式(默认)或缓冲')
def bridge(src, dst, 
          username_src, username_dst, port_src, port_dst,
          key_src, key_dst,  # 新增密钥参数
          use_ssh_config, stream):
    # ... [保留之前的参数解析代码]
    
    # 解析SSH配置时获取密钥路径
    src_hostname, src_user_conf, src_port_conf, src_key_conf = load_ssh_config(src_host, use_ssh_config)
    dst_hostname, dst_user_conf, dst_port_conf, dst_key_conf = load_ssh_config(dst_host, use_ssh_config)
    
    # 确定最终使用的密钥路径（命令行参数优先）
    key_src_final = key_src or src_key_conf
    key_dst_final = key_dst or dst_key_conf

    # 修改SSH连接逻辑
    try:
        # 带密钥的连接方式
        ssh_src.connect(src_hostname, 
                       port=port_src, 
                       username=username_src,
                       key_filename=key_src_final)  # 添加密钥参数
        
        ssh_dst.connect(dst_hostname,
                       port=port_dst,
                       username=username_dst,
                       key_filename=key_dst_final)  # 添加密钥参数
    # ... [保留后续代码] 