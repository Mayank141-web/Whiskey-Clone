#!/bin/sh
# Build every release file into dist/:
#   whiskey.tar.gz / whiskey-VERSION.tar.gz   source (used by install.sh)
#   whiskey_VERSION_all.deb                   Debian, Ubuntu, Mint, Pop!_OS...
#   whiskey-VERSION-1.noarch.rpm              Fedora, RHEL, openSUSE... (needs rpmbuild)
#   install.sh, whiskey.rb, PKGBUILD, SHA256SUMS
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cd "$ROOT" && python3 -c 'import whiskey; print(whiskey.__version__)')"
DIST="$ROOT/dist"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

rm -rf "$DIST"
mkdir -p "$DIST"

# --------------------------------------------------------------------- source tarball
SRCNAME="whiskey-$VERSION"
mkdir -p "$WORK/$SRCNAME"
(cd "$ROOT" && tar --exclude='__pycache__' -cf - whiskey install.sh README.md LICENSE Makefile packaging) \
    | tar -xf - -C "$WORK/$SRCNAME"
tar -czf "$DIST/$SRCNAME.tar.gz" -C "$WORK" "$SRCNAME"
cp "$DIST/$SRCNAME.tar.gz" "$DIST/whiskey.tar.gz"

# --------------------------------------------------------------------- staged /usr tree
stage() {
    dest="$1"
    make -s -C "$ROOT" install DESTDIR="$dest" PREFIX=/usr >/dev/null
}

# --------------------------------------------------------------------- .deb
if command -v dpkg-deb >/dev/null 2>&1; then
    DEB="$WORK/deb"
    stage "$DEB"
    mkdir -p "$DEB/DEBIAN"
    SIZE="$(du -sk "$DEB/usr" | cut -f1)"
    sed -e "s/@VERSION@/$VERSION/" -e "s/@SIZE@/$SIZE/" "$ROOT/packaging/linux/debian-control" > "$DEB/DEBIAN/control"
    cp "$ROOT/packaging/linux/postinst" "$DEB/DEBIAN/postinst"
    chmod 755 "$DEB/DEBIAN/postinst"
    dpkg-deb --root-owner-group --build "$DEB" "$DIST/whiskey_${VERSION}_all.deb" >/dev/null
fi

# --------------------------------------------------------------------- .rpm
if command -v rpmbuild >/dev/null 2>&1; then
    RPMTOP="$WORK/rpm"
    mkdir -p "$RPMTOP/SOURCES" "$RPMTOP/SPECS"
    cp "$DIST/$SRCNAME.tar.gz" "$RPMTOP/SOURCES/"
    sed "s/@VERSION@/$VERSION/" "$ROOT/packaging/linux/whiskey.spec" > "$RPMTOP/SPECS/whiskey.spec"
    rpmbuild --quiet --define "_topdir $RPMTOP" -bb "$RPMTOP/SPECS/whiskey.spec"
    cp "$RPMTOP"/RPMS/noarch/*.rpm "$DIST/"
fi

# --------------------------------------------------------------------- scripts & recipes
cp "$ROOT/install.sh" "$DIST/install.sh"
cp "$ROOT/Formula/whiskey.rb" "$DIST/whiskey.rb"
SHA="$(sha256sum "$DIST/$SRCNAME.tar.gz" | cut -d' ' -f1)"
sed -e "s/@VERSION@/$VERSION/" -e "s/@SHA256@/$SHA/" "$ROOT/packaging/linux/PKGBUILD" > "$DIST/PKGBUILD"

(cd "$DIST" && sha256sum * > SHA256SUMS)
echo "Built release $VERSION:"
ls -l "$DIST"
