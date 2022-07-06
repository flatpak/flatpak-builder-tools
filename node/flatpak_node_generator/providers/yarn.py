from pathlib import Path
from typing import Iterator, List, Optional, Type

import os
import re
import types
import urllib.parse

from ..integrity import Integrity
from ..manifest import ManifestGenerator
from ..package import GitSource, LocalSource, Package, PackageSource, ResolvedSource
from . import LockfileProvider, ModuleProvider, ProviderFactory, RCFileProvider
from .npm import NpmRCFileProvider
from .special import SpecialSourceProvider

GIT_URL_PATTERNS = [
    re.compile(r'^git:'),
    re.compile(r'^git\+.+:'),
    re.compile(r'^ssh:'),
    re.compile(r'^https?:.+\.git$'),
    re.compile(r'^https?:.+\.git#.+'),
]

GIT_URL_HOSTS = ['github.com', 'gitlab.com', 'bitbucket.com', 'bitbucket.org']


class YarnLockfileProvider(LockfileProvider):
    _LOCAL_PKG_RE = re.compile(r'^(?:file|link):')

    @staticmethod
    def is_git_version(version: str) -> bool:
        for pattern in GIT_URL_PATTERNS:
            if pattern.match(version):
                return True
        url = urllib.parse.urlparse(version)
        if url.netloc in GIT_URL_HOSTS:
            return len([p for p in url.path.split('/') if p]) == 2
        return False

    def unquote(self, string: str) -> str:
        if string.startswith('"'):
            assert string.endswith('"')
            return string[1:-1]
        else:
            return string

    def parse_package_section(self, lockfile: Path, section: List[str]) -> Package:
        assert section
        name_line = section[0]
        assert name_line.endswith(':'), name_line
        name_line = name_line[:-1]

        name = self.unquote(name_line.split(',', 1)[0])
        name, version_constraint = name.rsplit('@', 1)

        version: Optional[str] = None
        resolved: Optional[str] = None
        integrity: Optional[Integrity] = None

        section_indent = 0

        line = None
        for line in section[1:]:
            indent = 0
            while line[indent].isspace():
                indent += 1

            assert indent, line
            if not section_indent:
                section_indent = indent
            elif indent > section_indent:
                # Inside some nested section.
                continue

            line = line.strip()

            if line.startswith('"'):
                # XXX: assuming no spaces in the quoted region!
                key, value = line.split(' ', 1)
                line = f'{self.unquote(key)} {value}'

            if line.startswith('version'):
                version = self.unquote(line.split(' ', 1)[1])
            elif line.startswith('resolved'):
                resolved = self.unquote(line.split(' ', 1)[1])
            elif line.startswith('integrity'):
                _, values_str = line.split(' ', 1)
                values = self.unquote(values_str).split(' ')
                integrity = Integrity.parse(values[0])

        assert version, section

        source: PackageSource
        if self._LOCAL_PKG_RE.match(version_constraint):
            source = LocalSource(path=self._LOCAL_PKG_RE.sub('', version_constraint))
        else:
            assert resolved, section
            if self.is_git_version(resolved):
                source = self.parse_git_source(version=resolved)
            else:
                source = ResolvedSource(resolved=resolved, integrity=integrity)

        return Package(name=name, version=version, source=source, lockfile=lockfile)

    def process_lockfile(self, lockfile: Path) -> Iterator[Package]:
        section: List[str] = []

        with open(lockfile) as fp:
            for line in map(str.rstrip, fp):
                if not line.strip() or line.strip().startswith('#'):
                    continue

                if not line[0].isspace():
                    if section:
                        yield self.parse_package_section(lockfile, section)
                        section = []

                section.append(line)

        if section:
            yield self.parse_package_section(lockfile, section)


class YarnRCFileProvider(RCFileProvider):
    RCFILE_NAME = '.yarnrc'


class YarnModuleProvider(ModuleProvider):
    # From https://github.com/yarnpkg/yarn/blob/v1.22.4/src/fetchers/tarball-fetcher.js
    _PACKAGE_TARBALL_URL_RE = re.compile(
        r'(?:(@[^/]+)(?:/|%2f))?[^/]+/(?:-|_attachments)/(?:@[^/]+/)?([^/]+)$'
    )

    def __init__(self, gen: ManifestGenerator, special: SpecialSourceProvider) -> None:
        self.gen = gen
        self.special_source_provider = special
        self.mirror_dir = self.gen.data_root / 'yarn-mirror'

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        tb: Optional[types.TracebackType],
    ) -> None:
        pass

    async def generate_package(self, package: Package) -> None:
        source = package.source

        if isinstance(source, ResolvedSource):
            integrity = await source.retrieve_integrity()
            url_parts = urllib.parse.urlparse(source.resolved)
            match = self._PACKAGE_TARBALL_URL_RE.search(url_parts.path)
            if match is not None:
                scope, filename = match.groups()
                if scope:
                    filename = f'{scope}-{filename}'
            else:
                filename = os.path.basename(url_parts.path)

            self.gen.add_url_source(
                source.resolved, integrity, self.mirror_dir / filename
            )

        elif isinstance(source, GitSource):
            repo_name = urllib.parse.urlparse(source.url).path.split('/')[-1]
            name = f'{repo_name}-{source.commit}'
            repo_dir = self.gen.tmp_root / name
            target_tar = os.path.relpath(self.mirror_dir / name, repo_dir)

            self.gen.add_git_source(source.url, source.commit, repo_dir)
            self.gen.add_command(f'mkdir -p {self.mirror_dir}')
            self.gen.add_command(
                f'cd {repo_dir}; git archive --format tar -o {target_tar} HEAD'
            )

        elif isinstance(source, LocalSource):
            assert (package.lockfile.parent / source.path / 'package.json').is_file()

        else:
            raise NotImplementedError(
                f'Unknown source type {source.__class__.__name__}'
            )

        await self.special_source_provider.generate_special_sources(package)


class YarnProviderFactory(ProviderFactory):
    def __init__(self) -> None:
        pass

    def create_lockfile_provider(self) -> YarnLockfileProvider:
        return YarnLockfileProvider()

    def create_rcfile_providers(self) -> List[RCFileProvider]:
        return [YarnRCFileProvider(), NpmRCFileProvider()]

    def create_module_provider(
        self, gen: ManifestGenerator, special: SpecialSourceProvider
    ) -> YarnModuleProvider:
        return YarnModuleProvider(gen, special)
