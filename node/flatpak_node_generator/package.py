from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple, Union

import functools
import re

from .integrity import Integrity
from .url_metadata import RemoteUrlMetadata


class SemVer(NamedTuple):
    # Note that we ignore the metadata part, since all we do is version
    # comparisons.
    _SEMVER_RE = re.compile(r'(\d+)\.(\d+)\.(\d+)(?:-(?P<prerelease>[^+]+))?')

    @functools.total_ordering
    class Prerelease:
        def __init__(self, parts: Tuple[Union[str, int]]) -> None:
            self._parts = parts

        @staticmethod
        def parse(rel: str) -> Optional['SemVer.Prerelease']:
            if not rel:
                return None

            parts: List[Union[str, int]] = []

            for part in rel.split('.'):
                try:
                    part = int(part)
                except ValueError:
                    pass

                parts.append(part)

            return SemVer.Prerelease(tuple(parts)[:2])

        @property
        def parts(self) -> Tuple[Union[str, int]]:
            return self._parts

        def __lt__(self, other: 'SemVer.Prerelease'):
            for our_part, other_part in zip(self._parts, other._parts):
                if type(our_part) == type(other_part):
                    if our_part < other_part:  # type: ignore
                        return True
                # Number parts are always less than strings.
                elif isinstance(our_part, int):
                    return True

            return len(self._parts) < len(other._parts)

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


class ResolvedSource(NamedTuple):
    resolved: str
    integrity: Optional[Integrity]

    async def retrieve_integrity(self) -> Integrity:
        if self.integrity is not None:
            return self.integrity
        else:
            url = self.resolved
            assert url is not None, 'registry source has no resolved URL'
            metadata = await RemoteUrlMetadata.get(url, cachable=True)
            return metadata.integrity


class GitSource(NamedTuple):
    original: str
    url: str
    commit: str
    from_: Optional[str]


PackageSource = Union[ResolvedSource, GitSource]


class Package(NamedTuple):
    name: str
    version: str
    source: PackageSource
    lockfile: Path
