import re
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    NamedTuple,
    Optional,
    Tuple,
)

import yaml

from ..integrity import Integrity
from ..package import (
    GitSource,
    LocalSource,
    Lockfile,
    Package,
    PackageSource,
    ResolvedSource,
)
from . import LockfileProvider

_SUPPORTED_V6_VERSIONS = ('6', '7')


class PnpmLockfileProvider(LockfileProvider):
    """Parses pnpm-lock.yaml (v6/v7 and v9) into Package objects."""

    # NOTE v6/v7 keys: /name@version or /@scope/name@version
    # Version may have peer dep suffix like (react@18.2.0) — stop before '('
    _V6_PACKAGE_RE = re.compile(r'^/(?P<name>(?:@[^/]+/)?[^@]+)@(?P<version>[^(]+)')
    # NOTE v9 keys: name@version or @scope/name@version
    _V9_PACKAGE_RE = re.compile(r'^(?P<name>(?:@[^/]+/)?[^@]+)@(?P<version>[^(]+)')

    class Options(NamedTuple):
        no_devel: bool
        registry: str

    def __init__(self, options: 'PnpmLockfileProvider.Options') -> None:
        self.no_devel = options.no_devel
        self.registry = options.registry.rstrip('/')

    def _get_tarball_url(
        self,
        name: str,
        version: str,
        resolution: Dict[str, Any],
    ) -> str:
        if 'tarball' in resolution:
            return str(resolution['tarball'])

        if name.startswith('@'):
            basename = name.split('/')[-1]
        else:
            basename = name

        return f'{self.registry}/{name}/-/{basename}-{version}.tgz'

    def _parse_package_key(
        self, key: str, lockfile_version: str
    ) -> Optional[Tuple[str, str]]:
        if lockfile_version.startswith(_SUPPORTED_V6_VERSIONS):
            match = self._V6_PACKAGE_RE.match(key)
        else:
            match = self._V9_PACKAGE_RE.match(key)

        if match is None:
            return None
        return match.group('name'), match.group('version')

    def process_lockfile(self, lockfile_path: Path) -> Iterator[Package]:
        with open(lockfile_path, encoding='utf-8') as fp:
            data = yaml.safe_load(fp)

        raw_version = data.get('lockfileVersion')
        if raw_version is None:
            raise ValueError(f'{lockfile_path}: missing lockfileVersion field')

        lockfile_version = str(raw_version)
        if lockfile_version.startswith('5'):
            raise ValueError(
                f'{lockfile_path}: lockfile v5 (pnpm 5) is not supported. '
                'Please upgrade to pnpm 8+ and regenerate your lockfile.'
            )

        lockfile = Lockfile(lockfile_path, int(float(lockfile_version)))

        packages_dict: Dict[str, Any] = data.get('packages', {})
        if not packages_dict:
            return

        for key, info in packages_dict.items():
            if info is None:
                continue

            parsed = self._parse_package_key(key, lockfile_version)
            if parsed is None:
                continue

            name, version = parsed

            # NOTE v6/v7: dev packages have dev: true directly on the entry
            if self.no_devel and info.get('dev', False):
                continue

            resolution: Dict[str, Any] = info.get('resolution', {})
            if not resolution:
                continue

            source: PackageSource

            if resolution.get('type') == 'git':
                source = self.parse_git_source(
                    f'git+{resolution["repo"]}#{resolution["commit"]}'
                )
            elif 'directory' in resolution:
                source = LocalSource(path=resolution['directory'])
            else:
                integrity = None
                if 'integrity' in resolution:
                    integrity = Integrity.parse(resolution['integrity'])

                tarball_url = self._get_tarball_url(name, version, resolution)
                source = ResolvedSource(resolved=tarball_url, integrity=integrity)

            yield Package(
                name=name,
                version=version,
                source=source,
                lockfile=lockfile,
            )
