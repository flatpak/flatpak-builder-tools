#!/usr/bin/env python3

__license__ = "MIT"

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import suppress
from typing import Any, TextIO

try:
    import requirements
except ImportError:
    sys.exit(
        'Requirements module is not installed. Run "pip install requirements-parser"'
    )

parser = argparse.ArgumentParser()
parser.add_argument("packages", nargs="*")
parser.add_argument(
    "--python2", action="store_true", help="Look for a Python 2 package"
)
parser.add_argument(
    "--cleanup", choices=["scripts", "all"], help="Select what to clean up after build"
)
parser.add_argument("--requirements-file", "-r", help="Specify requirements.txt file")
parser.add_argument("--pyproject-file", help="Specify pyproject.toml file")
parser.add_argument(
    "--build-only",
    action="store_const",
    dest="cleanup",
    const="all",
    help="Clean up all files after build",
)
parser.add_argument(
    "--build-isolation",
    action="store_true",
    default=False,
    help=(
        "Do not disable build isolation. "
        "Mostly useful on pip that does't "
        "support the feature."
    ),
)
parser.add_argument(
    "--ignore-installed",
    type=lambda s: s.split(","),
    default="",
    help="Comma-separated list of package names for which pip "
    "should ignore already installed packages. Useful when "
    "the package is installed in the SDK but not in the "
    "runtime.",
)
parser.add_argument(
    "--checker-data",
    action="store_true",
    help='Include x-checker-data in output for the "Flatpak External Data Checker"',
)
parser.add_argument("--output", "-o", help="Specify output file name")
parser.add_argument(
    "--runtime",
    help=(
        "Specify a flatpak to run pip inside of a sandbox, "
        "ensures python version compatibility"
    ),
)
parser.add_argument(
    "--yaml", action="store_true", help="Use YAML as output format instead of JSON"
)
parser.add_argument(
    "--ignore-errors",
    action="store_true",
    help="Ignore errors when downloading packages",
)
parser.add_argument(
    "--ignore-pkg",
    nargs="*",
    help=(
        "Ignore a package when generating the manifest. "
        "Can only be used with a requirements file"
    ),
)
opts = parser.parse_args()

if opts.requirements_file and opts.pyproject_file:
    sys.exit("Can't use both requirements and pyproject files at the same time")

if opts.pyproject_file:
    try:
        from tomllib import load as toml_load
    except ModuleNotFoundError:
        try:
            from tomli import load as toml_load  # type: ignore
        except ModuleNotFoundError:
            sys.exit('tomli modules is not installed. Run "pip install tomli"')

if opts.yaml:
    try:
        import yaml
    except ImportError:
        sys.exit('PyYAML modules is not installed. Run "pip install PyYAML"')


def get_pypi_url(name: str, filename: str) -> str:
    url = f"https://pypi.org/pypi/{name}/json"
    print("Extracting download url for", name)
    with urllib.request.urlopen(url) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
        for release in body["releases"].values():
            for source in release:
                if source["filename"] == filename:
                    return str(source["url"])
        raise Exception(f"Failed to extract url from {url}")


def get_tar_package_url_pypi(name: str, version: str) -> str:
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    with urllib.request.urlopen(url) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
        for ext in ["bz2", "gz", "xz", "zip", "none-any.whl"]:
            for source in body["urls"]:
                if source["url"].endswith(ext):
                    return str(source["url"])
        err = f"Failed to get {name}-{version} source from {url}"
        raise Exception(err)


def get_package_name(filename: str) -> str:
    if filename.endswith(("bz2", "gz", "xz", "zip")):
        segments = filename.split("-")
        if len(segments) == 2:
            return segments[0]
        return "-".join(segments[: len(segments) - 1])
    if filename.endswith("whl"):
        segments = filename.split("-")
        if len(segments) == 5:
            return segments[0]
        candidate = segments[: len(segments) - 4]
        # Some packages list the version number twice
        # e.g. PyQt5-5.15.0-5.15.0-cp35.cp36.cp37.cp38-abi3-manylinux2014_x86_64.whl
        if candidate[-1] == segments[len(segments) - 4]:
            return "-".join(candidate[:-1])
        return "-".join(candidate)
    raise Exception(
        f"Downloaded filename: {filename} does not end with bz2, gz, xz, zip, or whl"
    )


def get_file_version(filename: str) -> str:
    name = get_package_name(filename)
    segments = filename.split(name + "-")
    version = segments[1].split("-")[0]
    for ext in ["tar.gz", "whl", "tar.xz", "tar.gz", "tar.bz2", "zip"]:
        version = version.replace("." + ext, "")
    return version


def get_file_hash(filename: str) -> str:
    sha = hashlib.sha256()
    print("Generating hash for", filename.split("/")[-1])
    with open(filename, "rb") as f:
        while True:
            data = f.read(1024 * 1024 * 32)
            if not data:
                break
            sha.update(data)
        return sha.hexdigest()


def download_tar_pypi(url: str, tempdir: str) -> None:
    if not url.startswith(("https://", "http://")):
        raise ValueError("URL must be HTTP(S)")

    with urllib.request.urlopen(url) as response:  # noqa: S310
        file_path = os.path.join(tempdir, url.split("/")[-1])
        with open(file_path, "x+b") as tar_file:
            shutil.copyfileobj(response, tar_file)


def parse_continuation_lines(fin: TextIO) -> Iterator[str]:
    for raw_line in fin:
        line = raw_line.rstrip("\n")
        while line.endswith("\\"):
            try:
                line = line[:-1] + next(fin).rstrip("\n")
            except StopIteration:
                sys.exit(
                    "Requirements have a wrong number of line "
                    'continuation characters "\\"'
                )
        yield line


def fprint(string: str) -> None:
    separator = "=" * 72  # Same as `flatpak-builder`
    print(separator)
    print(string)
    print(separator)


packages = []
if opts.requirements_file:
    requirements_file_input = os.path.expanduser(opts.requirements_file)
    try:
        with open(requirements_file_input) as in_req_file:
            reqs = parse_continuation_lines(in_req_file)
            reqs_as_str = "\n".join([r.split("--hash")[0] for r in reqs])
            reqs_list_raw = reqs_as_str.splitlines()
            py_version_regex = re.compile(
                r";.*python_version .+$"
            )  # Remove when pip-generator can handle python_version
            reqs_list = [py_version_regex.sub("", p) for p in reqs_list_raw]
            if opts.ignore_pkg:
                reqs_new = "\n".join(i for i in reqs_list if i not in opts.ignore_pkg)
            else:
                reqs_new = reqs_as_str
            packages = list(requirements.parse(reqs_new))
            with tempfile.NamedTemporaryFile(
                "w", delete=False, prefix="requirements."
            ) as temp_req_file:
                temp_req_file.write(reqs_new)
                requirements_file_output = temp_req_file.name
    except FileNotFoundError as err:
        print(err)
        sys.exit(1)

elif opts.pyproject_file:
    pyproject_file = os.path.expanduser(opts.pyproject_file)
    with open(pyproject_file, "rb") as f:
        pyproject_data = toml_load(f)
    dependencies = pyproject_data.get("project", {}).get("dependencies", [])
    packages = list(requirements.parse("\n".join(dependencies)))
    with tempfile.NamedTemporaryFile(
        "w", delete=False, prefix="requirements."
    ) as req_file:
        req_file.write("\n".join(dependencies))
        requirements_file_output = req_file.name

elif opts.packages:
    packages = list(requirements.parse("\n".join(opts.packages)))
    with tempfile.NamedTemporaryFile(
        "w", delete=False, prefix="requirements."
    ) as req_file:
        req_file.write("\n".join(opts.packages))
        requirements_file_output = req_file.name
elif not len(sys.argv) > 1:
    sys.exit("Please specifiy either packages or requirements file argument")
else:
    sys.exit("This option can only be used with requirements file")

for i in packages:
    if i["name"].lower().startswith("pyqt"):
        print("PyQt packages are not supported by flapak-pip-generator")
        print("However, there is a BaseApp for PyQt available, that you should use")
        print(
            "Visit https://github.com/flathub/com.riverbankcomputing.PyQt.BaseApp "
            "for more information"
        )
        sys.exit(0)

with open(requirements_file_output) as in_req_file:
    use_hash = "--hash=" in in_req_file.read()

python_version = "2" if opts.python2 else "3"
pip_executable = "pip2" if opts.python2 else "pip3"

if opts.runtime:
    flatpak_cmd = [
        "flatpak",
        "--devel",
        "--share=network",
        "--filesystem=/tmp",
        f"--command={pip_executable}",
        "run",
        opts.runtime,
    ]
    if opts.requirements_file and os.path.exists(requirements_file_output):
        prefix = os.path.realpath(requirements_file_output)
        flag = f"--filesystem={prefix}"
        flatpak_cmd.insert(1, flag)
else:
    flatpak_cmd = [pip_executable]

output_path = ""
output_package = ""

if opts.output:
    if os.path.isdir(opts.output):
        output_path = opts.output
    else:
        output_path = os.path.dirname(opts.output)
        output_package = os.path.basename(opts.output)

if not output_package:
    if opts.requirements_file:
        output_package = "python{}-{}".format(
            python_version,
            os.path.basename(opts.requirements_file).replace(".txt", ""),
        )
    elif len(packages) == 1:
        output_package = f"python{python_version}-{packages[0].name}"
    else:
        output_package = f"python{python_version}-modules"

output_filename = os.path.join(output_path, output_package)
suffix = ".yaml" if opts.yaml else ".json"
if not output_filename.endswith(suffix):
    output_filename += suffix

modules: list[dict[str, str | list[str] | list[dict[str, Any]]]] = []
vcs_modules: list[dict[str, str | list[str] | list[dict[str, Any]]]] = []
sources = {}

unresolved_dependencies_errors = []

tempdir_prefix = f"pip-generator-{output_package}"
with tempfile.TemporaryDirectory(prefix=tempdir_prefix) as tempdir:
    pip_download = [
        *flatpak_cmd,
        "download",
        "--exists-action=i",
        "--dest",
        tempdir,
        "-r",
        requirements_file_output,
    ]
    if use_hash:
        pip_download.append("--require-hashes")

    fprint("Downloading sources")
    cmd = " ".join(pip_download)
    print(f'Running: "{cmd}"')
    try:
        subprocess.run(pip_download, check=True)
        os.remove(requirements_file_output)
    except subprocess.CalledProcessError:
        os.remove(requirements_file_output)
        print("Failed to download")
        print("Please fix the module manually in the generated file")
        if not opts.ignore_errors:
            print("Ignore the error by passing --ignore-errors")
            raise

        with suppress(FileNotFoundError):
            os.remove(requirements_file_output)

    fprint("Downloading arch independent packages")
    for filename in os.listdir(tempdir):
        if not filename.endswith(("bz2", "any.whl", "gz", "xz", "zip")):
            version = get_file_version(filename)
            name = get_package_name(filename)
            try:
                url = get_tar_package_url_pypi(name, version)
                print(f"Downloading {url}")
                download_tar_pypi(url, tempdir)
            except Exception as err:
                # Can happen if only an arch dependent wheel is
                # available like for wasmtime-27.0.2
                unresolved_dependencies_errors.append(err)
            print("Deleting", filename)
            with suppress(FileNotFoundError):
                os.remove(os.path.join(tempdir, filename))

    files: dict[str, list[str]] = {get_package_name(f): [] for f in os.listdir(tempdir)}

    for filename in os.listdir(tempdir):
        name = get_package_name(filename)
        files[name].append(filename)

    # Delete redundant sources, for vcs sources
    for name, files_list in files.items():
        if len(files_list) > 1:
            zip_source = False
            for fname in files[name]:
                if fname.endswith(".zip"):
                    zip_source = True
            if zip_source:
                for fname in files[name]:
                    if not fname.endswith(".zip"):
                        with suppress(FileNotFoundError):
                            os.remove(os.path.join(tempdir, fname))

    vcs_packages: dict[str, dict[str, str | None]] = {
        str(x.name): {"vcs": x.vcs, "revision": x.revision, "uri": x.uri}
        for x in packages
        if x.vcs and x.name
    }

    fprint("Obtaining hashes and urls")
    for filename in os.listdir(tempdir):
        source: OrderedDict[str, str | dict[str, str]] = OrderedDict()
        name = get_package_name(filename)
        sha256 = get_file_hash(os.path.join(tempdir, filename))
        is_pypi = False

        if name in vcs_packages:
            uri = vcs_packages[name]["uri"]
            if not uri:
                raise ValueError(f"Missing URI for VCS package: {name}")
            revision = vcs_packages[name]["revision"]
            vcs = vcs_packages[name]["vcs"]
            if not vcs:
                raise ValueError(
                    f"Unable to determine VCS type for VCS package: {name}"
                )
            url = "https://" + uri.split("://", 1)[1]
            s = "commit"
            if vcs == "svn":
                s = "revision"
            source["type"] = vcs
            source["url"] = url
            if revision:
                source[s] = revision
            is_vcs = True
        else:
            name = name.casefold()
            is_pypi = True
            url = get_pypi_url(name, filename)
            source["type"] = "file"
            source["url"] = url
            source["sha256"] = sha256
            if opts.checker_data:
                checker_data = {"type": "pypi", "name": name}
                if url.endswith(".whl"):
                    checker_data["packagetype"] = "bdist_wheel"
                source["x-checker-data"] = checker_data
            is_vcs = False
        sources[name] = {"source": source, "vcs": is_vcs, "pypi": is_pypi}

# Python3 packages that come as part of org.freedesktop.Sdk.
system_packages = [
    "cython",
    "easy_install",
    "mako",
    "markdown",
    "meson",
    "pip",
    "pygments",
    "setuptools",
    "six",
    "wheel",
]

fprint("Generating dependencies")
for package in packages:
    if package.name is None:
        print(
            f"Warning: skipping invalid requirement specification {package.line} "
            "because it is missing a name",
            file=sys.stderr,
        )
        print(
            "Append #egg=<pkgname> to the end of the requirement line to fix",
            file=sys.stderr,
        )
        continue
    elif (
        not opts.python2
        and package.name.casefold() in system_packages
        and package.name.casefold() not in opts.ignore_installed
    ):
        print(f"{package.name} is in system_packages. Skipping.")
        continue

    if len(package.extras) > 0:
        extras = "[" + ",".join(extra for extra in package.extras) + "]"
    else:
        extras = ""

    version_list = [x[0] + x[1] for x in package.specs]
    version = ",".join(version_list)

    if package.vcs:
        revision = ""
        if package.revision:
            revision = "@" + package.revision
        pkg = package.uri + revision + "#egg=" + package.name
    else:
        pkg = package.name + extras + version

    dependencies = []
    # Downloads the package again to list dependencies

    tempdir_prefix = f"pip-generator-{package.name}"
    with tempfile.TemporaryDirectory(
        prefix=f"{tempdir_prefix}-{package.name}"
    ) as tempdir:
        pip_download = [
            *flatpak_cmd,
            "download",
            "--exists-action=i",
            "--dest",
            tempdir,
        ]
        try:
            print(f"Generating dependencies for {package.name}")
            subprocess.run([*pip_download, pkg], check=True, stdout=subprocess.DEVNULL)
            for filename in sorted(os.listdir(tempdir)):
                dep_name = get_package_name(filename)
                if (
                    dep_name.casefold() in system_packages
                    and dep_name.casefold() not in opts.ignore_installed
                ):
                    continue
                dependencies.append(dep_name)

        except subprocess.CalledProcessError:
            print(f"Failed to download {package.name}")

    is_vcs = bool(package.vcs)
    package_sources = []
    for dependency in dependencies:
        casefolded = dependency.casefold()
        if casefolded in sources and sources[casefolded].get("pypi") is True:
            source = sources[casefolded]
        elif dependency in sources and sources[dependency].get("pypi") is False:
            source = sources[dependency]
        elif (
            casefolded.replace("_", "-") in sources
            and sources[casefolded.replace("_", "-")].get("pypi") is True
        ):
            source = sources[casefolded.replace("_", "-")]
        elif (
            dependency.replace("_", "-") in sources
            and sources[dependency.replace("_", "-")].get("pypi") is False
        ):
            source = sources[dependency.replace("_", "-")]
        else:
            continue

        if not (not source["vcs"] or is_vcs):
            continue

        package_sources.append(source["source"])

    name_for_pip = "." if package.vcs else pkg

    module_name = f"python{python_version}-{package.name}"

    pip_command = [
        pip_executable,
        "install",
        "--verbose",
        "--exists-action=i",
        "--no-index",
        '--find-links="file://${PWD}"',
        "--prefix=${FLATPAK_DEST}",
        f'"{name_for_pip}"',
    ]
    if package.name in opts.ignore_installed:
        pip_command.append("--ignore-installed")
    if not opts.build_isolation:
        pip_command.append("--no-build-isolation")

    module = OrderedDict(
        [
            ("name", module_name),
            ("buildsystem", "simple"),
            ("build-commands", [" ".join(pip_command)]),
            ("sources", package_sources),
        ]
    )
    if opts.cleanup == "all":
        module["cleanup"] = ["*"]
    elif opts.cleanup == "scripts":
        module["cleanup"] = ["/bin", "/share/man/man1"]

    if package.vcs:
        vcs_modules.append(module)
    else:
        modules.append(module)

modules = vcs_modules + modules
if len(modules) == 1:
    pypi_module = modules[0]
else:
    pypi_module = {
        "name": output_package,
        "buildsystem": "simple",
        "build-commands": [],
        "modules": modules,
    }

print()
with open(output_filename, "w") as output:
    if opts.yaml:

        class OrderedDumper(yaml.Dumper):
            def increase_indent(
                self, flow: bool = False, indentless: bool = False
            ) -> None:
                return super().increase_indent(flow, indentless)

        def dict_representer(
            dumper: yaml.Dumper, data: OrderedDict[str, Any]
        ) -> yaml.nodes.MappingNode:
            return dumper.represent_dict(data.items())

        OrderedDumper.add_representer(OrderedDict, dict_representer)

        output.write(
            "# Generated with flatpak-pip-generator " + " ".join(sys.argv[1:]) + "\n"
        )
        yaml.dump(pypi_module, output, Dumper=OrderedDumper)
    else:
        output.write(json.dumps(pypi_module, indent=4) + "\n")
    print(f"Output saved to {output_filename}")

if len(unresolved_dependencies_errors) != 0:
    print("Unresolved dependencies. Handle them manually")
    for e in unresolved_dependencies_errors:
        print(f"- ERROR: {e}")

    workaround = """Example on how to handle arch dependent wheels:
    - type: file
      url: https://files.pythonhosted.org/packages/79/ae/7e5b85136806f9dadf4878bf73cf223fe5c2636818ba3ab1c585d0403164/numpy-1.26.4-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl
      sha256: 7ab55401287bfec946ced39700c053796e7cc0e3acbef09993a9ad2adba6ca6e
      only-arches:
      - aarch64
    - type: file
      url: https://files.pythonhosted.org/packages/3a/d0/edc009c27b406c4f9cbc79274d6e46d634d139075492ad055e3d68445925/numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
      sha256: 666dbfb6ec68962c033a450943ded891bed2d54e6755e35e5835d63f4f6931d5
      only-arches:
      - x86_64
    """
    raise Exception(
        f"Not all dependencies can be determined. Handle them manually.\n{workaround}"
    )
