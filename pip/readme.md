# Flatpak PIP Generator

Tool to automatically generate `flatpak-builder` manifest json from a `pip` package-name.

## Usage

`flatpak-pip-generator foo` which generates `foo.json` and can be included in a manifest like:

```json
"modules": [
  "foo.json",
  {
    "name": "other-modules"
  }
]
```

You can also list multiple packages in single command.

If your project contains a [requirements.txt file](https://pip.readthedocs.io/en/stable/user_guide/#requirements-files) with all the project dependencies, you can use 
```
flatpak-pip-generator --requirements-file=/the/path/to/requirements.txt --output pypi-dependencies
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
