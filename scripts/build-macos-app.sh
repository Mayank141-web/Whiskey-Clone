#!/bin/sh
# Build dist/Beer-macOS.dmg: a universal (Apple Silicon + Intel) Beer.app with its own Python.
# Must run on macOS (uses clang, iconutil, codesign and hdiutil).
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cd "$ROOT" && python3 -c 'import beer; print(beer.__version__)')"
BUILD="$ROOT/build/macos"
APP="$BUILD/Beer.app"
mkdir -p "$ROOT/dist"
rm -rf "$BUILD"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/lib"

# Launcher: one universal binary that picks the matching Python at runtime.
clang -O2 -mmacosx-version-min=10.15 -arch arm64 -arch x86_64 \
    -o "$APP/Contents/MacOS/Beer" "$ROOT/packaging/macos/launcher.c"

# Python for each CPU type.
sh "$ROOT/scripts/fetch-python.sh" aarch64-apple-darwin "$APP/Contents/Resources/python-arm64"
sh "$ROOT/scripts/fetch-python.sh" x86_64-apple-darwin "$APP/Contents/Resources/python-x86_64"

# Beer itself.
cp -R "$ROOT/beer" "$APP/Contents/Resources/lib/"
find "$APP" -name '__pycache__' -type d -prune -exec rm -rf {} +

# Icon.
ICONSET="$BUILD/Beer.iconset"
mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
    sips -z $s $s "$ROOT/beer/resources/beer.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
    d=$((s * 2))
    if [ $d -le 512 ]; then
        sips -z $d $d "$ROOT/beer/resources/beer.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
    else
        cp "$ROOT/beer/resources/beer.png" "$ICONSET/icon_${s}x${s}@2x.png"
    fi
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/Beer.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Beer</string>
  <key>CFBundleDisplayName</key><string>Beer</string>
  <key>CFBundleIdentifier</key><string>io.github.mayank141-web.beer</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleExecutable</key><string>Beer</string>
  <key>CFBundleIconFile</key><string>Beer</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>10.15</string>
  <key>LSApplicationCategoryType</key><string>public.app-category.games</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>Windows Program</string>
      <key>CFBundleTypeRole</key><string>Viewer</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>CFBundleTypeExtensions</key>
      <array><string>exe</string><string>msi</string><string>bat</string><string>lnk</string></array>
    </dict>
  </array>
</dict>
</plist>
PLIST

# Ad-hoc signature: required for Apple Silicon and lets Gatekeeper offer "Open Anyway".
codesign --force --deep --sign - "$APP"

# Disk image with an Applications shortcut to drag onto.
STAGE="$BUILD/dmg"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp "$ROOT/packaging/macos/READ ME FIRST.txt" "$STAGE/"
rm -f "$ROOT/dist/Beer-macOS.dmg"
hdiutil create -volname "Beer" -srcfolder "$STAGE" -ov -format UDZO "$ROOT/dist/Beer-macOS.dmg"
echo "Built $ROOT/dist/Beer-macOS.dmg"
