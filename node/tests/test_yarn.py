from pathlib import Path

from conftest import ProviderFactorySpec
from flatpak_node_generator.integrity import Integrity
from flatpak_node_generator.package import GitSource, Package, ResolvedSource
from flatpak_node_generator.providers.yarn import YarnLockfileProvider

TEST_LOCKFILE = """
# random comment
"@scope/name@^1.0.0":
  version "1.1.5"
  # random comment
  resolved "https://registry.yarnpkg.com/@scope/name/-/name-1.1.tgz#e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e"
  integrity sha512-Ortmd680rFfAylgo/ZT52IbCbOWajOYOz2d4B5Qj3M/x1vGctlWAXVYJjm04oacQ3uWVI+7XUR5ankuMyzpGhg==
  dependencies:
    thing "^2.0.0"

    bling "~2.2.0"

# random comment

thing@^2.0.0:
  version "2.0.1"
  resolved "https://codeload.github.com/flathub/thing/tar.gz/7448d8798a4380162d4b56f9b452e2f6f9e24e7a"

bling@~2.2.0:
  "version" "2.2.0"
  "resolved" "https://registry.yarnpkg.com/bling/-/name-1.1.tgz#a3db5c13ff90a36963278c6a39e4ee3c22e2a436"
  "integrity" sha512-K1nRedmBWZT2hzg6iG6jQQmIl1bvylqycxjMZ84qISYdEvpv7muMcW9yIU6tVe4NeJ1sNc/5d9QO9XKLqRiKgA==

"@scope/zing@git+https://somewhere.place/scope/zing":
  version "2.0.1"
  resolved "git+https://somewhere.place/scope/zing#9c6b057a2b9d96a4067a749ee3b3b0158d390cf1"
"""


def test_lockfile_parsing(tmp_path: Path) -> None:
    lockfile_provider = YarnLockfileProvider()

    yarn_lock = tmp_path / 'yarn.lock'
    yarn_lock.write_text(TEST_LOCKFILE)

    packages = list(lockfile_provider.process_lockfile(yarn_lock))

    assert packages == [
        Package(
            lockfile=yarn_lock,
            name='@scope/name',
            version='1.1.5',
            source=ResolvedSource(
                resolved='https://registry.yarnpkg.com/@scope/name/-/name-1.1.tgz#e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e',
                integrity=Integrity(
                    'sha512',
                    '3abb6677af34ac57c0ca5828fd94f9d886c26ce59a8ce60ecf6778079423dccff1d6f19cb655805d56098e6d38a1a710dee59523eed7511e5a9e4b8ccb3a4686',
                ),
            ),
        ),
        Package(
            lockfile=yarn_lock,
            name='thing',
            version='2.0.1',
            source=ResolvedSource(
                resolved='https://codeload.github.com/flathub/thing/tar.gz/7448d8798a4380162d4b56f9b452e2f6f9e24e7a',
                integrity=None,
            ),
        ),
        Package(
            lockfile=yarn_lock,
            name='bling',
            version='2.2.0',
            source=ResolvedSource(
                resolved='https://registry.yarnpkg.com/bling/-/name-1.1.tgz#a3db5c13ff90a36963278c6a39e4ee3c22e2a436',
                integrity=Integrity(
                    'sha512',
                    '2b59d179d9815994f687383a886ea34109889756efca5ab27318cc67ce2a21261d12fa6fee6b8c716f72214ead55ee0d789d6c35cff977d40ef5728ba9188a80',
                ),
            ),
        ),
        Package(
            lockfile=yarn_lock,
            name='@scope/zing',
            version='2.0.1',
            source=GitSource(
                original='git+https://somewhere.place/scope/zing#9c6b057a2b9d96a4067a749ee3b3b0158d390cf1',
                url='https://somewhere.place/scope/zing',
                commit='9c6b057a2b9d96a4067a749ee3b3b0158d390cf1',
                from_=None,
            ),
        ),
    ]
