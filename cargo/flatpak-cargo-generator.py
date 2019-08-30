#!/usr/bin/env python3

__license__ = 'MIT'

import toml
import json
from urllib.parse import quote as urlquote
import sys
import argparse

CRATES_IO = 'https://static.crates.io/crates'
CARGO_HOME = 'cargo'
CARGO_CRATES = f'{CARGO_HOME}/vendor'

def load_cargo_lock(lockfile='Cargo.lock'):
    with open(lockfile, 'r') as f:
        cargo_lock = toml.load(f)
    return cargo_lock

def generate_sources(cargo_lock):
    sources = [{
        'type': 'file',
        'url': 'data:' + urlquote(toml.dumps({
            'source': {
                'crates-io': {'replace-with': 'vendored-sources'},
                'vendored-sources': {'directory': f'{CARGO_CRATES}'}
            }
        })),
        'dest': CARGO_HOME,
        'dest-filename': 'config'
    }]
    metadata = cargo_lock['metadata']
    for package in cargo_lock['package']:
        name = package['name']
        version = package['version']
        if 'source' in package:
            source = package['source']
            key = f'checksum {name} {version} ({source})'
            if key not in metadata:
                print(f'{key} not in metadata', file=sys.stderr)
                continue
            checksum = metadata[key]
        else:
            print(f'{name} has no source', file=sys.stderr)
            continue
        sources += [
            {
                'type': 'file',
                'url': f'{CRATES_IO}/{name}/{name}-{version}.crate',
                'sha256': checksum,
                'dest': CARGO_CRATES,
                'dest-filename': f'{name}-{version}.crate'
            },
            {
                'type': 'file',
                'url': 'data:' + urlquote(json.dumps({'package': checksum, 'files': {}})),
                'dest': f'{CARGO_CRATES}/{name}-{version}',
                'dest-filename': '.cargo-checksum.json',
            }
        ]
    sources.append({
        'type': 'shell',
        'dest': CARGO_CRATES,
        'commands': [
            'for c in *.crate; do tar -xf $c; done'
        ]
    })
    return sources

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cargo_lock', help='Path to the Cargo.lock file')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    args = parser.parse_args()
    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'generated-sources.json'

    generated_sources = generate_sources(load_cargo_lock(args.cargo_lock))
    with open(outfile, 'w') as out:
        json.dump(generated_sources, out, indent=4, sort_keys=False)

if __name__ == '__main__':
    main()
