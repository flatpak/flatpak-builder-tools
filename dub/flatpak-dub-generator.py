#!/usr/bin/env python3

__license__ = 'MIT'
import json
import urllib.request
import urllib.parse
import hashlib
import logging
import argparse

REGISTRY_URL = "https://code.dlang.org/"

def get_remote_sha256(url):
    logging.info(f"Calculating sha256 of {url}")
    response = urllib.request.urlopen(url)
    sha256 = hashlib.sha256()
    while True:
        data = response.read(4096)
        if not data:
            break
        sha256.update(data)
    return sha256.hexdigest()

def load_dub_selections(dub_selections_file="dub.selections.json"):
    with open(dub_selections_file, "r") as f:
        dub_selections = json.load(f)
    assert dub_selections.get("fileVersion") == 1
    return dub_selections

def generate_sources(dub_selections):
    sources = []
    local_packages = []

    for name, version_obj in dub_selections["versions"].items():
        if isinstance(version_obj, dict):
            if "path" in version_obj:
                logging.warning(f"Skipping path based dependency {name}")
                continue
            version = version_obj["version"]
        else:
            version = version_obj
        dl_url = urllib.parse.urljoin(REGISTRY_URL, f"/packages/{name}/{version}.zip")
        sources += [{
            "type": "archive",
            "url": dl_url,
            "sha256": get_remote_sha256(dl_url),
            "dest": f".flatpak-dub/{name}-{version}"
        }]
        local_packages += [{
            "name": name,
            "version": version,
            "path": f"@builddir@/.flatpak-dub/{name}-{version}"
        }]
    sources += [
        {
            "type": "file",
            "url": "data:" + urllib.parse.quote(json.dumps(local_packages)),
            "dest": ".dub/packages",
            "dest-filename": "local-packages.json"
        },
        {
            "type": "shell",
            "commands": [
                "sed \"s|@builddir@|$(pwd)|g\" -i .dub/packages/local-packages.json"
            ]
        }
    ]

    return sources

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dub_selections_file', help='Path to the dub.selections.json file')
    parser.add_argument('-o', '--output', required=False, help='Where to write generated sources')
    args = parser.parse_args()
    if args.output is not None:
        outfile = args.output
    else:
        outfile = 'generated-sources.json'

    generated_sources = generate_sources(load_dub_selections(args.dub_selections_file))
    with open(outfile, 'w') as out:
        json.dump(generated_sources, out, indent=4, sort_keys=False)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
