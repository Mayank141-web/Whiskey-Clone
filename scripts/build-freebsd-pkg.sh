#!/bin/sh
# Build dist/beer-VERSION.pkg, a native FreeBSD package (any CPU). Run on FreeBSD.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cd "$ROOT" && python3 -c 'import beer; print(beer.__version__)')"
STAGE="$ROOT/build/freebsd/stage"
META="$ROOT/build/freebsd"
rm -rf "$META"
mkdir -p "$STAGE" "$ROOT/dist"
make -s -C "$ROOT" install DESTDIR="$STAGE" PREFIX=/usr/local >/dev/null

PYV="$(python3 -c 'import sys; print("py%d%d" % sys.version_info[:2])')"
MAJOR="$(uname -r | cut -d. -f1)"
cat > "$META/+MANIFEST" <<MAN
name: beer
version: "$VERSION"
origin: emulators/beer
comment: "Run Windows apps and games (like Pokemon fan games) with Wine"
www: "https://github.com/Mayank141-web/Whiskey-Clone"
maintainer: "noreply@github.com"
prefix: /usr/local
abi: "FreeBSD:$MAJOR:*"
arch: "freebsd:$MAJOR:*"
licenselogic: single
licenses: [MIT]
categories: [emulators, games]
desc: "Beer runs Windows programs on FreeBSD, Linux and macOS using Wine, with a one-click setup for Pokemon fan games."
scripts: {
  post-install: "echo 'Beer installed. Open it from your app menu (or run: beer). It will offer to install Wine and Tkinter if needed.'; for p in python3 $PYV-tkinter; do pkg info -e \$p || echo \"Tip: for the Beer window run: pkg install \$p\"; done"
}
MAN
( cd "$STAGE" && find . -type f -o -type l | sed 's|^\.||' ) > "$META/plist"
pkg create -M "$META/+MANIFEST" -p "$META/plist" -r "$STAGE" -o "$ROOT/dist"
ls -l "$ROOT/dist"/beer-*.pkg
