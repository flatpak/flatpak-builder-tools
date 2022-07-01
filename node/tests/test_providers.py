from pathlib import Path

import itertools

from conftest import FlatpakBuilder, ProviderFactorySpec
from flatpak_node_generator.manifest import ManifestGenerator


async def test_minimal_git(
    flatpak_builder: FlatpakBuilder,
    provider_factory_spec: ProviderFactorySpec,
    node_version: int,
) -> None:
    with ManifestGenerator() as gen:
        await provider_factory_spec.generate_modules('minimal-git', gen, node_version)

    flatpak_builder.build(
        sources=itertools.chain(gen.ordered_sources()),
        commands=[
            provider_factory_spec.install_command,
            """node -e 'require("nop")'""",
        ],
        use_node=node_version,
    )


async def test_local(
    flatpak_builder: FlatpakBuilder,
    provider_factory_spec: ProviderFactorySpec,
    node_version: int,
    shared_datadir: Path,
) -> None:
    with ManifestGenerator() as gen:
        await provider_factory_spec.generate_modules('local', gen, node_version)

    flatpak_builder.build(
        sources=itertools.chain(
            gen.ordered_sources(),
            [
                {
                    'type': 'dir',
                    'path': str(shared_datadir / 'packages' / 'local' / 'subdir'),
                    'dest': 'subdir',
                }
            ],
        ),
        commands=[
            provider_factory_spec.install_command,
            """node -e 'require("subdir").sayHello()'""",
        ],
        use_node=node_version,
    )

    hello_txt = flatpak_builder.module_dir / 'hello.txt'
    assert hello_txt.read_text() == 'Hello!'


async def test_local_link(
    flatpak_builder: FlatpakBuilder,
    yarn_provider_factory_spec: ProviderFactorySpec,
    node_version: int,
    shared_datadir: Path,
) -> None:
    with ManifestGenerator() as gen:
        await yarn_provider_factory_spec.generate_modules(
            'local-link-yarn', gen, node_version
        )

    flatpak_builder.build(
        sources=itertools.chain(
            gen.ordered_sources(),
            [
                {
                    'type': 'dir',
                    'path': str(
                        shared_datadir / 'packages' / 'local-link-yarn' / 'subdir'
                    ),
                    'dest': 'subdir',
                }
            ],
        ),
        commands=[
            yarn_provider_factory_spec.install_command,
            """node -e 'require("subdir").sayHello()'""",
        ],
        use_node=node_version,
    )

    hello_txt = flatpak_builder.module_dir / 'hello.txt'
    assert hello_txt.read_text() == 'Hello!'


async def test_special_electron(
    flatpak_builder: FlatpakBuilder,
    provider_factory_spec: ProviderFactorySpec,
    node_version: int,
) -> None:
    with ManifestGenerator() as gen:
        await provider_factory_spec.generate_modules('electron', gen, node_version)

    flatpak_builder.build(
        sources=itertools.chain(gen.ordered_sources()),
        commands=[provider_factory_spec.install_command],
        use_node=node_version,
    )

    electron_version = (
        flatpak_builder.module_dir / 'node_modules' / 'electron' / 'dist' / 'version'
    )
    assert electron_version.read_text() == '18.3.4'
