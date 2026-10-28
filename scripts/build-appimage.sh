#!/bin/sh
# Build dist/Beer-<arch>.AppImage for the CPU this runs on (x86_64 or aarch64).
# The AppImage carries its own Python + Tkinter, so it runs on any Linux distro.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64) TRIPLE=x86_64-unknown-linux-gnu ;;
    aarch64|arm64) ARCH=aarch64; TRIPLE=aarch64-unknown-linux-gnu ;;
    *) echo "Unsupported CPU: $ARCH" >&2; exit 1 ;;
esac
BUILD="$ROOT/build/appimage-$ARCH"
APPDIR="$BUILD/Beer.AppDir"
rm -rf "$BUILD"
mkdir -p "$APPDIR/usr/lib" "$ROOT/dist"

sh "$ROOT/scripts/fetch-python.sh" "$TRIPLE" "$APPDIR/usr/python"
cp -R "$ROOT/beer" "$APPDIR/usr/lib/"
find "$APPDIR" -name '__pycache__' -type d -prune -exec rm -rf {} +

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$HERE/usr/lib"
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONHOME
exec "$HERE/usr/python/bin/python3" -m beer "$@"
RUN
chmod 755 "$APPDIR/AppRun"

cp "$ROOT/beer/resources/beer.png" "$APPDIR/beer.png"
cp "$ROOT/beer/resources/beer.png" "$APPDIR/.DirIcon"
PYTHONPATH="$ROOT" python3 -c 'from beer.desktop import desktop_entry; print(desktop_entry("beer gui"), end="")' \
    > "$APPDIR/beer.desktop"

TOOL="$BUILD/appimagetool"
curl -fsSL --retry 3 -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
chmod +x "$TOOL"
ARCH="$ARCH" APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "$ROOT/dist/Beer-$ARCH.AppImage"
echo "Built $ROOT/dist/Beer-$ARCH.AppImage"
