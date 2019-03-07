#!/usr/bin/env python3

__license__ = 'WTFPL'

import pytoml
import json
from urllib.parse import quote as urlquote
import sys
import argparse

CRATES_IO = 'https://static.crates.io/crates'
CARGO_HOME = 'cargo'
CARGO_CRATES = f'{CARGO_HOME}/vendor'

CARGO_CONFIG = f"""\
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "{CARGO_CRATES}"
"""

def load_cargo_lock(lockfile='Cargo.lock'):
    with open(lockfile, 'r') as f:
        cargo_lock = pytoml.load(f)
    return cargo_lock

def generate_sources(cargo_lock):
    sources = [{
        'type': 'file',
        'url': 'data:' + urlquote(CARGO_CONFIG),
        'dest': CARGO_HOME,
        'dest-filename': 'config'
    }]
    metadata = cargo_lock['metadata']
    for package in cargo_lock['package']:
        name = package['name']
        version = package['version']
        if 'source' in package:
            source = package['source']
            checksum = metadata[f'checksum {name} {version} ({source})']
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
