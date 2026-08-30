from __future__ import annotations

import json
from typing import NamedTuple

from .sdk_extension import find_installed_package

NODE_GYP_INSTALL_VERSION = '11'


class NodeHeaders(NamedTuple):
    target: str
    runtime: str
    disturl: str

    @classmethod
    def with_defaults(
        cls,
        target: str,
        runtime: str | None = None,
        disturl: str | None = None,
    ) -> NodeHeaders:
        if runtime is None:
            runtime = 'node'
        if disturl is None:
            if runtime == 'node':
                disturl = 'http://nodejs.org/dist'
            elif runtime == 'electron':
                disturl = 'https://www.electronjs.org/headers'
            else:
                raise ValueError(
                    f"Can't guess `disturl` for {runtime} version {target}"
                )
        return cls(target, runtime, disturl)

    @property
    def url(self) -> str:
        # TODO it may be better to retrieve urls from disturl/index.json
        return f'{self.disturl}/v{self.target}/node-v{self.target}-headers.tar.gz'

    def install_version(self, sdk_extension: str | None = None) -> str:
        if sdk_extension is None:
            print(
                f"\nNo Node SDK extension supplied, using node-gyp installVersion '{NODE_GYP_INSTALL_VERSION}'"
            )
            return NODE_GYP_INSTALL_VERSION

        pkg_path = find_installed_package(sdk_extension, 'node-gyp')

        if pkg_path is None:
            print(
                f'\nFailed to detect node-gyp installVersion from Node SDK extension '
                f"'{sdk_extension}', using '{NODE_GYP_INSTALL_VERSION}'"
            )
            return NODE_GYP_INSTALL_VERSION

        try:
            with open(pkg_path, encoding='utf-8') as f:
                data = json.load(f)
                version = str(data['installVersion'])
                print(
                    f"\nUsing node-gyp installVersion '{version}' "
                    f"from SDK extension '{sdk_extension}'"
                )
                return version
        except json.JSONDecodeError as e:
            print(
                f'\nFailed to read node-gyp installVersion from Node SDK extension '
                f"'{sdk_extension}', using '{NODE_GYP_INSTALL_VERSION}': {e}"
            )
            return NODE_GYP_INSTALL_VERSION
