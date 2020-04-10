#!/usr/bin/env python3

__license__ = 'MIT'
import base64
import toml
import json
from urllib.parse import quote as urlquote
from urllib.parse import urlparse, ParseResult, parse_qs
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
CARGO_GIT_DB = f'{CARGO_HOME}/git/db'
CARGO_CRATES = f'{CARGO_HOME}/vendor'


def rust_digest(b):
    # The 0xff suffix matches Rust's behaviour
    # https://doc.rust-lang.org/src/core/hash/mod.rs.html#611-616
    digest = siphasher(b.encode() + b'\xff').decode('ascii').lower()
    logging.debug("Hashing %r to %r", b, digest)
    return digest


def canonical_url(url):
    "Converts a string to a Cargo Canonical URL, as per https://github.com/rust-lang/cargo/blob/35c55a93200c84a4de4627f1770f76a8ad268a39/src/cargo/util/canonical_url.rs#L19"
    logging.debug("canonicalising %s", url)
    # Hrm. The upstream cargo does not replace those URLs, but if we don't then it doesn't work too well :(
    url = url.replace("git+https://", "https://")
    u = urlparse(url)
    # It seems cargo drops query and fragment
    u = ParseResult(u.scheme, u.netloc, u.path, None, None, None)
    u = u._replace(path = u.path.rstrip('/'))

    if u.netloc == "github.com":
        u = u._replace(scheme = "https")
        u = u._replace(path = u.path.lower())

    if u.path.endswith(".git"):
        u = u._replace(path = u.path[:-len(".git")])

    return u

def load_cargo_lock(lockfile='Cargo.lock'):
    with open(lockfile, 'r') as f:
        cargo_lock = toml.load(f)
    return cargo_lock

def get_git_sources(package):
    name = package["name"]
    source = package["source"]
    revision = urlparse(source).fragment
    branches = parse_qs(urlparse(source).query).get("branch", [])
    if branches:
        assert len(branches) == 1, f"Expected exactly one branch, got {branches}"
        branch = branches[0]
    else:
        branch = "master"

    assert revision, "The commit needs to be indicated in the fragement part"
    canonical = canonical_url(source)
    reponame = canonical.path.rsplit('/', 1)[1]
    digest = rust_digest(canonical.geturl())
    shortcommit = revision[:8]
    cargo_git_source = {
        "canonical": canonical.geturl(),
        "branch": branch,
        "rev": revision,
    }
    git_sources = [
        {
            "type": "git",
            "url": canonical.geturl(),
            "commit": revision,
            "dest": f'{CARGO_CRATES}/{name}',
        },
        {
            "type": "shell",
            "commands": [
                f"git clone --bare {CARGO_CRATES}/{name} {CARGO_GIT_DB}/{name}-{digest}"
            ]
        },
        {
            "type": "shell",
            "commands": [
                # FIXME: This is an ugly workaround for imap-proto, https://github.com/djc/tokio-imap, which has workspaces in Cargo.toml
                # The correct solution is to parse Cargo.toml.
                # Then, however, we get very close to implementation details s.t. it seems smarter to patch cargo instead of
                # reverse engineering its behaviour.
                f"if test -d {CARGO_CRATES}/{name}/{name}; then "
                f"mv {CARGO_CRATES}/{name} {CARGO_CRATES}/{name}.bak; "
                f"cp -ar --dereference --reflink=auto {CARGO_CRATES}/{name}.bak/{name} {CARGO_CRATES}/{name}; "
                f"rm -r {CARGO_CRATES}/{name}.bak; "
                "fi",
            ],
        },
        {
            'type': 'file',
            # FIXME: Vendor is hard coded
            'url': "data:" + urlquote(json.dumps({'package': None, 'files': {}})),
            'dest': f'{CARGO_CRATES}/{name}', #-{version}',
            'dest-filename': '.cargo-checksum.json',
        },
        {
            "type": "shell",
            "commands": [
                f"echo rm -r {CARGO_CRATES}/{name}/.git",
                # FIXME: Cargo does not copy .git/ and some other files
            ],
        },
    ]
    return (git_sources, cargo_git_source)

def generate_sources(cargo_lock):
    sources = []
    cargo_git_sources = []
    metadata = cargo_lock.get('metadata')
    for package in cargo_lock['package']:
        name = package['name']
        version = package['version']
        if 'source' in package:
            source = package['source']
            if source.startswith("git+"):
                git_sources, cargo_git_source = get_git_sources(package)
                sources += git_sources
                cargo_git_sources.append(cargo_git_source)
                continue
            else:
                key = f'checksum {name} {version} ({source})'
                if metadata is not None and key in metadata:
                    checksum = metadata[key]
                elif "checksum" in package:
                    checksum = package["checksum"]
                else:
                    logging.warning(f"{name} doesn't have checksum")
                    continue
        else:
            logging.warning(f"{name} has no source")
            logging.debug(f"Package for {name}: {package}")
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
            },
        ]
    sources.append({
        'type': 'shell',
        'dest': CARGO_CRATES,
        'commands': [
            'for c in *.crate; do tar -xf $c; done'
        ]
    })
    cargo_sources = {
        'crates-io': {'replace-with': 'vendored-sources'},
        'vendored-sources': {'directory': f'{CARGO_CRATES}'},
    }
    for cargo_git_source in cargo_git_sources:
        # FIXME: Make those a proper attrib
        canonical = cargo_git_source["canonical"]
        branch = cargo_git_source["branch"]
        revision = cargo_git_source["rev"]

        key = canonical
        value = {
            "git": canonical,
            "branch": branch,
            # "rev": revision,
            "replace-with": "vendored-sources",
        }
        cargo_sources[key] = value

    logging.debug(f"Vendored sources: {cargo_sources}")
    sources.append({
        'type': 'file',
        'url': 'data:' + urlquote(toml.dumps({
            'source': cargo_sources,
        })),
        'dest': CARGO_HOME,
        'dest-filename': 'config'
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
    logging.basicConfig(level=logging.DEBUG)
    main()
