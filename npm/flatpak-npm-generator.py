#!/usr/bin/env python3

import argparse
import sys
import json
import base64
import binascii
import urllib.request
import urllib.parse

electron_arches = {
    "ia32": "i386",
    "x64": "x86_64",
    "arm": "arm"
}


def getModuleSources(module, seen=None, include_devel=True):
    sources = []
    seen = seen or {}

    version = module.get("version", "")
    added_url = None

    if module.get("dev", False) and not include_devel:
        pass
    if module.get("bundled", False):
        pass
    elif module.get("resolved", False) or (version.startswith("http") and not version.endswith(".git")):
        if module.get("resolved", False):
            url = module["resolved"]
        else:
            url = module["version"]
        added_url = url
        integrity = module["integrity"]
        if integrity not in seen:
            seen[integrity] = True
            integrity_type, integrity_base64 = integrity.split("-", 2)
            hex = binascii.hexlify(base64.b64decode(integrity_base64)).decode('utf8')
            source = {"type": "file",
                      "url": url,
                      "dest": "npm-cache/_cacache/content-v2/%s/%s/%s" % (integrity_type, hex[0:2], hex[2:4]),
                      "dest-filename": hex[4:]}
            source[integrity_type] = hex
            sources.append(source)

    if added_url:
        # Special case electron, adding sources for the electron binaries
        tarname = added_url[added_url.rfind("/")+1:]
        if tarname.startswith("electron-") and tarname[len("electron-")].isdigit() and tarname.endswith(".tgz"):
            electron_version = tarname[len("electron-"):-len(".tgz")]

            shasums_url = "https://github.com/electron/electron/releases/download/v" + electron_version + "/SHASUMS256.txt"
            f = urllib.request.urlopen(shasums_url)
            shasums = {}
            shasums_data = f.read().decode("utf8")
            for line in shasums_data.split('\n'):
                l = line.split()
                if len(l) == 2:
                    shasums[l[1][1:]] = l[0]

            mini_shasums = ""
            for arch in electron_arches.keys():
                basename = "electron-v" + electron_version + "-linux-" + arch + ".zip"
                source = {"type": "file",
                          "only-arches": [electron_arches[arch]],
                          "url": "https://github.com/electron/electron/releases/download/v" + electron_version + "/" + basename,
                          "sha256": shasums[basename],
                          "dest": "npm-cache"}
                sources.append(source)
                mini_shasums = mini_shasums + shasums[basename] + " *" + basename + "\n"
            source = {"type": "file",
                      "url": "data:" + urllib.parse.quote(mini_shasums.encode("utf8")),
                      "dest": "npm-cache",
                      "dest-filename": "SHASUMS256.txt-" + electron_version}
            sources.append(source)

    if "dependencies" in module:
        deps = module["dependencies"]
        for dep in deps:
            child_sources = getModuleSources(deps[dep], seen, include_devel=include_devel)
            sources = sources + child_sources

    return sources


def main():
    parser = argparse.ArgumentParser(description='Flatpak NPM generator')
    parser.add_argument('lockfile', type=str)
    parser.add_argument('-o', type=str, dest='outfile', default='generated-sources.json')
    parser.add_argument('--production', action='store_true', default=False)
    parser.add_argument('--recursive', action='store_true', default=False)
    args = parser.parse_args()

    include_devel = not args.production

    outfile = args.outfile

    if args.recursive:
        import glob
        lockfiles = glob.iglob('**/%s' % args.lockfile, recursive=True)
    else:
        lockfiles = [args.lockfile]

    sources = []
    seen = {}
    for lockfile in lockfiles:
        print('Scanning "%s" ' % lockfile, file=sys.stderr)

        with open(lockfile, 'r') as f:
            root = json.loads(f.read())

        s = getModuleSources(root, seen, include_devel=include_devel)
        sources += s
        print(' ... %d new entries' % len(s), file=sys.stderr)

    print('%d total entries' % len(sources), file=sys.stderr)

    print('Writing to "%s"' % outfile)
    with open(outfile, 'w') as f:
        f.write(json.dumps(sources, indent=4))


if __name__ == '__main__':
    main()
