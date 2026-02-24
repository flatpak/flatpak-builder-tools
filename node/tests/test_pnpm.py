from pathlib import Path

import pytest

from flatpak_node_generator.integrity import Integrity
from flatpak_node_generator.package import (
    Lockfile,
    Package,
    ResolvedSource,
)
from flatpak_node_generator.providers.pnpm import PnpmLockfileProvider

TEST_LOCKFILE_V9 = """
lockfileVersion: '9.0'

settings:
  autoInstallPeers: true
  excludeLinksFromLockfile: false

importers:
  .:
    dependencies:
      is-odd:
        specifier: ^3.0.1
        version: 3.0.1

packages:
  is-number@6.0.0:
    resolution: {integrity: sha512-Wu1VHeILBK8KAWJUAiSZQX94GmOE45Rg6/538fKwiloUu21KncEkYGPqob2oSZ5mUT73vLGrHQjKw3KMPwfDzg==}
    engines: {node: '>=0.10.0'}

  is-odd@3.0.1:
    resolution: {integrity: sha512-CQpnWPrDwmP1+SMHXZhtLtJv90yiyVfluGsX5iNCVkrhQtU3TQHsUWPG9wkdk9Lgd5yNpAg9jQEo90CBaXgWMA==}
    engines: {node: '>=4'}

  '@babel/core@7.23.0':
    resolution: {integrity: sha256-dGVzdA==}
    engines: {node: '>=6.9.0'}

snapshots:
  is-number@6.0.0: {}

  is-odd@3.0.1:
    dependencies:
      is-number: 6.0.0

  '@babel/core@7.23.0': {}
"""

TEST_LOCKFILE_V6 = """
lockfileVersion: '6.0'

dependencies:
  is-odd:
    specifier: ^3.0.1
    version: 3.0.1

devDependencies:
  is-number:
    specifier: ^6.0.0
    version: 6.0.0

packages:
  /is-number@6.0.0:
    resolution: {integrity: sha512-Wu1VHeILBK8KAWJUAiSZQX94GmOE45Rg6/538fKwiloUu21KncEkYGPqob2oSZ5mUT73vLGrHQjKw3KMPwfDzg==}
    engines: {node: '>=0.10.0'}
    dev: true

  /is-odd@3.0.1:
    resolution: {integrity: sha512-CQpnWPrDwmP1+SMHXZhtLtJv90yiyVfluGsX5iNCVkrhQtU3TQHsUWPG9wkdk9Lgd5yNpAg9jQEo90CBaXgWMA==}
    engines: {node: '>=4'}
    dev: false

  /next@14.0.5(react-dom@18.2.0)(react@18.2.0):
    resolution: {integrity: sha256-dGVzdA==}
    engines: {node: '>=18'}
    dev: false
"""


def test_lockfile_v9(tmp_path: Path) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=False,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile = Lockfile(tmp_path / 'pnpm-lock.yaml', 9)
    lockfile.path.write_text(TEST_LOCKFILE_V9)

    packages = list(provider.process_lockfile(lockfile.path))

    assert packages == [
        Package(
            lockfile=lockfile,
            name='is-number',
            version='6.0.0',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/is-number/-/is-number-6.0.0.tgz',
                integrity=Integrity(
                    'sha512',
                    '5aed551de20b04af0a016254022499417f781a6384e39460ebfe77f1f2b08a5a14bb6d4a9dc1246063eaa1bda8499e66513ef7bcb1ab1d08cac3728c3f07c3ce',
                ),
            ),
        ),
        Package(
            lockfile=lockfile,
            name='is-odd',
            version='3.0.1',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/is-odd/-/is-odd-3.0.1.tgz',
                integrity=Integrity(
                    'sha512',
                    '090a6758fac3c263f5f923075d986d2ed26ff74ca2c957e5b86b17e62342564ae142d5374d01ec5163c6f7091d93d2e0779c8da4083d8d0128f7408169781630',
                ),
            ),
        ),
        Package(
            lockfile=lockfile,
            name='@babel/core',
            version='7.23.0',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/@babel/core/-/core-7.23.0.tgz',
                integrity=Integrity(
                    'sha256',
                    '74657374',
                ),
            ),
        ),
    ]


def test_lockfile_v6(tmp_path: Path) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=False,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile = Lockfile(tmp_path / 'pnpm-lock.yaml', 6)
    lockfile.path.write_text(TEST_LOCKFILE_V6)

    packages = list(provider.process_lockfile(lockfile.path))

    assert packages == [
        Package(
            lockfile=lockfile,
            name='is-number',
            version='6.0.0',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/is-number/-/is-number-6.0.0.tgz',
                integrity=Integrity(
                    'sha512',
                    '5aed551de20b04af0a016254022499417f781a6384e39460ebfe77f1f2b08a5a14bb6d4a9dc1246063eaa1bda8499e66513ef7bcb1ab1d08cac3728c3f07c3ce',
                ),
            ),
        ),
        Package(
            lockfile=lockfile,
            name='is-odd',
            version='3.0.1',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/is-odd/-/is-odd-3.0.1.tgz',
                integrity=Integrity(
                    'sha512',
                    '090a6758fac3c263f5f923075d986d2ed26ff74ca2c957e5b86b17e62342564ae142d5374d01ec5163c6f7091d93d2e0779c8da4083d8d0128f7408169781630',
                ),
            ),
        ),
        Package(
            lockfile=lockfile,
            name='next',
            version='14.0.5',
            source=ResolvedSource(
                resolved='https://registry.npmjs.org/next/-/next-14.0.5.tgz',
                integrity=Integrity(
                    'sha256',
                    '74657374',
                ),
            ),
        ),
    ]


def test_lockfile_v6_no_devel(tmp_path: Path) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=True,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile = Lockfile(tmp_path / 'pnpm-lock.yaml', 6)
    lockfile.path.write_text(TEST_LOCKFILE_V6)

    packages = list(provider.process_lockfile(lockfile.path))

    names = [p.name for p in packages]
    assert 'is-number' not in names
    assert 'is-odd' in names
    assert 'next' in names


def test_lockfile_v5_rejected(tmp_path: Path) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=False,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile_path = tmp_path / 'pnpm-lock.yaml'
    lockfile_path.write_text(
        'lockfileVersion: 5.4\npackages:\n'
        '  /is-odd/3.0.1:\n'
        '    resolution: {integrity: sha256-dGVzdA==}\n'
    )

    with pytest.raises(ValueError, match='v5.*not supported'):
        list(provider.process_lockfile(lockfile_path))


def test_lockfile_unsupported_version_rejected(tmp_path: Path) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=False,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile_path = tmp_path / 'pnpm-lock.yaml'
    lockfile_path.write_text(
        'lockfileVersion: 42\npackages:\n'
        '  foo@1.0.0:\n'
        '    resolution: {integrity: sha256-dGVzdA==}\n'
    )

    with pytest.raises(ValueError, match='unsupported lockfileVersion 42'):
        list(provider.process_lockfile(lockfile_path))


def test_lockfile_v9_no_devel_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    provider = PnpmLockfileProvider(
        PnpmLockfileProvider.Options(
            no_devel=True,
            registry='https://registry.npmjs.org',
        )
    )

    lockfile = Lockfile(tmp_path / 'pnpm-lock.yaml', 9)
    lockfile.path.write_text(TEST_LOCKFILE_V9)

    packages = list(provider.process_lockfile(lockfile.path))

    captured = capsys.readouterr()
    assert '--no-devel is not yet supported for pnpm lockfile v9' in captured.err
    assert len(packages) == 3
