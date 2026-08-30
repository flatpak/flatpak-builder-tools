import functools
import json

from ..sdk_extension import find_installed_package

# See https://github.com/npm/hosted-git-info/pull/327
GITLAB_API_FORMAT_MIN_VERSION = (9, 0, 3)


def _parse_version_tuple(version: str) -> tuple[int, ...] | None:
    parts: list[int] = []
    for part in version.split('.'):
        digits = ''
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            return None
        parts.append(int(digits))
    return tuple(parts)


@functools.cache
def gitlab_uses_api_archive_format(sdk_extension: str | None) -> bool:
    if sdk_extension is None:
        print(
            '\nNo Node SDK extension supplied, assuming current '
            'hosted-git-info GitLab archive URL format'
        )
        return True

    pkg_path = find_installed_package(sdk_extension, 'hosted-git-info')

    if pkg_path is None:
        print(
            f'\nFailed to detect hosted-git-info version from Node SDK '
            f"extension '{sdk_extension}', assuming current GitLab archive "
            f'URL format'
        )
        return True

    try:
        with open(pkg_path, encoding='utf-8') as f:
            data = json.load(f)
            version_str = str(data['version'])
            version = _parse_version_tuple(version_str)
            if version is None:
                raise ValueError(f'unparseable version {version_str!r}')
            uses_api_format = version >= GITLAB_API_FORMAT_MIN_VERSION
            print(
                f"\nDetected hosted-git-info '{version_str}' from SDK "
                f"extension '{sdk_extension}'; using "
                f'{"API" if uses_api_format else "legacy"} GitLab archive URL '
                f'format'
            )
            return uses_api_format
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(
            f'\nFailed to read hosted-git-info version from Node SDK '
            f"extension '{sdk_extension}', assuming current GitLab archive "
            f'URL format: {e}'
        )
        return True
