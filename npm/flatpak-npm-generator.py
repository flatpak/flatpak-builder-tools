#!/usr/bin/env python3

import argparse
import sys
import json
import base64
import binascii
import urllib.request
import urllib.parse
import re

electron_arches = {
    "ia32": "i386",
    "x64": "x86_64",
    "arm": "arm"
}

def isGitUrl(url):
    return url.startswith("github:") or url.startswith("gitlab:") or url.startswith("bitbucket:") or url.startswith("git")

def getPathandCommitInfo(strippedUrl):
    parsedUrl = {}
    parsedUrl["path"] = re.split(r'#[0-9a-fA-F]*', strippedUrl)[0]
    parsedUrl["commit"] = re.findall(r'#[0-9a-fA-F]*', strippedUrl)[0][1:]
    return parsedUrl;

def parseGitUrl(url):
    if url.startswith("github:"):
        prefixStrippedUrl = re.split("github:", url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["server"] = "https://github.com/"
        parsedUrl["url"] = parsedUrl["server"] + parsedUrl["path"]

    elif url.startswith("gitlab:"):
        prefixStrippedUrl = re.split("gitlab:", url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["server"] = "https://gitlab.com/"
        parsedUrl["url"] = parsedUrl["server"] + parsedUrl["path"]

    elif url.startswith("bitbucket:"):
        prefixStrippedUrl = re.split("bitbucket:", url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["server"] = "https://bitbucket.org/"
        parsedUrl["url"] = parsedUrl["server"] + parsedUrl["path"]

    elif url.startwith("git://"):
        prefixStrippedUrl = re.split(r'\w+\.\w+\/',url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["domain"] = re.findall(r'\w+\.\w+\/',url)[0]
        parsedUrl["protocol"] = "git://"
        parsedUrl["url"] = parsedUrl["protocol"] + parsedUrl["domain"] + parsedUrl["path"]

    elif url.startwith("git+https://"):
        prefixStrippedUrl = re.split(r'\w+\.\w+\/',url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["domain"] = re.findall(r'\w+\.\w+\/',url)[0]
        parsedUrl["protocol"] = "https://"
        parsedUrl["url"] = parsedUrl["protocol"] + parsedUrl["domain"] + parsedUrl["path"]

    elif url.startwith("git+http://"):
        prefixStrippedUrl = re.split(r'\w+\.\w+\/',url)[1]
        parsedUrl = getPathandCommitInfo(prefixStrippedUrl)
        parsedUrl["domain"] = re.findall(r'\w+\.\w+\/',url)[0]
        parsedUrl["protocol"] = "http://"
        parsedUrl["url"] = parsedUrl["protocol"] + parsedUrl["domain"] + parsedUrl["path"]

    elif url.startwith("git+ssh://"):
        print("ssh protocol not supported")
        print("Found url is: " + url)

    return parsedUrl

def getModuleSources(module, name, seen=None, include_devel=True, npm3=False):
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

        if npm3:
            dest = "npm-cache/" + name + "/" + module["version"] + "/"
            destFilename = "package.tgz"
        else:
            dest = "npm-cache/_cacache/content-v2/%s/%s/%s" % (integrity_type, hex[0:2], hex[2:4]),
            destFilename = hex[4:]

        if integrity not in seen:
            seen[integrity] = True
            integrity_type, integrity_base64 = integrity.split("-", 2)
            hex = binascii.hexlify(base64.b64decode(integrity_base64)).decode('utf8')
            source = {"type": "file",
                      "url": url,
                      "dest": dest,
                      "dest-filename": destFilename}
            source[integrity_type] = hex
            sources.append(source)
    elif isGitUrl(module["version"]):
        parsedUrl = parseGitUrl(module["version"])
        print("git package found:")
        print("url: " + parsedUrl["url"])
        print("commit: " + parsedUrl["commit"])

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
            child_sources = getModuleSources(deps[dep], dep, seen, include_devel=include_devel, npm3=npm3)
            sources = sources + child_sources

    return sources


def main():
    parser = argparse.ArgumentParser(description='Flatpak NPM generator')
    parser.add_argument('lockfile', type=str)
    parser.add_argument('-o', type=str, dest='outfile', default='generated-sources.json')
    parser.add_argument('--production', action='store_true', default=False)
    parser.add_argument('--recursive', action='store_true', default=False)
    parser.add_argument('--npm3',action='store_true',default=False)
    args = parser.parse_args()

    include_devel = not args.production

    outfile = args.outfile
    npm3 =args.npm3

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

        s = getModuleSources(root, None, seen, include_devel=include_devel, npm3=npm3)
        sources += s
        print(' ... %d new entries' % len(s), file=sys.stderr)

    print('%d total entries' % len(sources), file=sys.stderr)

    print('Writing to "%s"' % outfile)
    with open(outfile, 'w') as f:
        f.write(json.dumps(sources, indent=4))


if __name__ == '__main__':
    main()
