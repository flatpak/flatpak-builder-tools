from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Dict, Iterator, List, Optional, Tuple

import dataclasses
import urllib.parse

from ..manifest import ManifestGenerator
from ..node_headers import NodeHeaders
from ..package import GitSource, Package
from .special import SpecialSourceProvider

_GIT_SCHEMES: Dict[str, Dict[str, str]] = {
    'github': {'scheme': 'https', 'netloc': 'github.com'},
    'gitlab': {'scheme': 'https', 'netloc': 'gitlab.com'},
    'bitbucket': {'scheme': 'https', 'netloc': 'bitbucket.com'},
    'git': {},
    'git+http': {'scheme': 'http'},
    'git+https': {'scheme': 'https'},
}


class LockfileProvider:
    def parse_git_source(self, version: str, from_: Optional[str] = None) -> GitSource:
        # https://github.com/microsoft/pyright/issues/1589
        # pyright: reportPrivateUsage=false

        original_url = urllib.parse.urlparse(version)
        assert original_url.scheme and original_url.path and original_url.fragment

        replacements = _GIT_SCHEMES.get(original_url.scheme, {})
        new_url = original_url._replace(fragment='', **replacements)
        # Replace e.g. git:github.com/owner/repo with git://github.com/owner/repo
        if not new_url.netloc:
            path = new_url.path.split('/')
            new_url = new_url._replace(netloc=path[0], path='/'.join(path[1:]))

        return GitSource(
            original=original_url.geturl(),
            url=new_url.geturl(),
            commit=original_url.fragment,
            from_=from_,
        )

    def process_lockfile(self, lockfile: Path) -> Iterator[Package]:
        raise NotImplementedError()


@dataclass
class Config:
    data: Dict[str, Any] = dataclasses.field(default_factory=lambda: {})

    def merge_new_keys_only(self, other: Dict[str, Any]) -> None:
        for key, value in other.items():
            if key not in self.data:
                self.data[key] = value

    def get_node_headers(self) -> Optional[NodeHeaders]:
        if 'target' not in self.data:
            return None
        target = self.data['target']
        runtime = self.data.get('runtime')
        disturl = self.data.get('disturl')

        assert isinstance(runtime, str) and isinstance(disturl, str)

        return NodeHeaders.with_defaults(target, runtime, disturl)

    def get_registry_for_scope(self, scope: str) -> Optional[str]:
        return self.data.get(f'{scope}:registry')


class ConfigProvider:
    @property
    def _filename(self) -> str:
        raise NotImplementedError()

    def parse_config(self, path: Path) -> Dict[str, Any]:
        raise NotImplementedError()

    def load_config(self, lockfile: Path) -> Config:
        config = Config()

        for parent in lockfile.parents:
            path = parent / self._filename
            if path.exists():
                config.merge_new_keys_only(self.parse_config(path))

        return config


class ModuleProvider(ContextManager['ModuleProvider']):
    async def generate_package(self, package: Package) -> None:
        raise NotImplementedError()


class ProviderFactory:
    def create_lockfile_provider(self) -> LockfileProvider:
        raise NotImplementedError()

    def create_config_provider(self) -> ConfigProvider:
        raise NotImplementedError()

    def create_module_provider(
        self,
        gen: ManifestGenerator,
        special: SpecialSourceProvider,
        lockfile_configs: Dict[Path, Config],
    ) -> ModuleProvider:
        raise NotImplementedError()
