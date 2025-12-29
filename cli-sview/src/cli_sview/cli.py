import subprocess
import json
import shutil
import click

from prettytable import PrettyTable


def convert_memory(mem_mb):
    units = ["MB", "GB", "TB"]
    size = float(mem_mb)
    for unit in units:
        if size < 1024:
            return f"{size:.2f}{unit}"
        size /= 1024
    return f"{size:.2f}PB"


def get_sinfo_from_json(sinfo_bin: str, node: str = None, partition: str = None):
    try:
        cmds = [sinfo_bin, '-N', '--json']
        if node:
            cmds.extend(['-n', node])
        if partition:
            cmds.extend(['-p', partition])
        result = subprocess.run(
            cmds,
            capture_output=True,
            text=True,
            check=True)
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Excutate command: {e.cmd} failed\n"
            f"Exit code: {e.returncode}\n"
            f"STDOUT: {e.stdout}\n"
            f"STDERR: {e.stderr}"
        )
        raise RuntimeError(error_msg) from e

    output = result.stdout

    data = json.loads(output)

    table = PrettyTable()
    table.field_names = ["NODELIST", "PARTITION", "CPUS(A/I/O/T)", "GRES_USED", "GRES_TOTAL", "MEMORY", "FREEMEM"]

    for node_info in data['sinfo']:
        node_name = node_info['nodes']['nodes'][0]
        cpus = f"{node_info['cpus']['allocated']}/{node_info['cpus']['idle']}/{node_info['cpus']['other']}/{node_info['cpus']['total']}"
        gres_used = node_info['gres']['used']
        gres_total = node_info['gres']['total']
        partition_name = node_info['partition']['name']
        memory = convert_memory(node_info['memory']['minimum'])
        free_mem = convert_memory(node_info['memory']['free']['minimum']['number'])
        table.add_row([node_name, partition_name, cpus, gres_used, gres_total, memory, free_mem])

    print(table)


def get_sinfo_from_default(sinfo_bin: str, node: str = None, partition: str = None):
    try:
        query_args = [
            'NodeList',
            'Partition',
            'CPUsState',
            'GresUsed',
            'Gres',
            'Memory',
            'FreeMem'
        ]
        cmds = [
            sinfo_bin,
            '-N',
            '-O', '|,'.join(x + ':.' for x in query_args)
        ]
        if partition:
            cmds.extend(['-p', partition])
        if node:
            cmds.extend(['-n', node])
        result = subprocess.run(
            cmds,
            capture_output=True,
            text=True,
            check=True)
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Excutate command: {e.cmd} failed\n"
            f"Exit code: {e.returncode}\n"
            f"STDOUT: {e.stdout}\n"
            f"STDERR: {e.stderr}"
        )
        raise RuntimeError(error_msg) from e

    output = result.stdout
    cols: list[str] = None
    data: list[dict[str, str]] = []
    for i, line in enumerate(output.splitlines()):
        line = list(map(str.strip, line.split('|')))
        if i == 0:
            cols = line
        else:
            assert len(cols) == len(line)
            data.append(dict(zip(cols, line)))

    table = PrettyTable()
    table.field_names = ["NODELIST", "PARTITION", "CPUS(A/I/O/T)", "GRES_USED", "GRES_TOTAL", "MEMORY", "FREEMEM"]
    for row in data:
        node_name = row['NODELIST']
        partition_name = row['PARTITION']
        cpus = row['CPUS(A/I/O/T)']
        gres_used = row['GRES_USED']
        gres_total = row['GRES']
        memory = convert_memory(row['MEMORY'])
        free_mem = convert_memory(row['FREE_MEM'])

        table.add_row([node_name, partition_name, cpus, gres_used, gres_total, memory, free_mem])

    print(table)


@click.command()
@click.option(
    '--node', '-n',
    type=click.STRING,
    help='If provided, query it only'
)
@click.option(
    '--partition', '-p',
    type=click.STRING,
    help='If provided, query it only')
def sview(node: str = None, partition: str = None):
    """
    Pretty view for available resources in Slurm.
    """
    if node and partition:
        print('Cannot specify both node and partition!')
        exit(1)
    sinfo_bin = shutil.which('sinfo')
    if sinfo_bin is None:
        print('Please install slurm first!')
        exit(1)

    for method in (get_sinfo_from_json, get_sinfo_from_default):
        try:
            method(sinfo_bin, node, partition)
            break
        except Exception as e:
            err = e
    else:
        print(err.__class__.__name__, ':', str(err))
        exit(1)


if __name__ == "__main__":
    sview()