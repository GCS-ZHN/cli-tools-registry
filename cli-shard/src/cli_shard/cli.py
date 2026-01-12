import pandas as pd
from pathlib import Path
from protools import seqio
import click


def binary_split(file: Path, output_dir: Path, num_shard: int):
    """
    Split a binary file into multiple shards (similar to Linux split command)
    """
    stat_size = file.stat().st_size
    chunk_size = stat_size // num_shard
    output_dir.mkdir(parents=True, exist_ok=True)
    max_buffer_size = 1<<17 # 128k
    with open(file, 'rb') as f:
        for i in range(num_shard):
            with open(output_dir / f'shard_{i}.bin', 'wb') as w:
                if i < num_shard - 1:
                    read_size = 0
                    while read_size < chunk_size: 
                        buffer_len = min(max_buffer_size, chunk_size - read_size)
                        buffer = f.read(buffer_len)
                        assert len(buffer) == buffer_len
                        w.write(buffer)
                        read_size += buffer_len
                    
                    assert read_size == chunk_size
                else:
                    for buffer in iter(lambda: f.read(max_buffer_size), b''):
                        w.write(buffer)

@click.command()
@click.option(
    '--input_file', '-i',
    type=click.Path(exists=True, resolve_path=True, path_type=Path),
    required=True,
    help="Input file path (supported formats: csv/tsv/xlsx/xls/txt/pkl)"
)
@click.option(
    '--output_dir', '-o',
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    required=True,
    help="Output directory path (Automatically creates if not exists)"
)
@click.option(
    '--num_shard', '-n',
    type=click.IntRange(min=1),
    required=True,
    help="Number of shards (must be ≥ 1)"
)
@click.option(
    '--shuffle', '-s',
    is_flag=True,
    help="Enable data shuffling before sharding"
)
def shard(input_file: Path, output_dir: Path, num_shard: int, shuffle: bool = False) -> None:
    """
    Command-line tool for splitting large data files into multiple shards.

    Key Features:
    1. Automatic format detection based on file extension
    2. Ensures data integrity (last shard contains all remaining rows)

    Usage Example:
    shard -i data.csv -o outputs/ -n 8 --shuffle
    """

    file_read = {
        '.txt': pd.read_table,
        '.tsv': pd.read_table,
        '.csv': pd.read_csv,
        '.pkl': pd.read_pickle,
        '.xlsx': pd.read_excel,
        '.xls': pd.read_excel,
        '.fasta': lambda x: seqio.read_fasta(x).to_dataframe()[['id', 'sequence']],
    }

    file_ext = input_file.suffix
    if file_ext in file_read:
        df: pd.DataFrame = file_read[file_ext](input_file)
    else:
        click.echo('Unknown file type detected, binary splitting in order(not shuffled).')
        binary_split(input_file, output_dir, num_shard)
        return
    
    if shuffle:
        df = df.sample(frac=1).reset_index(drop=True)
    
    shard_size = len(df) // num_shard
    assert shard_size > 0, "Number of shards is too large for the input file."
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(num_shard):
        start = i * shard_size
        end = (i + 1) * shard_size
        if i == num_shard - 1:
            end = len(df)
        shard_df = df.iloc[start:end]
        shard_df.to_csv(output_dir / f"shard_{i}.csv", index=False)


if __name__ == "__main__":
    shard()
