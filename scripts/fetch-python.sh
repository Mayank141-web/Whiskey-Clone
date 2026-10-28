#!/bin/sh
# Download a self-contained Python (with Tkinter) from astral-sh/python-build-standalone
# and trim it down, so the Beer app doesn't depend on whatever Python the user has.
#   usage: fetch-python.sh TARGET-TRIPLE DEST-DIR
#   e.g.   fetch-python.sh aarch64-apple-darwin build/python-arm64
set -eu
TRIPLE="$1"
DEST="$2"
PYVER="${BEER_PYTHON_VERSION:-3.12}"
API="https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"

AUTH=""
[ -n "${GH_TOKEN:-}" ] && AUTH="Authorization: Bearer $GH_TOKEN"
URL="$(curl -fsSL ${AUTH:+-H "$AUTH"} "$API" | python3 -c '
import json, re, sys
triple, ver = sys.argv[1], sys.argv[2]
assets = json.load(sys.stdin)["assets"]
for kind in ("install_only_stripped", "install_only"):
    pat = re.compile(r"^cpython-%s\.\d+\+\d+-%s-%s\.tar\.gz$" % (re.escape(ver), re.escape(triple), kind))
    for a in assets:
        if pat.match(a["name"]):
            print(a["browser_download_url"]); sys.exit(0)
sys.exit("no Python %s build for %s" % (ver, triple))
' "$TRIPLE" "$PYVER")"

echo "Fetching $URL"
TMP="$(mktemp -d)"
curl -fsSL --retry 3 -o "$TMP/python.tar.gz" "$URL"
rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "$TMP/python.tar.gz" -C "$TMP"
cp -R "$TMP/python/." "$DEST/"
rm -rf "$TMP"

# Trim things Beer never uses (keeps the download small).
LIB="$(echo "$DEST"/lib/python3.*)"
rm -rf "$LIB/test" "$LIB/idlelib" "$LIB/ensurepip" "$LIB/lib2to3" "$LIB/turtledemo" \
       "$LIB/pydoc_data" "$LIB/site-packages"/pip* "$DEST/include" "$DEST/share"
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} +
