from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import tarfile
import time

_SANITIZE_RE = re.compile(r'[\\/:*?"<>|]')


def populate_store(manifest_path: str, tarball_dir: str, store_dir: str) -> None:
    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)

    store_version = manifest['store_version']
    packages = manifest['packages']

    store = os.path.join(store_dir, store_version)
    os.makedirs(os.path.join(store, 'files'), exist_ok=True)
    os.makedirs(os.path.join(store, 'index'), exist_ok=True)

    now = int(time.time() * 1000)

    for tarball_name, info in packages.items():
        tarball_path = os.path.join(tarball_dir, tarball_name)
        if not os.path.isfile(tarball_path):
            print(
                f'ERROR: {tarball_path} not found',
                file=sys.stderr,
            )
            sys.exit(1)

        _process_tarball(
            tarball_path=tarball_path,
            pkg_name=info['name'],
            pkg_version=info['version'],
            integrity_hex=info['integrity_hex'],
            requires_build=info.get('requires_build', False),
            store=store,
            now=now,
        )


def _process_tarball(
    *,
    tarball_path: str,
    pkg_name: str,
    pkg_version: str,
    integrity_hex: str,
    requires_build: bool,
    store: str,
    now: int,
) -> None:
    index_files: dict[str, dict[str, object]] = {}

    with tarfile.open(tarball_path, 'r:gz') as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            fobj = tf.extractfile(member)
            if fobj is None:
                continue
            data = fobj.read()

            digest = hashlib.sha512(data).digest()
            file_hex = digest.hex()
            is_exec = bool(member.mode & 0o111)

            cas_dir = os.path.join(store, 'files', file_hex[:2])
            cas_name = file_hex[2:] + ('-exec' if is_exec else '')
            cas_path = os.path.join(cas_dir, cas_name)
            if not os.path.exists(cas_path):
                os.makedirs(cas_dir, exist_ok=True)
                with open(cas_path, 'wb') as out:
                    out.write(data)
                if is_exec:
                    os.chmod(cas_path, 0o755)

            rel_name = member.name
            if '/' in rel_name:
                rel_name = rel_name.split('/', 1)[1]

            b64 = base64.b64encode(digest).decode()
            index_files[rel_name] = {
                'checkedAt': now,
                'integrity': f'sha512-{b64}',
                'mode': member.mode,
                'size': len(data),
            }

    idx_prefix = integrity_hex[:2]
    idx_rest = integrity_hex[2:64]
    pkg_id = _SANITIZE_RE.sub('+', f'{pkg_name}@{pkg_version}')
    idx_dir = os.path.join(store, 'index', idx_prefix)
    os.makedirs(idx_dir, exist_ok=True)
    idx_path = os.path.join(idx_dir, f'{idx_rest}-{pkg_id}.json')
    index_data = {
        'name': pkg_name,
        'version': pkg_version,
        'requiresBuild': requires_build,
        'files': index_files,
    }
    with open(idx_path, 'w', encoding='utf-8') as out:
        json.dump(index_data, out)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(
            f'Usage: {sys.argv[0]} <manifest.json> <tarball-dir> <store-dir>',
            file=sys.stderr,
        )
        sys.exit(1)
    populate_store(sys.argv[1], sys.argv[2], sys.argv[3])
