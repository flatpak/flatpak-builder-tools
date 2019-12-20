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
                                 [--registry REGISTRY] [--no-devel]
                                 [--no-aiohttp] [--retries RETRIES] [-P] [-s]
                                 [--electron-chromedriver ELECTRON_CHROMEDRIVER]
                                 [--electron-non-patented-ffmpeg]
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
  --registry REGISTRY   The registry to use (npm only)
  --no-devel            Don't include devel dependencies (npm only)
  --no-aiohttp          Don't use aiohttp, and silence any warnings related to
                        it
  --retries RETRIES     Number of retries of failed requests
  -P, --no-autopatch    Don't automatically patch Git sources from
                        package*.json
  -s, --split           Split the sources file to fit onto GitHub.
  --electron-chromedriver ELECTRON_CHROMEDRIVER
                        Use the ChromeDriver version associated with the given
                        Electron version
  --electron-non-patented-ffmpeg
                        Download the non-patented ffmpeg binaries
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

### ChromeDriver support

If your app depends on node-chromedriver, then flatpak-node-generator will download it
to the directory `$FLATPAK_BUILDER_BUILDDIR/flatpak-node/chromedriver`. You need to
do two things in order to utilize this:

- Add `CHROMEDRIVER_SKIP_DOWNLOAD=true` to your environment variables.
- Add `$FLATPAK_BUILDER_BUILDDIR/flatpak-node/chromedriver` to your PATH.

It might look like this:

```yaml
build-options:
  append-path: '/usr/lib/sdk/node10/bin:/run/build/MY-MODULE/flatpak-node/chromedriver'
  env:
    CHROMEDRIVER_SKIP_DOWNLOAD: 'true'
    # ...
```

In addition, the default ChromeDriver only is available for x64. If you need to build
on other platforms, you can use the ChromeDriver binaries that are compiled by Electron
and distributed with their releases. To do this, pass
`--electron-chromedriver AN_ELECTRON_VERSION` to use the ChromeDriver given with that
Electron version. Note that you may not necessarily want to use a version here that
corresponds to the Electron version your app is using; many apps stay on older Electron
versions but may use newer ChromeDriver functionality.

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

### electron-builder and ARM architectures

If you want to build for ARM or ARM64 with electron-builder, there are two important
things to note:

- For ARM in particular, electron-builder will misdetect the architecture and give
  an error about it being unsupported. To work around this, you have to pass the
  architecture manually to electron-builder. flatpak-node-generator will write
  a shell script at `flatpak-node/electron-builder-arch-args.sh` that can be sourced
  to set the `$ELECTRON_BUILDER_ARCH_ARGS` environment variable. Then, this variable
  can be passed to the electron-builder command.
- For both ARM and ARM64, the electron-builder output directory will contain the
  architecture in its name.

Both of these cases are handled by the electron-webpack-quick-start example.

### Non-patented ffmpeg

By defualt, the ffmpeg that Electron ships with has proprietary codecs built in
like AAC and H.264. If you don't need these, you can pass
`--electron-non-patented-ffmpeg` to flatpak-node-generator. This will download
a patent-clean ffmpeg binary to `flatpak-node/libffmpeg.so`, which you can then
use to overwrite the default Electron ffmpeg, e.g.:

```yaml
- 'install -Dm 755 flatpak-node/libffmpeg.so -t /app/electron-webpack-quick-start'
```

An short example of this is again in the electron-webpack-quick-start
