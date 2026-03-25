import hashlib
import json
import re
import tarfile
from pathlib import Path

from flatpak_node_generator.populate_pnpm_store import _process_tarball


def _create_tarball(path: Path, files: dict[str, str | bytes]) -> None:
    with tarfile.open(path, 'w:gz') as tf:
        for name, data in files.items():
            content = data if isinstance(data, bytes) else data.encode('utf-8')
            tmp_file = path.parent / 'tmp_member'
            tmp_file.write_bytes(content)

            tarinfo = tarfile.TarInfo(name)
            tarinfo.size = len(content)
            tarinfo.mode = 0o644

            with open(tmp_file, 'rb') as f:
                tf.addfile(tarinfo, f)
            tmp_file.unlink()


def test_process_tarball_normal(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'
    pkg_json = json.dumps({'name': 'real-pkg', 'version': '1.2.3'})

    _create_tarball(
        tar_path,
        {'package/package.json': pkg_json, 'package/index.js': "console.log('hello');"},
    )

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='fallback-pkg',
        pkg_version='0.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
    )

    idx_files = list((store_dir / 'index' / 'a1').glob('*.json'))
    assert len(idx_files) == 1

    with open(idx_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data['name'] == 'real-pkg'
    assert data['version'] == '1.2.3'
    assert data['requiresBuild'] is False
    assert 'package.json' in data['files']
    assert 'index.js' in data['files']


def test_process_tarball_malformed_package_json(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'

    _create_tarball(tar_path, {'package/package.json': '{ malformed: json '})

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='fallback-pkg',
        pkg_version='0.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
    )

    idx_files = list((store_dir / 'index' / 'a1').glob('*.json'))
    assert len(idx_files) == 1

    with open(idx_files[0], 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data['name'] == 'fallback-pkg'
    assert data['version'] == '0.0.0'


def test_process_tarball_with_tarball_url_v3(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'
    tarball_url = 'https://example.com/pkg.tgz'

    _create_tarball(tar_path, {'package/index.js': "console.log('hello');"})

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='pkg',
        pkg_version='1.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
        tarball_url=tarball_url,
        store_version='v3',
    )

    import hashlib

    url_hash = hashlib.sha256(tarball_url.encode()).hexdigest()
    url_idx_dir = store_dir / 'index' / url_hash[:2]

    assert url_idx_dir.exists()
    assert len(list(url_idx_dir.glob('*.json'))) == 1


def test_process_tarball_with_tarball_url_v6(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'
    tarball_url = 'https://example.com/pkg.tgz'

    _create_tarball(tar_path, {'package/index.js': "console.log('hello');"})

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='pkg',
        pkg_version='1.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
        tarball_url=tarball_url,
        store_version='v6',
    )

    url_dir_name = re.sub(r'[:/]', '+', tarball_url)
    url_idx_file = store_dir / url_dir_name / 'integrity.json'

    assert url_idx_file.exists()


def test_process_tarball_with_uppercase_path(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'
    tarball_url = 'https://example.com/PKG.tgz'

    _create_tarball(tar_path, {'package/index.js': "console.log('hello');"})

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='pkg',
        pkg_version='1.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
        tarball_url=tarball_url,
        store_version='v6',
    )

    sanitized_tarball_url = re.sub(r'[:/]', '+', tarball_url)
    normalized_tarball_url = f'{sanitized_tarball_url}_{hashlib.sha256(sanitized_tarball_url.encode()).hexdigest()[:32]}'
    url_idx_file = store_dir / normalized_tarball_url / 'integrity.json'

    assert url_idx_file.exists()


def test_process_tarball_with_long_path(tmp_path: Path) -> None:
    tar_path = tmp_path / 'pkg.tgz'
    store_dir = tmp_path / 'store'
    tarball_url = f'https://example.com{"pkg" * 50}.tgz'

    _create_tarball(tar_path, {'package/index.js': "console.log('hello');"})

    _process_tarball(
        tarball_path=str(tar_path),
        pkg_name='pkg',
        pkg_version='1.0.0',
        integrity_hex='a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
        store=str(store_dir),
        now=1234567890,
        tarball_url=tarball_url,
        store_version='v6',
    )

    sanitized_tarball_url = re.sub(r'[:/]', '+', tarball_url)
    normalized_tarball_url = f'{sanitized_tarball_url[:87]}_{hashlib.sha256(sanitized_tarball_url.encode()).hexdigest()[:32]}'
    url_idx_file = store_dir / normalized_tarball_url / 'integrity.json'

    assert url_idx_file.exists()
