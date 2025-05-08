# Flatpak Deno Generator

run from jsr

```
deno -RN -W=. jsr:@flatpak/flatpak-deno-generator deno.lock
```

or locally from this repo

```
deno -RN -W=. main.ts deno.lock
```

This will create a `deno-sources.json` that can be used in flatpak build files:

- it creates and populates `./deno_dir` with npm dependencies
- it creates and populates `./vendor` with jsr + http dependencies

## Usage:

- Use the sources file as a source, example:

```yml
sources:
  - deno-sources.json
```

- To use `deno_dir` point `DENO_DIR` env variable to it, like so:

```yml
- name: someModule
  buildsystem: simple
  build-options:
    env:
      DENO_DIR: deno_dir
```

- To use `vendor` move it next to your `deno.json` file and make sure to compile
  or run with `--vendor` flag, exmaple:

```yml
- # src is where my deno project at
- mv ./vendor src/
- DENORT_BIN=$PWD/denort ./deno compile --vendor --no-check --output virtaudio-bin --cached-only
  --allow-all --include ./src/gui.slint --include ./src/client.html ./src/gui.ts
```

## Notes

Currently this only supports lockfile V5 (available since deno version 2.3)

## License

MIT

## Example

- checkout https://github.com/flathub/io.github.sigmasd.VirtAudio/
