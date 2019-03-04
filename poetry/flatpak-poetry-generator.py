#!/usr/bin/env python3

__license__ = "MIT"

import argparse
import json
import sys
import urllib.parse
import urllib.request

import toml


def get_pypi_source(name: str, version: str, hashes: list) -> tuple:
    url = "https://pypi.python.org/pypi/{}/json".format(name)
    print("Extracting download url and hash for {}, version {}".format(name, version))
    with urllib.request.urlopen(url) as response:
        body = json.loads(response.read().decode("utf-8"))
        for release, source_list in body["releases"].items():
            if release == version:
                for source in source_list:
                    if (
                        source["packagetype"] == "bdist_wheel"
                        and "py3" in source["python_version"]
                        and source["digests"]["sha256"] in hashes
                    ):
                        return source["url"], source["digests"]["sha256"]
                for source in source_list:
                    if (
                        source["packagetype"] == "sdist"
                        and "source" in source["python_version"]
                        and source["digests"]["sha256"] in hashes
                    ):
                        return source["url"], source["digests"]["sha256"]
        else:
            raise Exception("Failed to extract url and hash from {}".format(url))


def get_module_sources(lockfile, include_devel=True):
    sources = []
    parsed_toml = toml.load(lockfile)
    all_hashes = parsed_toml["metadata"]["hashes"]
    for section, packages in parsed_toml.items():
        if section == "package":
            for package in packages:
                if (
                    package["category"] == "dev"
                    and include_devel
                    or package["category"] == "main"
                ):
                    hashes = all_hashes[package["name"]]
                    url, hash = get_pypi_source(
                        package["name"], package["version"], hashes
                    )
                    source = {"type": "file", "url": url, "sha256": hash}
                    sources.append(source)
    return sources


def main():
    parser = argparse.ArgumentParser(description="Flatpak Poetry generator")
    parser.add_argument("lockfile", type=str)
    parser.add_argument(
        "-o", type=str, dest="outfile", default="generated-poetry-sources.json"
    )
    parser.add_argument("--production", action="store_true", default=False)
    parser.add_argument("--recursive", action="store_true", default=False)
    args = parser.parse_args()

    include_devel = not args.production

    outfile = args.outfile

    if args.recursive:
        import glob

        lockfiles = glob.iglob("**/%s" % args.lockfile, recursive=True)
    else:
        lockfiles = [args.lockfile]

    sources = []
    for lockfile in lockfiles:
        print('Scanning "%s" ' % lockfile, file=sys.stderr)

        with open(lockfile, "r") as f:
            s = get_module_sources(f, include_devel=include_devel)
            sources += s

        print(" ... %d new entries" % len(s), file=sys.stderr)

    print('Writing to "%s"' % outfile)
    with open(outfile, "w") as f:
        f.write(json.dumps(sources, indent=4))


if __name__ == "__main__":
    main()
