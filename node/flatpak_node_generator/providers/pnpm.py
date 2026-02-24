import json
import re
import types
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
)

import yaml

from ..integrity import Integrity
from ..manifest import ManifestGenerator
from ..package import (
    GitSource,
    LocalSource,
    Lockfile,
    Package,
    PackageSource,
    ResolvedSource,
)
from . import LockfileProvider, ModuleProvider, ProviderFactory, RCFileProvider
from .npm import NpmRCFileProvider
from .special import SpecialSourceProvider

_SUPPORTED_V6_VERSIONS = ('6', '7')

# All currently supported lockfile versions (v6/v7/v9) use store v10.
# Needs to be updated when a new pnpm major changes the store layout
_STORE_VERSION = 'v10'

_POPULATE_STORE_SCRIPT = Path(__file__).parents[1] / 'populate_pnpm_store.py'


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


class PnpmModuleProvider(ModuleProvider):
    """Generates flatpak sources for pnpm packages."""

    class Options(NamedTuple):
        registry: str

    class _TarballInfo(NamedTuple):
        tarball_name: str
        name: str
        version: str
        integrity: Integrity

    def __init__(
        self,
        gen: ManifestGenerator,
        special: SpecialSourceProvider,
        lockfile_root: Path,
        options: 'PnpmModuleProvider.Options',
    ) -> None:
        self.gen = gen
        self.special_source_provider = special
        self.lockfile_root = lockfile_root
        self.registry = options.registry
        self.tarball_dir = self.gen.data_root / 'pnpm-tarballs'
        self.store_dir = self.gen.data_root / 'pnpm-store'
        self._tarballs: List[PnpmModuleProvider._TarballInfo] = []

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        tb: Optional[types.TracebackType],
    ) -> None:
        if exc_type is None:
            self._finalize()

    async def generate_package(self, package: Package) -> None:
        source = package.source

        if isinstance(source, ResolvedSource):
            assert source.resolved is not None
            assert source.integrity is not None

            # Use name-version as filename; replace / in scoped names
            tarball_name = f'{package.name.replace("/", "-")}-{package.version}.tgz'
            self.gen.add_url_source(
                url=source.resolved,
                integrity=source.integrity,
                destination=self.tarball_dir / tarball_name,
            )
            self._tarballs.append(
                self._TarballInfo(
                    tarball_name=tarball_name,
                    name=package.name,
                    version=package.version,
                    integrity=source.integrity,
                )
            )

            await self.special_source_provider.generate_special_sources(package)

        elif isinstance(source, GitSource):
            name = f'{package.name}-{source.commit}'
            path = self.gen.data_root / 'git-packages' / name
            self.gen.add_git_source(source.url, source.commit, path)

        elif isinstance(source, LocalSource):
            pass

        else:
            raise NotImplementedError(
                f'Unknown source type {source.__class__.__name__}'
            )

    def _finalize(self) -> None:
        if self._tarballs:
            self._add_store_population_script()
            self._add_pnpm_config()

    def _add_store_population_script(self) -> None:
        packages = {}
        for info in self._tarballs:
            packages[info.tarball_name] = {
                'name': info.name,
                'version': info.version,
                'integrity_hex': info.integrity.digest,
                # TODO: extract from lockfile (v6: requiresBuild on entry,
                # v9: requiresBuild in snapshots section)
                'requires_build': False,
            }

        manifest = {
            'store_version': _STORE_VERSION,
            'packages': packages,
        }
        manifest_json = json.dumps(manifest, separators=(',', ':'))
        manifest_dest = self.gen.data_root / 'pnpm-manifest.json'
        self.gen.add_data_source(manifest_json, manifest_dest)

        with open(_POPULATE_STORE_SCRIPT, encoding='utf-8') as f:
            script_source = f.read()
        script_dest = self.gen.data_root / 'populate_pnpm_store.py'
        self.gen.add_data_source(script_source, script_dest)

        self.gen.add_command(
            f'python3 {script_dest} {manifest_dest} {self.tarball_dir} {self.store_dir}'
        )

    def _add_pnpm_config(self) -> None:
        self.gen.add_command(f'echo "store-dir=$PWD/{self.store_dir}" >> .npmrc')


class PnpmProviderFactory(ProviderFactory):
    class Options(NamedTuple):
        lockfile: PnpmLockfileProvider.Options
        module: PnpmModuleProvider.Options

    def __init__(
        self, lockfile_root: Path, options: 'PnpmProviderFactory.Options'
    ) -> None:
        self.lockfile_root = lockfile_root
        self.options = options

    def create_lockfile_provider(self) -> PnpmLockfileProvider:
        return PnpmLockfileProvider(self.options.lockfile)

    def create_rcfile_providers(self) -> List[RCFileProvider]:
        return [NpmRCFileProvider()]

    def create_module_provider(
        self, gen: ManifestGenerator, special: SpecialSourceProvider
    ) -> PnpmModuleProvider:
        return PnpmModuleProvider(gen, special, self.lockfile_root, self.options.module)
