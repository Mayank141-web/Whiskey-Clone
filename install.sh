#!/bin/sh
# Whiskey installer for Linux (any distro), FreeBSD and macOS.
#
#   curl -fsSL https://github.com/Mayank141-web/Whiskey-Clone/releases/latest/download/install.sh | sudo sh
#
# or from a downloaded copy of the source:   sudo ./install.sh
#
# Options:
#   --prefix DIR   install under DIR (default /usr/local)
#   --no-deps      don't install Python/Tk with the package manager
#   --no-wine      don't install Wine now (Whiskey can do it later: whiskey install-wine)
#   --uninstall    remove Whiskey (your bottles and games are kept)
set -eu

REPO="Mayank141-web/Whiskey-Clone"
PREFIX="${PREFIX:-/usr/local}"
DEPS=1
WINE=1
UNINSTALL=0

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift ;;
        --prefix=*) PREFIX="${1#--prefix=}" ;;
        --no-deps) DEPS=0 ;;
        --no-wine) WINE=0 ;;
        --uninstall) UNINSTALL=1 ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
LIBDIR="$PREFIX/lib/whiskey"
BINDIR="$PREFIX/bin"
SHAREDIR="$PREFIX/share"

if [ "$UNINSTALL" = 1 ]; then
    rm -rf "$LIBDIR" "$BINDIR/whiskey" "$SHAREDIR/applications/whiskey.desktop" \
           "$SHAREDIR/icons/hicolor/scalable/apps/whiskey.svg"
    say "Whiskey removed. Your bottles are still in ~/.local/share/whiskey (Linux/FreeBSD)"
    say "or ~/Library/Application Support/Whiskey (macOS); delete that folder to remove them too."
    exit 0
fi

if [ "$(id -u)" != 0 ] && [ ! -w "$PREFIX" ]; then
    echo "Please run with sudo:  sudo sh $0 $*" >&2
    exit 1
fi

# ---------------------------------------------------------------- dependencies
install_deps() {
    say "Installing Python and Tk (for the Whiskey window)..."
    if have apt-get; then
        DEBIAN_FRONTEND=noninteractive apt-get update -q && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-tk
    elif have dnf; then dnf install -y python3 python3-tkinter
    elif have yum; then yum install -y python3 python3-tkinter
    elif have pacman; then pacman -Sy --needed --noconfirm python tk
    elif have zypper; then zypper --non-interactive install python3 python3-tk
    elif have apk; then apk add python3 py3-tkinter
    elif have xbps-install; then xbps-install -Sy python3 python3-tkinter
    elif have eopkg; then eopkg install -y python3 python3-tkinter
    elif have urpmi; then urpmi --auto python3 tkinter3
    elif have emerge; then emerge --noreplace dev-lang/python dev-lang/tk
    elif [ "$OS" = FreeBSD ] && have pkg; then
        ASSUME_ALWAYS_YES=yes pkg bootstrap -y >/dev/null 2>&1 || true
        pkg install -y python3
        PYV="$(python3 -c 'import sys; print("py%d%d" % sys.version_info[:2])')"
        pkg install -y "$PYV-tkinter" || pkg install -y "$PYV-tk" || true
    elif [ "$OS" = Darwin ]; then
        : # macOS ships python3 with Tk; Homebrew users should use the brew formula instead.
    else
        echo "Unknown package manager: please install python3 and Tkinter yourself." >&2
    fi
}

if [ "$DEPS" = 1 ]; then
    install_deps || echo "Warning: could not install all dependencies; continuing." >&2
fi

if ! have python3; then
    echo "python3 is required but was not found." >&2
    exit 1
fi

# ---------------------------------------------------------------- get the source
SRC=""
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/whiskey/__init__.py" ]; then
    SRC="$SCRIPT_DIR"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    if [ -n "${WHISKEY_VERSION:-}" ]; then
        URL="https://github.com/$REPO/releases/download/$WHISKEY_VERSION/whiskey.tar.gz"
    else
        URL="https://github.com/$REPO/releases/latest/download/whiskey.tar.gz"
    fi
    say "Downloading Whiskey from $URL"
    if have curl; then curl -fsSL "$URL" -o "$TMP/whiskey.tar.gz"
    elif have wget; then wget -qO "$TMP/whiskey.tar.gz" "$URL"
    elif have fetch; then fetch -qo "$TMP/whiskey.tar.gz" "$URL"
    else echo "Need curl, wget or fetch to download Whiskey." >&2; exit 1
    fi
    tar -xzf "$TMP/whiskey.tar.gz" -C "$TMP"
    SRC="$(dirname "$(find "$TMP" -name __init__.py -path '*/whiskey/__init__.py' | head -n 1)")/.."
fi

# ---------------------------------------------------------------- install files
say "Installing Whiskey into $PREFIX"
rm -rf "$LIBDIR"
mkdir -p "$LIBDIR" "$BINDIR"
cp -R "$SRC/whiskey" "$LIBDIR/"
find "$LIBDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

cat > "$BINDIR/whiskey" <<EOF
#!/bin/sh
PYTHONPATH="$LIBDIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m whiskey "\$@"
EOF
chmod 755 "$BINDIR/whiskey"

if [ "$OS" != Darwin ]; then
    mkdir -p "$SHAREDIR/applications" "$SHAREDIR/icons/hicolor/scalable/apps"
    cp "$SRC/whiskey/resources/whiskey.svg" "$SHAREDIR/icons/hicolor/scalable/apps/whiskey.svg"
    PYTHONPATH="$LIBDIR" python3 -c 'from whiskey.desktop import desktop_entry; print(desktop_entry(), end="")' \
        > "$SHAREDIR/applications/whiskey.desktop"
    have update-desktop-database && update-desktop-database "$SHAREDIR/applications" >/dev/null 2>&1 || true
    have gtk-update-icon-cache && gtk-update-icon-cache -q "$SHAREDIR/icons/hicolor" >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------- Wine
if [ "$WINE" = 1 ]; then
    if [ "$OS" = Darwin ]; then
        say "On macOS, finish by running (without sudo):  whiskey install-wine"
    else
        say "Installing Wine (this is what actually runs Windows programs)..."
        "$BINDIR/whiskey" install-wine || echo "Wine install failed; try again later with: whiskey install-wine" >&2
    fi
fi

say "Done! Open Whiskey from your app menu, or run:  whiskey"
say "Play a Pokemon fan game:  whiskey pokemon ~/Downloads/YourGame.zip"
