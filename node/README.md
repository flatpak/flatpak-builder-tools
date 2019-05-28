# flatpak-node-generator

A more modern successor for flatpak-npm-generator and flatpak-yarn-generator, for Node 10+ only.
(For Node 8, use flatpak-npm-generator and flatpak-yarn-generator.)

## Requirements

- Python 3.6+.
- aiohttp. (flatpak-node-generator will fall back onto urllib.request if aiohttp is not available,
  but performance will take a serious hit.)

## Complete examples

There are two examples provided for how to use flatpak-node-generator:

- `vanilla-quick-start` - A Flatpak of
  [electron-quick-start](https://github.com/electron/electron-quick-start). It uses npm for
  package management and a rather basic Electron workflow.
  (Current on the Electron 4 version.)
- `webpack-quick-start` - A Flatpak of
  [electron-webpack-quick-start](https://github.com/electron-userland/electron-webpack-quick-start).
  It uses yarn for package management and electron-builder + webpack.

Both manifests have comments to highlight their differences, so you can mix and match to e.g.
get npm with electron-builder.

## Usage

```
usage: flatpak-node-generator.py [-h] [-o OUTPUT] [-r] [-R RECURSIVE_PATTERN]
                                 [--no-devel] [--no-aiohttp]
                                 [--retries RETRIES] [-P] [-s]
                                 {npm,yarn} lockfile

Flatpak Node generator

positional arguments:
  {npm,yarn}
  lockfile              The lockfile path (package-lock.json or yarn.lock)

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        The output sources file
  -r, --recursive       Recursively process all files under the lockfile
                        directory with the lockfile basename
  -R RECURSIVE_PATTERN, --recursive-pattern RECURSIVE_PATTERN
                        Given -r, restrict files to those matching the given
                        pattern.
  --no-devel            Don't include devel dependencies (npm only)
  --no-aiohttp          Don't use aiohttp, and silence any warnings related to
                        it
  --retries RETRIES     Number of retries of failed requests
  -P, --no-autopatch    Don't automatically patch Git sources from
                        package*.json
  -s, --split           Split the sources file to fit onto GitHub.
```

flatpak-node-generator.py takes the package manager (npm or yarn), and a path to a lockfile for
that package manager. It will then write an output sources file (default is generated-sources.json)
containing all the sources set up like needed for the given package manager.

If you're on npm and you don't want to include devel dependencies, pass --no-devel, and pass
--production to `npm install` itself when you call.

### Splitting mode

If your Node app has too many dependencies (particularly with npm), the generated-sources.json
may be larger than GitHub's maximum size. In order to circumvent this, you can pass `-s`, which
will write multiple files (generated-sources.0.json, generated-sources.1.json, etc) instead of
one, each smaller than the GitHub limit.

### Recursive mode

Sometimes you might have multiple lockfiles in a single source tree that need to have sources
generated for them. For this, you can pass `-r`, which will find all the lockfiles with the
name of the lockfile path you gave it in the same directory.

E.g. for instance, if you run:

```
flatpak-node-generator yarn -r ~/my-project/yarn.lock
```

flatpak-node-generator will find all files named yarn.lock inside of my-project.

If you want to match only certain lockfiles, pass `-R pattern` too:

```
flatpak-node-generator yarn -r ~/my-project/yarn.lock -R 'something*/yarn.lock' -R 'another*/yarn.lock'
```

In this case, only lockfiles matching `something*/yarn.lock` or `another*/yarn.lock` will be used.

With yarn, we're done here. However, npm has a few more curveballs you need to know about.

If you have any Git sources in your package.json, then they need to be patched to point to the
Flatpak-downloaded Git repos. flatpak-node-generator normally takes care of this patching
automatically. However, in the case of recursive package.jsons, this is a little different.

Say you have the following project directory structure:

```
my-project/
  node_modules/
    my-nested-project/
      package.json
      package-lock.json
  package-lock.json
```

`my-nested-project` doesn't ship built dependencies, so you need to build them yourself.
Therefore, you might run something like this in your Flatpak build commands:

- `npm install ...` in the root directory.
- `npm install ...` in the my-nested-project directory.
- `npm run build` or whatever build command in the my-nested-project directory.

However, if my-nested-project uses a Git source, then flatpak-node-generator will try to patch
it out...except my-nested-project's directory won't exist until you run the first `npm install`,
therefore the patch command and your build will fail.

In order to work around this, you need to pass `-P` / `--no-autopatch` to flatpak-node-generator.
This will disable the automated patching. Then, you'll need to call the scripts to patch your
package files manually. so a new build-commands might look like this:

- `flatpak-node/patch.sh`.
- `npm install ...` in the root directory.
- `flatpak-node/patch/node_modules/my-nested-project.sh`
- `npm install ...` in the my-nested-project directory.
- `npm run build` or whatever build command in the my-nested-project directory.

In short, flatpak-node-generator will generate a patch script named
`flatpak-node/patch/path-to-package-lock.json`; if package-lock.json is in the root directory,
then the name will just be `patch.sh`. Here these will be called manually, thereby ensuring
that the files that need to be patched will already exist.

(In addition, flatpak-node-generator will generate `flatpak-node/patch-all.sh`, which is what is
automatically run by default when you *don't* pass `-P`.)
