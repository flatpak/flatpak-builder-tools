# Flatpak PIP Generator

Tool to automatically generate `flatpak-builder` manifest json from a `pip`
package-name.

This requires `requirements-parser` which can be installed on your host with `pip3 install --user requirements-parser`.

## Usage

`flatpak-pip-generator --runtime='org.freedesktop.Sdk//22.08' foo` which generates `python3-foo.json` and can be included in a manifest like:

```json
"modules": [
  "python3-foo.json",
  {
    "name": "other-modules"
  }
]
```

You can also list multiple packages in single command:
```
flatpak-pip-generator --runtime='org.freedesktop.Sdk//22.08' foo\>=1.0.0,\<2.0.0 bar
```

If your project contains a [requirements.txt file](https://pip.readthedocs.io/en/stable/user_guide/#requirements-files) with all the project dependencies, you can use
```
flatpak-pip-generator --runtime='org.freedesktop.Sdk//22.08' --requirements-file='/the/path/to/requirements.txt' --output pypi-dependencies
```

You can use that in your manifest like
```json
"modules": [
  "pypi-dependencies.json",
  {
    "name": "other-modules"
  }
]
```

## Options

```
usage: flatpak-pip-generator.py [-h] [--python2] [--cleanup {scripts,all}]
                                [--requirements-file REQUIREMENTS_FILE]
                                [--pyproject-file PYPROJECT_FILE] [--build-only]
                                [--build-isolation][--ignore-installed IGNORE_INSTALLED]
                                [--checker-data] [--output OUTPUT] [--runtime RUNTIME]
                                [--yaml] [--ignore-errors] [--ignore-pkg [IGNORE_PKG ...]]
                                [packages ...]

positional arguments:
  packages

options:
  -h, --help            show this help message and exit
  --python2             Look for a Python 2 package
  --cleanup {scripts,all}
                        Select what to clean up after build
  --requirements-file, -r REQUIREMENTS_FILE
                        Specify requirements.txt file. Cannot be used with pyproject file.
  --pyproject-file PYPROJECT_FILE
                        Specify pyproject.toml file. Cannot be used with requirements file.
  --build-only          Clean up all files after build
  --build-isolation     Do not disable build isolation. Mostly useful on pip that does't support the feature.
  --ignore-installed IGNORE_INSTALLED
                        Comma-separated list of package names for which pip should ignore already installed packages.
                        Useful when the package is installed in the SDK but not in the runtime.
  --checker-data        Include x-checker-data in output for the "Flatpak External Data Checker"
  --output, -o OUTPUT   Specify output file name
  --runtime RUNTIME     Specify a flatpak to run pip inside of a sandbox, ensures python version compatibility.
                        Format: $RUNTIME_ID//$RUNTIME_BRANCH
  --yaml                Use YAML as output format instead of JSON
  --ignore-errors       Ignore errors when downloading packages
  --ignore-pkg [IGNORE_PKG ...]
                        Ignore packages when generating the manifest. Needs to be specified
                        with version constraints if present (e.g. --ignore-pkg 'foo>=3.0.0' 'baz>=21.0').
```

## Development

1. Install uv https://docs.astral.sh/uv/getting-started/installation/
2. `uv sync -v --all-groups --frozen`
3. Format and lint: `uv run ruff format && uv run ruff check --fix --exit-non-zero-on-fix`
4. Type check: `uv run mypy .`
