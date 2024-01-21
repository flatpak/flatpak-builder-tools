# Flatpak Builder Tools

This repository contains a collection of various scripts to aid in using `flatpak-builder`.

Feel free to submit your own scripts that would be useful for others.

The intended usage of the generators is as a submodule used as part of your build
process to generate manifests.

See the sub-directories of the respective tools for more information and licenses.

## Converting JSON to YAML with flatpak-json2yaml.py

 1. Save the contents of `flatpak-json2yaml.py` to any directory.
 2. Execute the following command: `python3 flatpak-json2yaml.py /path/to/sample-file.json --output sample-file.yml`

If you experience any errors with packages, create a virtual environment and install the missing packages.
