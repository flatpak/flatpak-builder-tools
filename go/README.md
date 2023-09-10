# Go

This script requires Go and git to be installed. You also need the Python in [requirements.txt](./requirements.txt).

This script works by creating a new Go module in a temporary folder, add the given Go package as a dependency, and then runs `go list -m all` to get the full list of Go modules. For each module, it uses `go list -m -json <module>` to get detailed information. And then finally, it outputs the module in YAML format.

## Usage

```
./flatpak-go-deps.py <repository@version>
```

For example, here's how you'd get Flatpak manifests for some Tor pluggable transports:

```
./flatpak-go-deps.py git.torproject.org/pluggable-transports/meek.git/meek-client@v0.38.0
./flatpak-go-deps.py git.torproject.org/pluggable-transports/snowflake.git/client@v2.6.0
./flatpak-go-deps.py gitlab.com/yawning/obfs4.git/obfs4proxy@obfs4proxy-0.0.14
```

This is what the output looks like:

```
$ ./flatpak-go-deps.py git.torproject.org/pluggable-transports/meek.git/meek-client@v0.38.0
go: creating new go.mod: module tempmod
Cloning into 'src/meek-client'...
warning: redirecting to https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/meek.git/
remote: Enumerating objects: 2676, done.
remote: Counting objects: 100% (658/658), done.
remote: Compressing objects: 100% (281/281), done.
remote: Total 2676 (delta 372), reused 658 (delta 372), pack-reused 2018
Receiving objects: 100% (2676/2676), 549.97 KiB | 440.00 KiB/s, done.
Resolving deltas: 100% (1546/1546), done.
Note: switching to 'v0.38.0'.

You are in 'detached HEAD' state. You can look around, make experimental
changes and commit them, and you can discard any commits you make in this
state without impacting any branches by switching back to a branch.

If you want to create a new branch to retain commits you create, you may
do so (now or later) by using -c with the switch command. Example:

  git switch -c <new-branch-name>

Or undo this operation with:

  git switch -

Turn off this advice by setting config variable advice.detachedHead to false

HEAD is now at 3be00b7 programVersion = "0.38.0"

build-commands:
- . /usr/lib/sdk/golang/enable.sh; export GOPATH=$PWD; export GO111MODULE=off; go
  install git.torproject.org/pluggable-transports/meek.git/meek.git
build-options:
  env:
    GOBIN: /app/bin/
buildsystem: simple
name: meek-client
sources:
- dest: src/git/torproject/org/pluggable-transports/goptlib/git
  tag: v1.1.0
  type: git
  url: https://git.torproject.org/pluggable-transports/goptlib.git.git
- dest: src/github/com/andybalholm/brotli
  tag: v1.0.4
  type: git
  url: https://github.com/andybalholm/brotli.git
- dest: src/github/com/klauspost/compress
  tag: v1.15.9
  type: git
  url: https://github.com/klauspost/compress.git
- dest: src/github/com/refraction-networking/utls
  tag: v1.1.5
  type: git
  url: https://github.com/refraction-networking/utls.git
- dest: src/golang/org/x/crypto
  tag: v0.0.0-20220829220503-c86fa9a7ed90
  type: git
  url: https://golang.org/x/crypto.git
- dest: src/golang/org/x/net
  tag: v0.0.0-20220909164309-bea034e7d591
  type: git
  url: https://golang.org/x/net.git
- dest: src/golang/org/x/sys
  tag: v0.0.0-20220728004956-3c1f35247d10
  type: git
  url: https://golang.org/x/sys.git
- dest: src/golang/org/x/term
  tag: v0.0.0-20210927222741-03fcf44c2211
  type: git
  url: https://golang.org/x/term.git
- dest: src/golang/org/x/text
  tag: v0.3.7
  type: git
  url: https://golang.org/x/text.git
- dest: src/golang/org/x/tools
  tag: v0.0.0-20180917221912-90fa682c2a6e
  type: git
  url: https://golang.org/x/tools.git
```