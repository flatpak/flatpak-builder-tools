#!/usr/bin/env python3

import argparse
import yaml

# https://reorx.com/blog/python-yaml-tips/
class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)

def update_sources(sources, new_versions):
    updated_sources = []
    for source in sources:
        if isinstance(source, dict) and 'tag' in source and 'url' in source:
            url = source['url']
            *_, org, repo = url.strip('/').split('/')
            repo = f"{org}/{repo}"
            if repo in new_versions:
                source['tag'] = new_versions[repo]
        updated_sources.append(source)
    return updated_sources

def main():
    parser = argparse.ArgumentParser(description="Update module sources in a YAML file.")
    parser.add_argument("file", metavar="FILE", type=str, help="YAML file to update")
    parser.add_argument("--update", nargs=2, help="Update module versions in the format 'org/repo vX.Y.Z'", metavar=("org/repo", "vX.Y.Z"), action="append")
    
    args = parser.parse_args()

    if not args.update:
        print("No updates provided.")
        return

    update_dict = {}

    for update in args.update:
        org_repo, version = update
        update_dict[org_repo] = version

    try:
        with open(args.file, 'r') as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
        
        if 'modules' in data:
            for module in data['modules']:
                if 'sources' in module:
                    module['sources'] = update_sources(module['sources'], update_dict)

        with open(args.file, 'w') as file:
            yaml.dump(data, file, sort_keys=False, Dumper=IndentDumper)

        print(f"Updated {args.file} with new module versions.")

    except FileNotFoundError:
        print(f"File not found: {args.file}")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")

if __name__ == "__main__":
    raise SystemExit(main())

