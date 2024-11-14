#!/usr/bin/env python3

__license__ = 'MIT'

import argparse
import hashlib
import json
import logging
import re
import shutil
import sys
import tempfile
from typing import List, Dict, Optional
import urllib.request
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument('packages', nargs='*')
parser.add_argument('--output', '-o',
                    help='Specify output file name', default="maven-sources.json")
parser.add_argument('--repo', '-r', action="append")
parser.add_argument('--verbose', '-v', action='store_true')

def assembleUri(repo: str, groupId: str, artifactId: str, version: str, classifier: Optional[str], extension: str) -> str:
    groupId = groupId.replace(".", "/")
    if(classifier is not None):
        return f'{repo}{groupId}/{artifactId}/{version}/{artifactId}-{version}-{classifier}.{extension}'
    else:
        return f'{repo}{groupId}/{artifactId}/{version}/{artifactId}-{version}.{extension}'

def getFileHash(file) -> str:
    file.seek(0)
    byteData = file.read() # read entire file as bytes
    return hashlib.sha256(byteData).hexdigest()

def parsePomDeps(parsed_pom) -> List[Dict[str, str]]:
    ns = {'POM': 'http://maven.apache.org/POM/4.0.0'}

    result = []

    parent = parsed_pom.find("POM:parent", ns)
    if parent is not None:
        groupId = parent.find("POM:groupId", ns).text
        artifactId = parent.find("POM:artifactId", ns).text
        version = parent.find("POM:version", ns).text

        result.append({
            "groupId": groupId,
            "artifactId": artifactId,
            "version": version
        })

    deps = parsed_pom.findall("POM:dependencies/POM:dependency", ns)
    for dep in deps:
        groupId = dep.find("POM:groupId", ns).text
        artifactId = dep.find("POM:artifactId", ns).text
        version = dep.find("POM:version", ns)

        if(version is None):
            continue

        version = version.text

        result.append({
            "groupId": groupId,
            "artifactId": artifactId,
            "version": version
        })

    return result

def getPackagingType(parsed_pom) -> Optional[str]:
    ns = {'POM': 'http://maven.apache.org/POM/4.0.0'}

    packaging = parsed_pom.find("POM:packaging", ns)
    if packaging is not None and packaging.text == "pom":
        return None # Nothing to download for this

    if packaging is None:
        # jar is default if nothing is specified
        return "jar"

    return packaging.text

modules = []
addedModules = []

def addModule(groupId: str, artifactId: str, version: str, classifier: Optional[str] = None):
    addedModules.append({
        "groupId": groupId,
        "artifactId": artifactId,
        "version": version,
        "classifier": classifier
    })

def downloadAndAdd(repo: str, groupId: str, artifactId: str, version: str, classifier: Optional[str], binaryType: str) -> bool:
    url = assembleUri(repo, groupId, artifactId, version, classifier, binaryType)
    groupId = groupId.replace(".", "/")
    try:
        with urllib.request.urlopen(url) as response:
            with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                shutil.copyfileobj(response, tmp_file)

                modules.append({
                   "type": "file",
                   "url": url,
                   "sha256": getFileHash(tmp_file),
                   "dest": f"maven-local/{groupId}/{artifactId}/{version}"
                })

                return True
    except urllib.error.HTTPError:
        logging.warning("Unable to download %s file for %s", binaryType, artifactId)
        return False

def parseGradleMetadata(repo: str, groupId: str, artifactId: str, version: str) -> bool:
    url = assembleUri(repo, groupId, artifactId, version, None, "module")
    groupId = groupId.replace(".", "/")
    try:
        with urllib.request.urlopen(url) as response:
            with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                shutil.copyfileobj(response, tmp_file)

                tmp_file.seek(0)
                gradle_meta = json.loads(tmp_file.read().decode('utf-8'))
                for variant in gradle_meta["variants"]:
                    if "files" not in variant:
                        continue
                    for file in variant["files"]:
                        modules.append({
                           "type": "file",
                           "url": f'{repo}{groupId}/{artifactId}/{version}/{file["url"]}',
                           "sha256": file["sha256"],
                           "dest": f'maven-local/{groupId}/{artifactId}/{version}'
                        })

                modules.append({
                   "type": "file",
                   "url": url,
                   "sha256": getFileHash(tmp_file),
                   "dest": f"maven-local/{groupId}/{artifactId}/{version}"
                })

                return True
    except urllib.error.HTTPError:
        logging.warning("Unable to get the extended Gradle module metadata for %s", artifactId)
        return False

def parseProperties(repos: list[str], groupId: str, artifactId: str, version:str) -> Dict[str, str]:
    result = dict()

    for repo in repos:
        url = assembleUri(repo, groupId, artifactId, version, None, "pom")

        try:
            logging.debug("Looking up properties for %s:%s at %s", artifactId, version, url)
            with urllib.request.urlopen(url) as response:
                with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                    shutil.copyfileobj(response, tmp_file)
                    tmp_file.seek(0)
                    file_content = tmp_file.read().decode('utf-8')
                    parsed_file = ET.fromstring(file_content)

                    ns = {'POM': 'http://maven.apache.org/POM/4.0.0'}
                    groupIdTag = parsed_file.find("POM:groupId", ns)
                    if groupIdTag is not None:
                        result["project.groupId"] = groupIdTag.text

                    versionTag = parsed_file.find("POM:version", ns)
                    if versionTag is not None:
                        result["project.version"] = versionTag.text

                    properties = parsed_file.find("POM:properties", ns)
                    if properties is not None:
                        for prop in properties.iter():
                            # Strip namespace from tag name
                            _, _, tag = prop.tag.rpartition("}")
                            result[tag] = prop.text

                    parent = parsed_file.find("POM:parent", ns)
                    if parent is not None:
                        parentGroupId = parent.find("POM:groupId", ns).text
                        parentArtifactId = parent.find("POM:artifactId", ns).text
                        parentVersion = parent.find("POM:version", ns).text

                        # If there are any duplicate properties, overwrite parent ones with more specific child props
                        parentProps = parseProperties(repos, parentGroupId, parentArtifactId, parentVersion)
                        parentProps.update(result)
                        result = parentProps

        except urllib.error.HTTPError:
            pass

    return result

def replaceProperties(original: str, properties: Dict[str, str]) -> str:
    result = original
    while match := re.search(r"\${(.*)}", result):
        if match.group(1) in properties:
            result = result.replace(match.group(), properties[match.group(1)])
        else:
            logging.warning("Unable to substitute property %s in %s", match.group(1), original)
            break

    return result

def parsePomTree(repos: list[str], groupId: str, artifactId: str, version: str, classifier: Optional[str] = None, properties: Optional[Dict[str, str]] = None) -> bool:
    if properties is None:
        properties = {}

    groupId = replaceProperties(groupId, properties)
    artifactId = replaceProperties(artifactId, properties)
    version = replaceProperties(version, properties)

    for module in addedModules:
        if module["groupId"] == groupId and module["artifactId"] == artifactId and module["version"] == version:
            return True

    for repo in repos:
        url = assembleUri(repo, groupId, artifactId, version, None, "pom")

        try:
            logging.debug("Looking for %s:%s at %s", artifactId, version, url)
            with urllib.request.urlopen(url) as response:
                with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
                    addModule(groupId, artifactId, version, classifier)

                    shutil.copyfileobj(response, tmp_file)
                    tmp_file.seek(0)
                    file_content = tmp_file.read().decode('utf-8')
                    parsed_file = ET.fromstring(file_content)

                    if (binaryType := getPackagingType(parsed_file)) is not None:
                        downloadAndAdd(repo, groupId, artifactId, version, classifier, binaryType)

                    if("do_not_remove: published-with-gradle-metadata" in file_content):
                        # This module has extended Gradle metadata, download that (and its dependencies)
                        parseGradleMetadata(repo, groupId, artifactId, version)

                    deps = parsePomDeps(parsed_file)
                    for dep in deps:
                        parsePomTree(repos, dep["groupId"], dep["artifactId"], dep["version"], None, properties)

                    groupId = groupId.replace(".", "/")
                    modules.append({
                        "type": "file",
                        "url": url,
                        "sha256": getFileHash(tmp_file),
                        "dest": f"maven-local/{groupId}/{artifactId}/{version}"
                    })

                    return True

        except urllib.error.HTTPError:
            pass

    logging.warning("%s:%s not found in any source", artifactId, version)
    return False

def main():
    opts = parser.parse_args()

    repos = []
    if(opts.repo is not None):
        repos.extend(opts.repo)
    else:
        repos.append("https://repo.maven.apache.org/maven2/")

    if len(opts.packages) < 1:
        parser.print_help()
        sys.exit(1)

    if opts.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel)

    for package in opts.packages:
        package_parts = package.split(":")
        if len(package_parts) != 3 and len(package_parts) != 4:
            print("Package names must be in the format groupId:artifactId:version(:classifier)")
            sys.exit(1)

        groupId = package_parts[0]
        artifactId = package_parts[1]
        version = package_parts[2]
        classifier = None
        if(len(package_parts) == 4):
            classifier = package_parts[3]

        properties = parseProperties(repos, groupId, artifactId, version)
        parsePomTree(repos, groupId, artifactId, version, classifier, properties)

    with open(opts.output, 'w') as output:
        output.write(json.dumps(modules, indent=4))
        logging.info('Output saved to %s', opts.output)

if __name__ == "__main__":
    main()
