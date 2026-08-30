import functools
import os
import platform
import struct


def get_flatpak_arch() -> str:
    machine = platform.machine().lower()
    is_32bit = struct.calcsize('P') * 8 == 32

    if machine in ('x86_64', 'amd64'):
        return 'i386' if is_32bit else 'x86_64'

    if machine in ('i386', 'i486', 'i586', 'i686'):
        return 'i386'

    if machine == 'aarch64':
        return 'aarch64'

    if machine.startswith('arm'):
        return 'arm'

    return machine


@functools.cache
def find_installed_package(sdk_extension: str, *package_path_parts: str) -> str | None:
    try:
        ext_id, version = sdk_extension.split('//')
    except ValueError:
        return None

    flatpak_user_dir = os.environ.get('FLATPAK_USER_DIR')
    if flatpak_user_dir:
        search_roots = [flatpak_user_dir]
    else:
        xdg_data_home = os.environ.get(
            'XDG_DATA_HOME',
            os.path.expanduser('~/.local/share'),
        )
        search_roots = [
            os.path.join(xdg_data_home, 'flatpak'),
            '/var/lib/flatpak',
        ]

    arch = get_flatpak_arch()

    for root in search_roots:
        candidate = os.path.join(
            root,
            'runtime',
            ext_id,
            arch,
            version,
            'active',
            'files',
            'lib',
            'node_modules',
            'npm',
            'node_modules',
            *package_path_parts,
            'package.json',
        )

        if os.path.isfile(candidate):
            return candidate

    return None
