from pathlib import Path

from flatpak_node_generator.providers.npm import NpmConfigProvider

TEST_CONFIG = r"""
# comment
1 = 1     ; inline comment
; comment
'2' = '2'
"3" = "3"
a = x     # inline comment
b = "x"
c = 'x'
d = "true"
e = false
f = 'null'
g = \;\#\3\4\
"h=1" = 1=2
i
'[1,[2,3],{}]' = '{"4": 5}'

r1[] = a
r1 = b
r2 = c
r2[] = d
"""


def test_config_loading(tmp_path: Path) -> None:
    config_provider = NpmConfigProvider()

    npmrc = tmp_path / '.npmrc'
    npmrc.write_text(TEST_CONFIG)

    config = config_provider.load_config(npmrc / 'lockfile')
    assert config.data == {
        '1': '1',
        '2': 2,
        '3': '3',
        'a': 'x',
        'b': 'x',
        'c': 'x',
        'd': True,
        'e': False,
        'f': None,
        'g': r';#\3\4' + '\\',
        '"h': '1" = 1=2',
        'i': True,
        '1,2,3,[object Object]': {'4': 5},
        'r1': ['a', 'b'],
        'r2': ['c', 'd'],
    }
