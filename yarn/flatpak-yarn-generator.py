#!/usr/bin/env python3

import argparse
import sys
import json
import re

def getModuleSources(lockfile, include_devel=True):
    sources = []
    currentSource = ''
    currentSourceVersion = ''
    yarnVersion = ''
    for line in lockfile:
        if '# yarn lockfile' in line:
           yarnVersion = re.split('# yarn lockfile ', line)[1].strip('\n')
        if line.endswith(':\n') and 'dependencies' not in line and 'optionalDependencies' not in line:
            destLocation = re.findall(r'[a-zA-Z0-9\-\/@_.]*@', line)[0][:-1]
            if '/' in destLocation:
                temp=re.split('/', destLocation)
                currentSource = temp[0] + '-' + temp[1]
            else:
                currentSource = destLocation
        if 'version' in line and currentSource:
            currentSourceVersion = re.split('version ', line)[1].strip('\n').strip('"')
        if 'resolved' in line and currentSource and currentSourceVersion:
            resolvedStrippedStr = re.split('resolved ', line)[1].strip('\n').strip('"')
            tempList = re.split('#', resolvedStrippedStr)
            source = {'type': 'file',
                 'url': tempList[0],
                 'sha1': tempList[1],
                 'dest': 'yarn-mirror',
                 'dest-filename': currentSource + '-' + currentSourceVersion + '.tgz'}
            currentSource = ''
            sources.append(source)
    
    return sources

def main():
    parser = argparse.ArgumentParser(description='Flatpak Yarn generator')
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
    for lockfile in lockfiles:
        print('Scanning "%s" ' % lockfile, file=sys.stderr)

        with open(lockfile, 'r') as f:
            s = getModuleSources(f ,include_devel=include_devel)
            sources += s

        print(' ... %d new entries' % len(s), file=sys.stderr)

    print('%d total entries' % len(sources), file=sys.stderr)

    print('Writing to "%s"' % outfile)
    with open(outfile, 'w') as f:
        f.write(json.dumps(sources, indent=4))


if __name__ == '__main__':
    main()