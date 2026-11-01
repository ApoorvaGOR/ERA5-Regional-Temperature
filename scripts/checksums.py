"""Write or verify the repository SHA-256 inventory using only Python's standard library."""
import argparse
from pathlib import Path

from package_monthly import sha256

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', '__pycache__', 'work', '.pytest_cache'}


def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and
                  not (set(p.relative_to(root).parts) & IGNORED) and
                  p.name not in {'checksums.sha256', '.DS_Store'} and
                  p.suffix not in {'.pyc', '.zip'})


def run(root, write=False):
    inventory = root / 'checksums.sha256'
    if write:
        inventory.write_text(''.join(f'{sha256(p)}  {p.relative_to(root).as_posix()}\n' for p in files(root)))
        print('Updated', inventory)
        return
    checked = set()
    for line in inventory.read_text().splitlines():
        digest, name = line.split('  ', 1)
        if sha256(root / name) != digest:
            raise ValueError(f'Checksum mismatch: {name}')
        checked.add(name)
    expected = {p.relative_to(root).as_posix() for p in files(root)}
    if checked != expected:
        raise ValueError(f'Inventory coverage mismatch: {checked.symmetric_difference(expected)}')
    print(f'All {len(checked)} file checksums match')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--write', action='store_true', help='Regenerate after intentional repository changes')
    a = p.parse_args()
    run(a.root, a.write)
