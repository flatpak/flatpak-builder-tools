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
