#!/usr/bin/env python3
import subprocess
import sys
import json
import os
import tempfile
import yaml
import requests
from bs4 import BeautifulSoup


def get_module_info(module):
    if " " not in module:
        return None, None

    module_name, module_version = module.split(" ", 1)
    result = subprocess.run(
        ["go", "list", "-m", "-json", module_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return module_name, json.loads(result.stdout)


def get_git_url(module_name):
    if "gitlab.com" in module_name:
        return (
            f"https://gitlab.com/{module_name.lstrip('gitlab.com/')}"
            if module_name.endswith(".git")
            else f"https://gitlab.com/{module_name.lstrip('gitlab.com/')}.git"
        )
    elif "github.com" in module_name:
        return (
            f"https://github.com/{module_name.lstrip('github.com/')}"
            if module_name.endswith(".git")
            else f"https://github.com/{module_name.lstrip('github.com/')}.git"
        )
    elif "git.torproject.org" in module_name:
        return f"https://{module_name}"
    else:
        response = requests.get(f"https://{module_name}/?go-get=1")
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.content, "html.parser")
        meta_tag = soup.find("meta", {"name": "go-import"})
        if meta_tag:
            return meta_tag["content"].split(" ")[2]
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: ./flatpak-go-deps.py <repository/folder@version>")
        sys.exit(1)

    repo_and_folder, version = sys.argv[1].split("@")

    if "/" in repo_and_folder:
        repo, folder = repo_and_folder.rsplit("/", 1)
        repo_name = folder
    else:
        repo = repo_and_folder
        folder = ""
        repo_name = os.path.basename(repo).replace(".git", "")

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        subprocess.run(["go", "mod", "init", "tempmod"], check=True)

        try:
            subprocess.run(
                ["git", "clone", f"https://{repo}", f"src/{repo_name}"], check=True
            )
            os.chdir(f"src/{repo_name}")
            subprocess.run(["git", "checkout", version], check=True)
            os.chdir(temp_dir)
            if folder:
                os.chdir(f"src/{repo_name}/{folder}")
        except subprocess.CalledProcessError:
            print(
                f"Error fetching {repo}@{version}. Please verify the repository and version."
            )
            sys.exit(1)

        result = subprocess.run(
            ["go", "list", "-m", "all"],
            check=True,
            capture_output=True,
            text=True,
        )

        modules = result.stdout.strip().split("\n")
        sources = []

        for module in modules:
            module_name, info = get_module_info(module)
            if not module_name or not info:
                continue
            path = info["Path"]
            version = info.get("Version")
            if not version:
                continue

            git_url = get_git_url(module_name)
            if not git_url:
                git_url = f"https://{module_name}.git"

            if version.startswith("v"):
                ref_type = "tag"
            else:
                ref_type = "commit"

            sources.append(
                {
                    "type": "git",
                    "url": git_url,
                    ref_type: version,
                    "dest": f"src/{path.replace('.', '/')}",
                }
            )

        yaml_data = {
            "name": repo_name,
            "buildsystem": "simple",
            "build-options": {"env": {"GOBIN": "/app/bin/"}},
            "build-commands": [
                f". /usr/lib/sdk/golang/enable.sh; export GOPATH=$PWD; export GO111MODULE=off; go install {repo}/{os.path.basename(repo)}"
            ],
            "sources": sources,
        }

        print()
        print(yaml.dump(yaml_data))


if __name__ == "__main__":
    main()
