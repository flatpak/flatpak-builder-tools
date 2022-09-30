#!/usr/bin/env bash

set -e

REGISTRY=localhost:4873

curl -X PUT http://$REGISTRY/-/user/org.couchdb.user:test \
  -H 'Content-Type: application/json' \
  -d '{"name": "test", "password": "test"}'
echo

pkg_path="$(dirname "$0")/../tests/data/packages/custom-registry/registry-package"

tmpdir=$(mktemp -d)
trap 'rm -rf -- "$tmpdir"' EXIT

cp -r "$pkg_path/"* "$tmpdir"

cat > "$tmpdir/.npmrc" <<EOF
registry = http://$REGISTRY
_auth = $(echo -n test:test | base64)
EOF

(set -x; flatpak run \
  --command=bash \
  --cwd="$tmpdir" \
  --filesystem="$tmpdir" \
  --share=network \
  org.freedesktop.Sdk//22.08 \
  -c ". /usr/lib/sdk/node16/enable.sh \
      && npm publish --loglevel verbose --registry http://$REGISTRY")
