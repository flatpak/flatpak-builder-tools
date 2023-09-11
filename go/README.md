# Flatpak Go Generator

This script requires Go and git to be installed. You also need the Python in [requirements.txt](./requirements.txt).

This script works by creating a new Go module in a temporary folder, add the given Go package as a dependency, and then runs `go list -m all` to get the full list of Go modules. For each module, it uses `go list -m -json <module>` to get detailed information. And then finally, it outputs the module in YAML format.

## Usage

```
./flatpak-go-deps.py <repository@version>
```

For example, here's how you'd get Flatpak manifests for some Tor pluggable transports:

```
./flatpak-go-deps.py git.torproject.org/pluggable-transports/meek.git/meek-client --version v0.38.0
./flatpak-go-deps.py git.torproject.org/pluggable-transports/snowflake.git/client --version v2.6.0
./flatpak-go-deps.py gitlab.com/yawning/obfs4.git/obfs4proxy --version obfs4proxy-0.0.14
```

If the deps are hosted on GitHub or GitLab, it uses the GitHub and GitLab API to find the commit IDs, as this is much quicker than git cloning the full repos. However these APIs have rate limits, and it falls back to git cloning. You can optionally pass in `--github_api_token` or `--gitlab_api_token` if you want to avoid the rate limits.

This is what the output looks like:

```
$ ./flatpak-go-deps.py git.torproject.org/pluggable-transports/meek.git/meek-client --version v0.38.0
✨ Creating temporary Go module
go: creating new go.mod: module tempmod
✨ Cloning the target repository
Cloning into 'src/meek-client'...
warning: redirecting to https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/meek.git/
remote: Enumerating objects: 2676, done.
remote: Counting objects: 100% (658/658), done.
remote: Compressing objects: 100% (281/281), done.
remote: Total 2676 (delta 372), reused 658 (delta 372), pack-reused 2018
Receiving objects: 100% (2676/2676), 549.97 KiB | 1.02 MiB/s, done.
Resolving deltas: 100% (1546/1546), done.
✨ Checking out version v0.38.0
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
✨ Found 10 dependencies
✨ Module: git.torproject.org/pluggable-transports/goptlib.git v1.1.0
✨ Git URL: https://git.torproject.org/pluggable-transports/goptlib.git
✨ Cloning https://git.torproject.org/pluggable-transports/goptlib.git@v1.1.0 to find commit ID
Cloning into bare repository '/tmp/tmp4auq0b5l'...
warning: redirecting to https://gitlab.torproject.org/tpo/anti-censorship/pluggable-transports/goptlib.git/
remote: Enumerating objects: 920, done.
remote: Counting objects: 100% (26/26), done.
remote: Compressing objects: 100% (20/20), done.
remote: Total 920 (delta 8), reused 9 (delta 2), pack-reused 894
Receiving objects: 100% (920/920), 169.14 KiB | 347.00 KiB/s, done.
Resolving deltas: 100% (473/473), done.
✨ Found commit ID: 781a46c66d2ddbc3509354ae7f1fccab74cb9927
✨ Module: github.com/andybalholm/brotli v1.0.4
✨ Git URL: https://github.com/andybalholm/brotli
✨ Used GitHub API to find commit ID: 1d750214c25205863625bb3eb8190a51b2cef26d
✨ Module: github.com/klauspost/compress v1.15.9
✨ Git URL: https://github.com/klauspost/compress
✨ Used GitHub API to find commit ID: 4b4f3c94fdf8c3a6c725e2ff110d9b44f88823ed
✨ Module: github.com/refraction-networking/utls v1.1.5
✨ Git URL: https://github.com/refraction-networking/utls
✨ Used GitHub API to find commit ID: 7a37261931c6d4ab67fec65e73a3cc68df4ef84a
✨ Module: golang.org/x/crypto v0.0.0-20220829220503-c86fa9a7ed90
✨ Found short_commit_id: c86fa9a7ed90
✨ Git URL: https://go.googlesource.com/crypto
✨ Cloning https://go.googlesource.com/crypto to find long commit ID version of c86fa9a7ed90
Cloning into bare repository '/tmp/tmp_v2n6aqt'...
remote: Finding sources: 100% (6/6)
remote: Total 6906 (delta 3826), reused 6901 (delta 3826)
Receiving objects: 100% (6906/6906), 7.07 MiB | 12.10 MiB/s, done.
Resolving deltas: 100% (3826/3826), done.
✨ Found commit ID: c86fa9a7ed909e2f2a8ab8298254fca727aba16a
✨ Module: golang.org/x/net v0.0.0-20220909164309-bea034e7d591
✨ Found short_commit_id: bea034e7d591
✨ Git URL: https://go.googlesource.com/net
✨ Cloning https://go.googlesource.com/net to find long commit ID version of bea034e7d591
Cloning into bare repository '/tmp/tmpnuomejb1'...
remote: Finding sources: 100% (38/38)
remote: Total 12487 (delta 7842), reused 12476 (delta 7842)
Receiving objects: 100% (12487/12487), 13.68 MiB | 13.91 MiB/s, done.
Resolving deltas: 100% (7842/7842), done.
✨ Found commit ID: bea034e7d591acfddd606603cf48fae48bbdd340
✨ Module: golang.org/x/sys v0.0.0-20220728004956-3c1f35247d10
✨ Found short_commit_id: 3c1f35247d10
✨ Git URL: https://go.googlesource.com/sys
✨ Cloning https://go.googlesource.com/sys to find long commit ID version of 3c1f35247d10
Cloning into bare repository '/tmp/tmpq5awv07s'...
remote: Total 14830 (delta 10172), reused 14830 (delta 10172)
Receiving objects: 100% (14830/14830), 24.51 MiB | 18.52 MiB/s, done.
Resolving deltas: 100% (10172/10172), done.
✨ Found commit ID: 3c1f35247d107ad3669216fc09e75d66fa146363
✨ Module: golang.org/x/term v0.0.0-20210927222741-03fcf44c2211
✨ Found short_commit_id: 03fcf44c2211
✨ Git URL: https://go.googlesource.com/term
✨ Cloning https://go.googlesource.com/term to find long commit ID version of 03fcf44c2211
Cloning into bare repository '/tmp/tmp047hj5wu'...
remote: Total 385 (delta 212), reused 385 (delta 212)
Receiving objects: 100% (385/385), 115.10 KiB | 1.55 MiB/s, done.
Resolving deltas: 100% (212/212), done.
✨ Found commit ID: 03fcf44c2211dcd5eb77510b5f7c1fb02d6ded50
✨ Module: golang.org/x/text v0.3.7
✨ Git URL: https://go.googlesource.com/text
✨ Cloning https://go.googlesource.com/text@v0.3.7 to find commit ID
Cloning into bare repository '/tmp/tmp83wmuo0u'...
remote: Total 6627 (delta 3942), reused 6627 (delta 3942)
Receiving objects: 100% (6627/6627), 24.28 MiB | 14.28 MiB/s, done.
Resolving deltas: 100% (3942/3942), done.
✨ Found commit ID: 383b2e75a7a4198c42f8f87833eefb772868a56f
✨ Module: golang.org/x/tools v0.0.0-20180917221912-90fa682c2a6e
✨ Found short_commit_id: 90fa682c2a6e
✨ Git URL: https://go.googlesource.com/tools
✨ Cloning https://go.googlesource.com/tools to find long commit ID version of 90fa682c2a6e
Cloning into bare repository '/tmp/tmps_tqnqmg'...
remote: Total 81895 (delta 50074), reused 81895 (delta 50074)
Receiving objects: 100% (81895/81895), 51.39 MiB | 20.37 MiB/s, done.
Resolving deltas: 100% (50074/50074), done.
✨ Found commit ID: 90fa682c2a6e6a37b3a1364ce2fe1d5e41af9d6d
✨ 🌟 ✨
build-commands:
- . /usr/lib/sdk/golang/enable.sh; export GOPATH=$PWD; export GO111MODULE=off; go
  install git.torproject.org/pluggable-transports/meek.git/meek.git
build-options:
  env:
    GOBIN: /app/bin/
buildsystem: simple
name: meek-client
sources:
- commit: 781a46c66d2ddbc3509354ae7f1fccab74cb9927
  dest: src/git/torproject/org/pluggable-transports/goptlib/git
  type: git
  url: https://git.torproject.org/pluggable-transports/goptlib.git
- commit: 1d750214c25205863625bb3eb8190a51b2cef26d
  dest: src/github/com/andybalholm/brotli
  type: git
  url: https://github.com/andybalholm/brotli
- commit: 4b4f3c94fdf8c3a6c725e2ff110d9b44f88823ed
  dest: src/github/com/klauspost/compress
  type: git
  url: https://github.com/klauspost/compress
- commit: 7a37261931c6d4ab67fec65e73a3cc68df4ef84a
  dest: src/github/com/refraction-networking/utls
  type: git
  url: https://github.com/refraction-networking/utls
- commit: c86fa9a7ed909e2f2a8ab8298254fca727aba16a
  dest: src/golang/org/x/crypto
  type: git
  url: https://go.googlesource.com/crypto
- commit: bea034e7d591acfddd606603cf48fae48bbdd340
  dest: src/golang/org/x/net
  type: git
  url: https://go.googlesource.com/net
- commit: 3c1f35247d107ad3669216fc09e75d66fa146363
  dest: src/golang/org/x/sys
  type: git
  url: https://go.googlesource.com/sys
- commit: 03fcf44c2211dcd5eb77510b5f7c1fb02d6ded50
  dest: src/golang/org/x/term
  type: git
  url: https://go.googlesource.com/term
- commit: 383b2e75a7a4198c42f8f87833eefb772868a56f
  dest: src/golang/org/x/text
  type: git
  url: https://go.googlesource.com/text
- commit: 90fa682c2a6e6a37b3a1364ce2fe1d5e41af9d6d
  dest: src/golang/org/x/tools
  type: git
  url: https://go.googlesource.com/tools
```