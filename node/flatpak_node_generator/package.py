import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple, Union

from .integrity import Integrity
from .url_metadata import RemoteUrlMetadata


@dataclass(frozen=True, order=True, eq=True)
class SemVer:
    # Note that we ignore the metadata part, since all we do is version
    # comparisons.
    _SEMVER_RE = re.compile(r'(\d+)\.(\d+)\.(\d+)(?:-(?P<prerelease>[^+]+)(\+|$))?')

    @functools.total_ordering
    class Prerelease:
        def __init__(self, parts: Tuple[Union[str, int], ...]) -> None:
            self._parts = parts

        def __hash__(self) -> int:
            return hash(self._parts)

        @staticmethod
        def parse(rel: str) -> Optional['SemVer.Prerelease']:
            if not rel:
                return None

            parts: List[Union[str, int]] = []

            for part_s in rel.split('.'):
                converted_part: Union[str, int]
                try:
                    converted_part = int(part_s)
                except ValueError:
                    converted_part = part_s

                parts.append(converted_part)

            return SemVer.Prerelease(tuple(parts))

        @property
        def parts(self) -> Tuple[Union[str, int], ...]:
            return self._parts

        def __lt__(self, other: object) -> bool:
            if not isinstance(other, SemVer.Prerelease):
                return NotImplemented

            for our_part, other_part in zip(self._parts, other._parts):
                if type(our_part) == type(other_part):  # noqa: E721
                    if our_part < other_part:  # type: ignore
                        return True
                # Number parts are always less than strings.
                elif isinstance(our_part, int):
                    return True

            return len(self._parts) < len(other._parts)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, SemVer.Prerelease):
                return NotImplemented

            return self._parts == other._parts

        def __repr__(self) -> str:
            return f'Prerelease(parts={self.parts})'

    major: int
    minor: int
    patch: int
    prerelease: Optional[Prerelease] = None

    @staticmethod
    def parse(version: str) -> 'SemVer':
        match = SemVer._SEMVER_RE.match(version)
        if match is None:
            raise ValueError(f'Invalid semver version: {version}')

        major, minor, patch = map(int, match.groups()[:3])
        prerelease = SemVer.Prerelease.parse(match.group('prerelease'))

        return SemVer(major, minor, patch, prerelease)


class PackageSource:
    pass


@dataclass(frozen=True, eq=True)
class PackageFileSource(PackageSource):
    integrity: Optional[Integrity]


@dataclass(frozen=True, eq=True)
class PackageURLSource(PackageFileSource):
    resolved: str

    async def retrieve_integrity(self) -> Integrity:
        if self.integrity is not None:
            return self.integrity
        else:
            url = self.resolved
            assert url is not None, 'registry source has no resolved URL'
            metadata = await RemoteUrlMetadata.get(url, cachable=True)
            return metadata.integrity


@dataclass(frozen=True, eq=True)
class RegistrySource(PackageFileSource):
    pass


@dataclass(frozen=True, eq=True)
class ResolvedSource(RegistrySource, PackageURLSource):
    pass


@dataclass(frozen=True, eq=True)
class GitSource(PackageSource):
    original: str
    url: str
    commit: str
    from_: Optional[str]


@dataclass(frozen=True, eq=True)
class NamedGitSource:
    package_name: str
    git_source: GitSource


@dataclass(frozen=True, eq=True)
class LocalSource(PackageSource):
    path: str


@dataclass(frozen=True, eq=True)
class Lockfile:
    path: Path
    version: int


class Package(NamedTuple):
    name: str
    version: str
    source: PackageSource
    lockfile: Lockfile
