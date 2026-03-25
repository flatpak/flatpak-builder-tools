from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import re
import sys
import tarfile
import time

_SANITIZE_RE = re.compile(r'[\\/:*?"<>|]')
_MAX_LENGTH_WITHOUT_HASH = 120


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
            raise FileNotFoundError(tarball_path)

        _process_tarball(
            tarball_path=tarball_path,
            pkg_name=info['name'],
            pkg_version=info['version'],
            integrity_hex=info['integrity_hex'],
            store=store,
            now=now,
            tarball_url=info.get('tarball_url'),
            store_version=store_version,
        )


def _process_tarball(
    *,
    tarball_path: str,
    pkg_name: str,
    pkg_version: str,
    integrity_hex: str,
    store: str,
    now: int,
    tarball_url: str | None = None,
    store_version: str = 'v3',
) -> None:
    index_files: dict[str, dict[str, object]] = {}
    real_pkg_name = pkg_name
    real_pkg_version = pkg_version

    with tarfile.open(tarball_path, 'r:gz') as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            fobj = tf.extractfile(member)
            if fobj is None:
                continue
            data = fobj.read()

            if member.name.endswith('package.json') and member.name.count('/') <= 1:
                with contextlib.suppress(ValueError, TypeError, UnicodeDecodeError):
                    pkg_data = json.loads(data.decode('utf-8'))
                    if isinstance(pkg_data, dict):
                        if 'name' in pkg_data and isinstance(pkg_data['name'], str):
                            real_pkg_name = pkg_data['name']
                        if 'version' in pkg_data and isinstance(
                            pkg_data['version'], str
                        ):
                            real_pkg_version = pkg_data['version']

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

    index_data = {
        'name': real_pkg_name,
        'version': real_pkg_version,
        'requiresBuild': False,
        'files': index_files,
    }

    idx_prefix = integrity_hex[:2]
    idx_rest = integrity_hex[2:64]
    pkg_id = _SANITIZE_RE.sub('+', f'{pkg_name}@{pkg_version}')
    idx_dir = os.path.join(store, 'index', idx_prefix)
    os.makedirs(idx_dir, exist_ok=True)
    idx_path = os.path.join(idx_dir, f'{idx_rest}-{pkg_id}.json')
    with open(idx_path, 'w', encoding='utf-8') as out:
        json.dump(index_data, out)

    # For tarball-URL packages, also create an index entry keyed by the URL hash
    # this is how pnpm looks up tarball deps without integrity
    if tarball_url:
        if store_version == 'v3':
            url_hash = hashlib.sha256(tarball_url.encode()).hexdigest()
            url_idx_prefix = url_hash[:2]
            url_idx_rest = url_hash[2:64]
            url_idx_dir = os.path.join(store, 'index', url_idx_prefix)
            os.makedirs(url_idx_dir, exist_ok=True)
            url_idx_path = os.path.join(url_idx_dir, f'{url_idx_rest}-{pkg_id}.json')
            with open(url_idx_path, 'w', encoding='utf-8') as out:
                json.dump(index_data, out)
        else:
            url_dir_name = re.sub(r'[:/]', '+', tarball_url)
            if (
                len(url_dir_name) > _MAX_LENGTH_WITHOUT_HASH
                or url_dir_name != url_dir_name.lower()
            ):
                url_dir_name = f'{url_dir_name[: _MAX_LENGTH_WITHOUT_HASH - 33]}_{hashlib.sha256(url_dir_name.encode()).hexdigest()[:32]}'
            url_idx_dir = os.path.join(store, url_dir_name)
            os.makedirs(url_idx_dir, exist_ok=True)
            url_idx_path = os.path.join(url_idx_dir, 'integrity.json')
            with open(url_idx_path, 'w', encoding='utf-8') as out:
                json.dump(index_data, out)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(
            f'Usage: {sys.argv[0]} <manifest.json> <tarball-dir> <store-dir>',
            file=sys.stderr,
        )
        sys.exit(1)
    populate_store(sys.argv[1], sys.argv[2], sys.argv[3])
