import subprocess
import json
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


@click.command()
def sview():
    """
    Pretty view for available resources in Slurm.
    """
    try:
        result = subprocess.run(
            ['sinfo', '-N', '--json'],
            capture_output=True,
            text=True,
            check=True,
            shell=True)
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Excutate command: {e.cmd} failed\n"
            f"Exit code: {e.returncode}\n"
            f"STDOUT: {e.stdout}\n"
            f"STDERR: {e.stderr}"
        )
        print(error_msg)
        exit(1)

    output = result.stdout

    data = json.loads(output)

    table = PrettyTable()
    table.field_names = ["NODELIST", "CPUS(A/I/O/T)", "GRES_USED", "GRES_TOTAL", "MEMORY", "FREEMEM"]

    for node_info in data['sinfo']:
        node_name = node_info['nodes']['nodes'][0]
        cpus = f"{node_info['cpus']['allocated']}/{node_info['cpus']['idle']}/{node_info['cpus']['other']}/{node_info['cpus']['total']}"
        gres_used = node_info['gres']['used']
        gres_total = node_info['gres']['total']
        memory = convert_memory(node_info['memory']['minimum'])
        free_mem = convert_memory(node_info['memory']['free']['minimum']['number'])
        table.add_row([node_name, cpus, gres_used, gres_total, memory, free_mem])

    print(table)


if __name__ == "__main__":
    sview()