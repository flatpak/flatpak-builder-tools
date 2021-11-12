# Flatpak Go Get Generator

Tool to automatically create the source list for a Go module.

The script does not require Go in the host system.

## Usage

- Create a manifest where you give the Go module network access, set `GO111MODULE` to `off`, and set `GOPATH` to `$PWD`.

  Example (`example.json`):
  ```json
  {
      "app-id": "com.example.test",
      "runtime": "org.kde.Platform",
      "runtime-version": "5.15",
      "sdk": "org.kde.Sdk",
      "modules": [
          {
              "name": "obfs4proxy",
              "buildsystem": "simple",
              "build-options": {
                  "env": {
                      "GOBIN": "/app/bin/"
                  },
                  "build-args": [
                      "--share=network"
                  ]
              },
              "build-commands": [
                  ". /usr/lib/sdk/golang/enable.sh; export GOPATH=$PWD; export GO111MODULE=off; go get gitlab.com/yawning/obfs4.git/obfs4proxy"
              ]
          }
      ]
  }
  ```

- Run `flatpak-builder` with `--keep-build-dirs` to download all of the sources for you:
   ```sh
   flatpak-builder build --force-clean --keep-build-dirs example.json
   ```

- For each Go package you want to build, run `flatpak-go-get-generator.py` with build-dir pointing the the build directory in `.flatpak-builder/build`:
   ```sh
   ./flatpak-go-get-generator.py ./.flatpak-builder/build/obfs4proxy
   ```

- Convert the source list to YAML if necessary:
   ```sh
   ../flatpak-json2yaml.py ./obfs4proxy-sources.json
   ```

- Update the the manifest to remove network access, replace `go get` with `go install`, and add the list to the sources field of the Go module in the manifest.

  Example final manifest:
  
  ```json
  {
      "app-id": "com.example.test",
      "runtime": "org.kde.Platform",
      "runtime-version": "5.15",
      "sdk": "org.kde.Sdk",
      "modules": [
          {
              "name": "obfs4proxy",
              "buildsystem": "simple",
              "build-options": {
                  "env": {
                      "GOBIN": "/app/bin/"
                  }
              },
              "build-commands": [
                  ". /usr/lib/sdk/golang/enable.sh; export GOPATH=$PWD; export GO111MODULE=off; go install gitlab.com/yawning/obfs4.git/obfs4proxy"
              ],
              "sources": [
                  {
                      "type": "git",
                      "url": "https://go.googlesource.com/net",
                      "commit": "69e39bad7dc2bbb411fa35755c46020969029fa7",
                      "dest": "src/golang.org/x/net"
                  },
                  {
                      "type": "git",
                      "url": "https://go.googlesource.com/crypto",
                      "commit": "ceb1ce70b4faafeeb5b3f23cc83f09b39a4f3f1d",
                      "dest": "src/golang.org/x/crypto"
                  },
                  {
                      "type": "git",
                      "url": "https://go.googlesource.com/text",
                      "commit": "18b340fc7af22495828ffbe71e9f9e22583bc7a9",
                      "dest": "src/golang.org/x/text"
                  },
                  {
                      "type": "git",
                      "url": "https://go.googlesource.com/sys",
                      "commit": "faf0a1b62c6b439486fd1d914d8185627b99d387",
                      "dest": "src/golang.org/x/sys"
                  },
                  {
                      "type": "git",
                      "url": "https://gitlab.com/yawning/obfs4",
                      "commit": "e330d1b7024b4ab04f7d96cc1afc61325744fafc",
                      "dest": "src/gitlab.com/yawning/obfs4.git"
                  },
                  {
                      "type": "git",
                      "url": "https://gitlab.com/yawning/utls",
                      "commit": "f1bcf4b40e4596d0ccd1dbf8f3a9f4922f9759ca",
                      "dest": "src/gitlab.com/yawning/utls.git"
                  },
                  {
                      "type": "git",
                      "url": "https://gitlab.com/yawning/bsaes",
                      "commit": "0a714cd429ec754482b4001e918db30cd2094405",
                      "dest": "src/gitlab.com/yawning/bsaes.git"
                  },
                  {
                      "type": "git",
                      "url": "https://git.torproject.org/pluggable-transports/goptlib",
                      "commit": "13b7b3552e1eef32e4d8a2a7813f22488f91dc09",
                      "dest": "src/git.torproject.org/pluggable-transports/goptlib.git"
                  },
                  {
                      "type": "git",
                      "url": "https://github.com/dsnet/compress",
                      "commit": "f66993602bf5da07ef49d35b08e7264ae9fe2b6e",
                      "dest": "src/github.com/dsnet/compress"
                  },
                  {
                      "type": "git",
                      "url": "https://github.com/dchest/siphash",
                      "commit": "991656ee3840f823396c2eb7f4a70d65dac06832",
                      "dest": "src/github.com/dchest/siphash"
                  }
              ]
          }
      ]
  }
  ```

