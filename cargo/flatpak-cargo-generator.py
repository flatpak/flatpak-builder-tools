#!/usr/bin/env python3

__license__ = 'MIT'
import base64
import toml
import json
from urllib.parse import quote as urlquote
from urllib.parse import urlparse, ParseResult
import sys
import argparse
import logging


key = b'\x00' * 16
try:
    # this is siphash-cffi
    from siphash import siphash_64
    siphasher = lambda b: base64.b16encode(siphash_64(key, b))

except ImportError:
    # this is siphash
    from siphash import SipHash_2_4
    siphasher = lambda b: SipHash_2_4(key, b).hexdigest()



CRATES_IO = 'https://static.crates.io/crates'
CARGO_HOME = 'cargo'
CARGO_CRATES = f'{CARGO_HOME}/vendor'


def rust_digest(b):
    # The 0xff suffix matches Rust's behaviour
    # https://doc.rust-lang.org/src/core/hash/mod.rs.html#611-616
    digest = siphasher(b.encode() + b'\xff').decode('ascii').lower()
    logging.debug("Hashing %r to %r", b, digest)
    return digest


def canonical_url(url):
    "Converts a string to a Cargo Canonical URL, as per https://github.com/rust-lang/cargo/blob/35c55a93200c84a4de4627f1770f76a8ad268a39/src/cargo/util/canonical_url.rs#L19"
    u = urlparse(url)
    # It seems cargo drops query and fragment
    u = ParseResult(u.scheme, u.netloc, u.path, None, None, None)
    u = u._replace(path = u.path.rstrip('/'))

    if u.netloc == "github.com":
        u = u._replace(scheme = "https")
        u = u._replace(path = u.path.lower())

    if u.path.endswith(".git"):
        u.path = u.path[:-len(".git")]

    return u

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
            if source.startswith("git+"):
                revision = urlparse(source).fragment
                assert revision, "The commit needs to be indicated in the fragement part"
                canonical = canonical_url(source)
                reponame = canonical.path.rsplit('/', 1)[1]
                hash = rust_digest(canonical.geturl())
                git_sources = [
                    {
                        "type": "git",
                        "url": canonical.geturl(),
                        "commit": revision,
                        "dest": f"cargo/git/db/{reponame}-{hash}"
                    },
                ]
                sources += git_sources
                continue

            else:
                key = f'checksum {name} {version} ({source})'
                if key not in metadata:
                    print(f'{key} ({source}) not in metadata', file=sys.stderr)
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
