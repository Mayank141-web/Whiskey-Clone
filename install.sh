#!/bin/sh
# Beer installer for Linux (any distro), FreeBSD and macOS.
#
#   curl -fsSL https://github.com/Mayank141-web/Whiskey-Clone/releases/latest/download/install.sh | sudo sh
#
# or from a downloaded copy of the source:   sudo ./install.sh
#
# Private repository? Sign in once with the GitHub CLI, then:
#   gh release download -R Mayank141-web/Whiskey-Clone -p install.sh -p beer.tar.gz -D /tmp/beer --clobber
#   sudo sh /tmp/beer/install.sh
#
# Options:
#   --prefix DIR   install under DIR (default /usr/local)
#   --no-deps      don't install Python/Tk with the package manager
#   --no-wine      don't install Wine now (Beer can do it later: beer install-wine)
#   --uninstall    remove Beer (your bottles and games are kept)
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
LIBDIR="$PREFIX/lib/beer"
BINDIR="$PREFIX/bin"
SHAREDIR="$PREFIX/share"

if [ "$UNINSTALL" = 1 ]; then
    rm -rf "$LIBDIR" "$BINDIR/beer" "$SHAREDIR/applications/beer.desktop" \
           "$SHAREDIR/icons/hicolor/scalable/apps/beer.svg"
    say "Beer removed. Your bottles are still in ~/.local/share/beer (Linux/FreeBSD)"
    say "or ~/Library/Application Support/Beer (macOS); delete that folder to remove them too."
    exit 0
fi

if [ "$(id -u)" != 0 ] && [ ! -w "$PREFIX" ]; then
    echo "Please run with sudo:  sudo sh $0 $*" >&2
    exit 1
fi

# ---------------------------------------------------------------- dependencies
install_deps() {
    say "Installing Python and Tk (for the Beer window)..."
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

# ---------------------------------------------------------------- downloading
# Works for public and private repos. For a private repo, a GitHub token is taken
# from GITHUB_TOKEN / GH_TOKEN, or from the GitHub CLI ('gh auth login') of the
# user who ran sudo.
github_token() {
    if [ -n "${GITHUB_TOKEN:-}" ]; then echo "$GITHUB_TOKEN"; return; fi
    if [ -n "${GH_TOKEN:-}" ]; then echo "$GH_TOKEN"; return; fi
    have gh || return 0
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != root ]; then
        if have sudo; then sudo -u "$SUDO_USER" gh auth token 2>/dev/null || true; fi
    elif [ -n "${DOAS_USER:-}" ]; then
        su -m "$DOAS_USER" -c 'gh auth token' 2>/dev/null || true
    else
        gh auth token 2>/dev/null || true
    fi
}

fetch_url() {  # fetch_url URL DEST [HEADER [HEADER]]
    _fu_url="$1"; _fu_dest="$2"; shift 2
    if have curl; then
        case $# in
            0) curl -fsSL --retry 3 -o "$_fu_dest" "$_fu_url" ;;
            1) curl -fsSL --retry 3 -H "$1" -o "$_fu_dest" "$_fu_url" ;;
            *) curl -fsSL --retry 3 -H "$1" -H "$2" -o "$_fu_dest" "$_fu_url" ;;
        esac
    elif have wget; then
        case $# in
            0) wget -q -O "$_fu_dest" "$_fu_url" ;;
            1) wget -q --header="$1" -O "$_fu_dest" "$_fu_url" ;;
            *) wget -q --header="$1" --header="$2" -O "$_fu_dest" "$_fu_url" ;;
        esac
    elif have fetch && [ $# -eq 0 ]; then
        fetch -qo "$_fu_dest" "$_fu_url"
    else
        echo "Need curl or wget to download Beer." >&2; return 1
    fi
}

download_release_file() {  # download_release_file NAME DEST
    _dr_name="$1"; _dr_dest="$2"
    _dr_tag="${BEER_VERSION:-}"
    if [ -n "$_dr_tag" ]; then
        _dr_url="https://github.com/$REPO/releases/download/$_dr_tag/$_dr_name"
    else
        _dr_url="https://github.com/$REPO/releases/latest/download/$_dr_name"
    fi
    say "Downloading $_dr_name"
    if fetch_url "$_dr_url" "$_dr_dest" 2>/dev/null; then return 0; fi

    # Private repo: ask the GitHub API for the file, using a token.
    _dr_token="$(github_token)"
    if [ -z "$_dr_token" ]; then
        echo "Could not download $_dr_name. If the repository is private, first sign in with the" >&2
        echo "GitHub CLI ('gh auth login'), or set GITHUB_TOKEN, then run this again." >&2
        return 1
    fi
    if [ -n "$_dr_tag" ]; then _dr_api="https://api.github.com/repos/$REPO/releases/tags/$_dr_tag"
    else _dr_api="https://api.github.com/repos/$REPO/releases/latest"; fi
    fetch_url "$_dr_api" "$_dr_dest.json" "Authorization: Bearer $_dr_token" "Accept: application/vnd.github+json"
    _dr_asset="$(python3 -c '
import json, sys
for a in json.load(open(sys.argv[1]))["assets"]:
    if a["name"] == sys.argv[2]:
        print(a["url"])
' "$_dr_dest.json" "$_dr_name")"
    rm -f "$_dr_dest.json"
    if [ -z "$_dr_asset" ]; then echo "The release has no file called $_dr_name." >&2; return 1; fi
    fetch_url "$_dr_asset" "$_dr_dest" "Authorization: Bearer $_dr_token" "Accept: application/octet-stream"
}

# ---------------------------------------------------------------- get the source
SRC=""
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/beer/__init__.py" ]; then
    SRC="$SCRIPT_DIR"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/beer.tar.gz" ]; then
        # Downloaded next to this script (e.g. with 'gh release download' from a private repo).
        cp "$SCRIPT_DIR/beer.tar.gz" "$TMP/beer.tar.gz"
    else
        download_release_file beer.tar.gz "$TMP/beer.tar.gz"
    fi
    tar -xzf "$TMP/beer.tar.gz" -C "$TMP"
    SRC="$(dirname "$(find "$TMP" -name __init__.py -path '*/beer/__init__.py' | head -n 1)")/.."
fi

# ---------------------------------------------------------------- install files
say "Installing Beer into $PREFIX"
rm -rf "$LIBDIR"
mkdir -p "$LIBDIR" "$BINDIR"
cp -R "$SRC/beer" "$LIBDIR/"
find "$LIBDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

cat > "$BINDIR/beer" <<EOF
#!/bin/sh
PYTHONPATH="$LIBDIR\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m beer "\$@"
EOF
chmod 755 "$BINDIR/beer"

if [ "$OS" != Darwin ]; then
    mkdir -p "$SHAREDIR/applications" "$SHAREDIR/icons/hicolor/scalable/apps"
    cp "$SRC/beer/resources/beer.svg" "$SHAREDIR/icons/hicolor/scalable/apps/beer.svg"
    PYTHONPATH="$LIBDIR" python3 -c 'from beer.desktop import desktop_entry; print(desktop_entry(), end="")' \
        > "$SHAREDIR/applications/beer.desktop"
    have update-desktop-database && update-desktop-database "$SHAREDIR/applications" >/dev/null 2>&1 || true
    have gtk-update-icon-cache && gtk-update-icon-cache -q "$SHAREDIR/icons/hicolor" >/dev/null 2>&1 || true
fi

# ---------------------------------------------------------------- Wine
if [ "$WINE" = 1 ]; then
    if [ "$OS" = Darwin ]; then
        say "On macOS, finish by running (without sudo):  beer install-wine"
    else
        say "Installing Wine (this is what actually runs Windows programs)..."
        "$BINDIR/beer" install-wine || echo "Wine install failed; try again later with: beer install-wine" >&2
    fi
fi

say "Done! Open Beer from your app menu, or run:  beer"
say "Play a Pokemon fan game:  beer pokemon ~/Downloads/YourGame.zip"
