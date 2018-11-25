#!/usr/bin/env python3
# Copyright 2018 Çağatay Yiğit Şahin
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from pathlib import Path
from typing import List, Dict

def repo_paths(build_dir: Path) -> List[Path]:
    src_dir = build_dir / 'src'
    repo_paths: List[Path] = []

    domains = src_dir.iterdir()
    for domain in domains:
        domain_users = domain.iterdir()
        for user in domain_users:
            user_repos = user.iterdir()
            repo_paths += list(user_repos)
    return repo_paths

def repo_source(repo_path: Path) -> Dict[str, str]:
    import subprocess
    def current_commit(repo_path: Path) -> str:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, cwd=repo_path, text=True).stdout.strip()

    def remote_url(repo_path: Path) -> str:
        return subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, cwd=repo_path, text=True).stdout.strip()

    source_object = {'type': 'git', 'url': remote_url(repo_path), 'commit': current_commit(repo_path), 'dest': str(repo_path.relative_to(build_dir))}
    return source_object

def sources(build_dir: Path) -> List[Dict[str, str]]:
    return list(map(repo_source, repo_paths(build_dir)))

def main():
    def directory(string: str) -> Path:
        path = Path(string)
        if not path.is_dir():
            msg = 'build-dir should be a directory.'
            raise argparse.ArgumentTypeError(msg)
        return path

    import argparse
    parser = argparse.ArgumentParser(description='For a Go module’s dependencies, output array of sources in flatpak-manifest format.')
    parser.add_argument('build_dir', help='Build directory of the module in .flatpak-builder/build', type=directory)
    args = parser.parse_args()

    global build_dir
    build_dir = args.build_dir
    source_list = sources(build_dir)

    import json
    print(json.dumps(source_list, indent=2))

if __name__ == '__main__':
    main()
