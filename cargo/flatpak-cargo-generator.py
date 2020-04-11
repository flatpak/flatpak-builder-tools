#!/usr/bin/env python3

__license__ = 'MIT'
import base64
import toml
import json
from urllib.parse import quote as urlquote
from urllib.parse import urlparse, ParseResult, parse_qs
import os
import tempfile
import subprocess
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
VENDORED_SOURCES = 'vendored-sources'


def rust_digest(b):
    # The 0xff suffix matches Rust's behaviour
    # https://doc.rust-lang.org/src/core/hash/mod.rs.html#611-616
    digest = siphasher(b.encode() + b'\xff').decode('ascii').lower()
    logging.debug('Hashing %r to %r', b, digest)
    return digest

def canonical_url(url):
    'Converts a string to a Cargo Canonical URL, as per https://github.com/rust-lang/cargo/blob/35c55a93200c84a4de4627f1770f76a8ad268a39/src/cargo/util/canonical_url.rs#L19'
    logging.debug('canonicalising %s', url)
    # Hrm. The upstream cargo does not replace those URLs, but if we don't then it doesn't work too well :(
    url = url.replace('git+https://', 'https://')
    u = urlparse(url)
    # It seems cargo drops query and fragment
    u = ParseResult(u.scheme, u.netloc, u.path, None, None, None)
    u = u._replace(path = u.path.rstrip('/'))

    if u.netloc == 'github.com':
        u = u._replace(scheme = 'https')
        u = u._replace(path = u.path.lower())

    if u.path.endswith('.git'):
        u = u._replace(path = u.path[:-len('.git')])

    return u

def load_cargo_lock(lockfile='Cargo.lock'):
    with open(lockfile, 'r') as f:
        cargo_lock = toml.load(f)
    return cargo_lock

def get_git_cargo_packages(git_url, revision):
    tmdir = os.path.join(tempfile.gettempdir(), 'flatpak-cargo', rust_digest(git_url))
    if not os.path.isdir(os.path.join(tmdir, '.git')):
        subprocess.run(['git', 'clone', git_url, tmdir], check=True)
    subprocess.run(['git', 'checkout', tmdir], cwd=tmdir, check=True)
    with open(os.path.join(tmdir, 'Cargo.toml'), 'r') as r:
        root_toml = toml.load(r)
    if 'package' in root_toml:
        return [(root_toml['package']['name'], '.')]
    elif 'workspace' in root_toml:
        packages = []
        for subpkg in root_toml['workspace']['members']:
            with open(os.path.join(tmdir, subpkg, 'Cargo.toml'), 'r') as f:
                pkg_toml = toml.load(f)
                packages.append((pkg_toml['package']['name'], subpkg))
        return packages
    else:
        raise ValueError(f'Neither "package" nor "workspace" in {git_url}')

def get_git_sources(package):
    name = package['name']
    source = package['source']
    revision = urlparse(source).fragment
    branches = parse_qs(urlparse(source).query).get('branch', [])
    if branches:
        assert len(branches) == 1, f'Expected exactly one branch, got {branches}'
        branch = branches[0]
    else:
        branch = 'master'

    assert revision, 'The commit needs to be indicated in the fragement part'
    canonical = canonical_url(source)
    repo_url = canonical.geturl()
    _, repo_name = repo_url.rsplit('/', 1)
    digest = rust_digest(repo_url)
    cargo_vendored_entry = {
        repo_url: {
            'git': repo_url,
            'branch': branch,
            #XXX 'rev': revision,
            'replace-with': VENDORED_SOURCES,
        }
    }
    git_repo_sources = {digest: [
        {
            'type': 'git',
            'url': repo_url,
            'commit': revision,
            'dest': f'{CARGO_GIT_DB}/{repo_name}-{digest}',
        },
        {
            'type': 'shell',
            'commands': [
                f'cd {CARGO_GIT_DB}/{repo_name}-{digest} && git config core.bare true'
            ]
        }
    ]}
    git_sources = []
    for pkg_name, pkg_subpath in get_git_cargo_packages(repo_url, revision):
        if pkg_name != name:
            continue
        if pkg_subpath == '.':
            checkout_commands = [
                f'git clone {CARGO_GIT_DB}/{repo_name}-{digest} {CARGO_CRATES}/{pkg_name}'
            ]
        else:
            checkout_commands = [
                f'git clone {CARGO_GIT_DB}/{repo_name}-{digest} {CARGO_CRATES}/{pkg_name}.full',
                f'mv {CARGO_CRATES}/{pkg_name}.full/{pkg_subpath} {CARGO_CRATES}/{pkg_name}',
                f'rm -rf {CARGO_CRATES}/{pkg_name}.full'
            ]
        git_sources += [
            {
                'type': 'shell',
                'commands': checkout_commands
            },
            {
                'type': 'file',
                'url': 'data:' + urlquote(json.dumps({'package': None, 'files': {}})),
                'dest': f'{CARGO_CRATES}/{name}', #-{version}',
                'dest-filename': '.cargo-checksum.json',
            }
        ]
    return (git_sources, git_repo_sources, cargo_vendored_entry)

def generate_sources(cargo_lock):
    sources = []
    module_sources = []
    cargo_vendored_sources = {
        VENDORED_SOURCES: {'directory': f'{CARGO_CRATES}'},
        'crates-io': {'replace-with': VENDORED_SOURCES},
    }
    git_repo_sources = {}
    metadata = cargo_lock.get('metadata')
    for package in cargo_lock['package']:
        name = package['name']
        version = package['version']
        if 'source' in package:
            source = package['source']
            if source.startswith('git+'):
                git_sources, pkg_git_repo_sources, cargo_vendored_entry = get_git_sources(package)
                module_sources += git_sources
                cargo_vendored_sources.update(cargo_vendored_entry)
                git_repo_sources.update(pkg_git_repo_sources)
                continue
            else:
                key = f'checksum {name} {version} ({source})'
                if metadata is not None and key in metadata:
                    checksum = metadata[key]
                elif 'checksum' in package:
                    checksum = package['checksum']
                else:
                    logging.warning(f'{name} doesn\'t have checksum')
                    continue
        else:
            logging.warning(f'{name} has no source')
            logging.debug(f'Package for {name}: {package}')
            continue
        module_sources += [
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

    for repo_sources in git_repo_sources.values():
        sources += repo_sources

    sources += module_sources
    sources.append({
        'type': 'shell',
        'dest': CARGO_CRATES,
        'commands': [
            'for c in *.crate; do tar -xf $c; done'
        ]
    })

    logging.debug(f'Vendored sources: {cargo_vendored_sources}')
    sources.append({
        'type': 'file',
        'url': 'data:' + urlquote(toml.dumps({
            'source': cargo_vendored_sources,
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
