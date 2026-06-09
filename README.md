# Flatpak Builder Tools

This repository contains a collection of community-contributed scripts
designed to assist with building applications, without network
access, using [Flatpak Builder][flatpak-builder].

The primary purpose of these scripts is to generate a Flatpak Builder
source or module manifests that can be included in the main
Flatpak Builder manifest.

Please refer to the individual tool subdirectories for documentation,
usage information, and licensing details.

Contributions and new tool submissions are welcome!

Any tool proposed for inclusion must demonstrate a verifiable use
in building a Flatpak package. Submissions must also include appropriate
CI coverage, including formatting, linting, validation, and testing as
appropriate for the language being used to implement the tool.

Anyone wishing to submit or maintain a tool in this repository must add
themselves to the `CODEOWNERS` file. Once added, they will be granted
the appropriate permissions. Requests to become a maintainer of an
existing tool require a prior history of contributions and approval
from the current `CODEOWNER`(s) responsible for that tool.

Please open an issue in this repository for maintainer access.

Please note that some tools here are unmaintained and kept only for
historical reasons. These are marked with a warning label in their
respective README file.

### Contributing guidelines

Please refer to the tool subdirectory for guidelines specific to the
tool if any.

- Commits should be prefixed by the tool it is modifying. As an example
  changes to the node generator should be prefixed by `node:` and
  changes to the cargo generator should be prefixed by `cargo:`. This
  is not a hard requirement but it is advisable to follow this
  convention.

## External Projects

This is a list of similar projects maintained by the community outside
this repository, sorted by language / ecosystem. The requirements to
add a project to this list are the same as above.

### Flutter

 - **flatpak-flutter**: [flatpak-flutter][flatpak-flutter] has been
   developed by [Jan Koudijs][jan-koudijs] and allows to build
   Flutter applications using Flatpak Builder without network access.
   It is used extensively in [Flathub][flathub] for packaging Flutter
   applications.

[flatpak-builder]: https://github.com/flatpak/flatpak-builder
[flatpak-flutter]: https://github.com/TheAppgineer/flatpak-flutter
[jan-koudijs]: https://github.com/JanKoudijs
[flathub]: https://github.com/flathub
