"""Losslessly split/restore the original wide monthly CSV for GitHub uploads."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pack(source, target, rows=2500):
    target.mkdir(parents=True, exist_ok=True)
    if list(target.glob('part-*.csv.gz')):
        raise ValueError('Target already contains shards. Use an empty directory.')
    parts = []
    with source.open('rb') as f:
        header = f.readline()
        index = 0
        while True:
            lines = [f.readline() for _ in range(rows)]
            lines = [line for line in lines if line]
            if not lines:
                break
            index += 1
            path = target / f'part-{index:03d}.csv.gz'
            with path.open('wb') as raw:
                with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as z:
                    z.write(header)
                    z.writelines(lines)
            if path.stat().st_size >= 25 * 1024**2:
                raise ValueError('Shard exceeds browser upload limit; use fewer rows.')
            parts.append(dict(file=path.name, rows=len(lines), bytes=path.stat().st_size,
                              sha256=sha256(path)))
    manifest = dict(source_name=source.name, source_bytes=source.stat().st_size,
                    source_sha256=sha256(source), rows=sum(x['rows'] for x in parts),
                    columns=len(header.decode().strip().split(',')), parts=parts)
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Packed {manifest["rows"]:,} rows into {len(parts)} lossless shards')


def restore(source, output):
    manifest = json.loads((source / 'manifest.json').read_text())
    if output.exists():
        raise ValueError('Output exists; choose a new output path.')
    output.parent.mkdir(parents=True, exist_ok=True)
    header = None
    with output.open('wb') as out:
        for entry in manifest['parts']:
            path = source / entry['file']
            if sha256(path) != entry['sha256']:
                raise ValueError(f'Checksum mismatch: {path}')
            with gzip.open(path, 'rb') as f:
                current = f.readline()
                if header is None:
                    header = current
                    out.write(header)
                elif header != current:
                    raise ValueError('Inconsistent shard headers')
                for line in f:
                    out.write(line)
    if sha256(output) != manifest['source_sha256']:
        raise ValueError('Restored CSV checksum mismatch')
    print('Restored original CSV byte for byte:', output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('pack')
    a.add_argument('source', type=Path)
    a.add_argument('target', type=Path)
    a.add_argument('--rows', type=int, default=2500)
    b = sub.add_parser('restore')
    b.add_argument('source', type=Path)
    b.add_argument('output', type=Path)
    args = p.parse_args()
    if args.command == 'pack':
        if args.rows < 1:
            p.error('--rows must be positive')
        pack(args.source, args.target, args.rows)
    else:
        restore(args.source, args.output)
