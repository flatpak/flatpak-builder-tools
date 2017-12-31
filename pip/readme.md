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
