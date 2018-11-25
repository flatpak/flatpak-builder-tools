#!/usr/bin/env python3
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
