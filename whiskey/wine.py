"""Finding and installing Wine, the compatibility layer that actually runs Windows programs.

Whiskey does not translate Windows programs itself: Wine does. Whiskey's job is to get a
working Wine onto the machine and drive it so you never have to touch a terminal.
"""

import glob
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request

from . import system

GCENX_RELEASES_API = "https://api.github.com/repos/Gcenx/macOS_Wine_builds/releases?per_page=30"
WINETRICKS_URL = "https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"

# On macOS these are the places a Wine.app bundle may live.
MAC_APP_GLOBS = [
    os.path.join("{runtime}", "*.app"),
    "/Applications/Wine*.app",
    os.path.expanduser("~/Applications/Wine*.app"),
]


class WineNotFound(RuntimeError):
    pass


def _log(log, msg):
    if log:
        log(msg)


# --------------------------------------------------------------------------- discovery

def _mac_candidates():
    found = []
    for pattern in MAC_APP_GLOBS:
        pattern = pattern.format(runtime=system.runtime_dir())
        for app in sorted(glob.glob(pattern)):
            bindir = os.path.join(app, "Contents", "Resources", "wine", "bin")
            found.append(bindir)
    for bindir in ("/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin"):
        found.append(bindir)
    return found


def _pick_binary(bindir):
    names = ["wine64", "wine"] if system.is_macos() else ["wine", "wine64"]
    for name in names:
        path = os.path.join(bindir, name)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def find_wine():
    """Return the path of the wine executable to use, or None."""
    override = os.environ.get("WHISKEY_WINE")
    if override and os.access(override, os.X_OK):
        return override
    if system.is_macos():
        for bindir in _mac_candidates():
            path = _pick_binary(bindir)
            if path:
                return path
    for name in ("wine", "wine64"):
        path = system.which(name)
        if path:
            return path
    # FreeBSD's 32-bit wine lives in a separate tree.
    path = _pick_binary("/usr/local/wine-proton/bin")
    return path


def require_wine():
    path = find_wine()
    if not path:
        raise WineNotFound(
            "Wine is not installed yet. Run 'whiskey install-wine' "
            "(or click 'Install Wine' in the app)."
        )
    return path


def wineserver_for(wine):
    path = os.path.join(os.path.dirname(wine), "wineserver")
    if os.path.exists(path):
        return path
    return system.which("wineserver")


def wine_version(wine=None):
    wine = wine or find_wine()
    if not wine:
        return None
    try:
        out = subprocess.run([wine, "--version"], capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def find_winetricks():
    path = system.which("winetricks")
    if path:
        return path
    local = os.path.join(system.data_dir(), "bin", "winetricks")
    if os.access(local, os.X_OK):
        return local
    return None


def install_winetricks(log=None):
    """Download winetricks into Whiskey's own folder if the system doesn't have it."""
    existing = find_winetricks()
    if existing:
        return existing
    dest = os.path.join(system.data_dir(), "bin", "winetricks")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    _log(log, "Downloading winetricks...")
    _download(WINETRICKS_URL, dest)
    os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dest


# --------------------------------------------------------------------------- install plans

def detect_package_manager():
    """Name of the system package manager we know how to drive, or None."""
    if system.os_name() == "freebsd":
        return "pkg" if system.which("pkg") else None
    if system.is_macos():
        return "brew" if system.which("brew") else None
    for name in ("apt-get", "dnf", "yum", "pacman", "zypper", "apk", "xbps-install",
                 "emerge", "eopkg", "nix-env", "swupd", "urpmi"):
        if system.which(name):
            return name
    return None


def linux_install_steps(pm):
    """Steps to install Wine with package manager ``pm``.

    Each step is a list of alternative commands; the first alternative that
    succeeds completes the step. Commands that need root are prefixed later.
    """
    if pm == "apt-get":
        return [
            [["dpkg", "--add-architecture", "i386"]],
            [["apt-get", "update"]],
            [
                ["apt-get", "install", "-y", "--install-recommends",
                 "wine", "wine64", "wine32:i386", "winetricks"],
                ["apt-get", "install", "-y", "--install-recommends", "wine", "winetricks"],
                ["apt-get", "install", "-y", "wine"],
            ],
        ]
    if pm in ("dnf", "yum"):
        return [[[pm, "install", "-y", "wine", "winetricks"], [pm, "install", "-y", "wine"]]]
    if pm == "pacman":
        return [[["pacman", "-Sy", "--needed", "--noconfirm", "wine", "winetricks"],
                 ["pacman", "-Sy", "--needed", "--noconfirm", "wine"]]]
    if pm == "zypper":
        return [[["zypper", "--non-interactive", "install", "wine", "winetricks"],
                 ["zypper", "--non-interactive", "install", "wine"]]]
    if pm == "apk":
        return [[["apk", "add", "wine"]]]
    if pm == "xbps-install":
        return [[["xbps-install", "-Sy", "wine", "wine-32bit", "winetricks"],
                 ["xbps-install", "-Sy", "wine"]]]
    if pm == "emerge":
        return [[["emerge", "--noreplace", "app-emulation/wine-vanilla"]]]
    if pm == "eopkg":
        return [[["eopkg", "install", "-y", "wine", "winetricks"], ["eopkg", "install", "-y", "wine"]]]
    if pm == "nix-env":
        return [[["nix-env", "-iA", "nixpkgs.wineWowPackages.stable", "nixpkgs.winetricks"]]]
    if pm == "swupd":
        return [[["swupd", "bundle-add", "wine"]]]
    if pm == "urpmi":
        return [[["urpmi", "--auto", "wine"]]]
    if pm == "pkg":  # FreeBSD
        return [
            [["pkg", "install", "-y", "wine", "winetricks"], ["pkg", "install", "-y", "wine"]],
            # 32-bit Windows programs (most RPG Maker / Pokemon games) need the i386 add-on.
            [["/usr/local/share/wine/pkg32.sh", "install", "-y", "wine", "mesa-dri"], ["true"]],
        ]
    return []


NEEDS_ROOT = {"apt-get", "dnf", "yum", "pacman", "zypper", "apk", "xbps-install", "emerge",
              "eopkg", "swupd", "urpmi", "pkg", "dpkg", "/usr/local/share/wine/pkg32.sh"}


def _run_steps(steps, log, dry_run=False):
    sudo = system.sudo_prefix()
    for alternatives in steps:
        ok = False
        for cmd in alternatives:
            if cmd[0] in NEEDS_ROOT:
                cmd = sudo + cmd
            _log(log, "$ " + " ".join(cmd))
            if dry_run:
                ok = True
                break
            try:
                if subprocess.call(cmd) == 0:
                    ok = True
                    break
            except OSError as exc:
                _log(log, "  failed: %s" % exc)
        if not ok:
            return False
    return True


# --------------------------------------------------------------------------- macOS

def _download(url, dest):
    """Download with curl when present (it uses the system certificate store), else urllib."""
    if system.which("curl"):
        subprocess.check_call(["curl", "-fL", "--retry", "3", "-o", dest, url])
        return
    req = urllib.request.Request(url, headers={"User-Agent": "Whiskey"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _fetch_json(url):
    if system.which("curl"):
        out = subprocess.check_output(["curl", "-fsSL", "-H", "Accept: application/vnd.github+json", url])
        return json.loads(out.decode("utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "Whiskey"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def pick_mac_wine_asset(releases):
    """Choose the best Wine build from Gcenx/macOS_Wine_builds release metadata.

    Prefers the newest stable build, then devel, then staging.
    """
    for flavour in ("stable", "devel", "staging"):
        pattern = re.compile(r"^wine-%s-[\d.]+(-\d+)?-osx64\.tar\.xz$" % flavour)
        for release in releases:
            if release.get("draft"):
                continue
            for asset in release.get("assets", []):
                if pattern.match(asset.get("name", "")):
                    return asset["name"], asset["browser_download_url"]
    return None


def ensure_rosetta(log=None):
    """Wine builds for macOS are Intel binaries; Apple Silicon needs Rosetta 2."""
    if not system.is_apple_silicon():
        return True
    if subprocess.call(["arch", "-x86_64", "/usr/bin/true"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
        return True
    _log(log, "Installing Rosetta 2 (needed to run Wine on Apple Silicon)...")
    return subprocess.call(["softwareupdate", "--install-rosetta", "--agree-to-license"]) == 0


def unquarantine(path):
    """Strip Gatekeeper's quarantine flag so macOS lets the unsigned Wine build run."""
    if system.is_macos() and os.path.exists(path):
        subprocess.call(["xattr", "-dr", "com.apple.quarantine", path],
                        stderr=subprocess.DEVNULL)


def install_wine_macos(log=None):
    if not ensure_rosetta(log):
        _log(log, "Rosetta 2 could not be installed; Wine will not run without it.")
        return False
    runtime = system.runtime_dir()
    os.makedirs(runtime, exist_ok=True)
    try:
        _log(log, "Looking up the newest Wine build for macOS...")
        picked = pick_mac_wine_asset(_fetch_json(GCENX_RELEASES_API))
        if not picked:
            raise RuntimeError("no macOS Wine build found in the release list")
        name, url = picked
        _log(log, "Downloading %s ..." % name)
        tmp = tempfile.mkdtemp(prefix="whiskey-")
        archive = os.path.join(tmp, name)
        _download(url, archive)
        _log(log, "Unpacking...")
        for old in glob.glob(os.path.join(runtime, "*.app")):
            shutil.rmtree(old, ignore_errors=True)
        subprocess.check_call(["tar", "-xf", archive, "-C", runtime])
        shutil.rmtree(tmp, ignore_errors=True)
        unquarantine(runtime)
        if find_wine():
            return True
        raise RuntimeError("the downloaded archive did not contain a Wine.app")
    except Exception as exc:  # fall back to Homebrew / MacPorts below
        _log(log, "Direct download failed: %s" % exc)

    if system.which("brew"):
        _log(log, "Trying Homebrew instead...")
        for cmd in (["brew", "install", "--cask", "gcenx/wine/wine-crossover"],
                    ["brew", "install", "--cask", "wine-stable"]):
            _log(log, "$ " + " ".join(cmd))
            if subprocess.call(cmd) == 0:
                for app in glob.glob("/Applications/Wine*.app"):
                    unquarantine(app)
                if find_wine():
                    return True
    if system.which("port"):
        _log(log, "Trying MacPorts instead...")
        if _run_steps([[["port", "install", "wine-stable"]]], log):
            return bool(find_wine())
    return False


# --------------------------------------------------------------------------- entry point

def install_wine(log=print, dry_run=False):
    """Install Wine for the current OS. Returns True on success."""
    name = system.os_name()
    if name == "macos":
        if dry_run:
            _log(log, "Would download the latest Wine build from Gcenx/macOS_Wine_builds")
            return True
        ok = install_wine_macos(log)
    else:
        pm = detect_package_manager()
        steps = linux_install_steps(pm) if pm else []
        if pm == "pkg":
            steps = [[["pkg", "bootstrap", "-y"], ["true"]]] + steps
        if not steps:
            _log(log, "Could not find a supported package manager on %s." % system.describe())
            _log(log, "Install Wine with your distribution's tools (package name is usually 'wine'), "
                      "or via Flatpak: flatpak install flathub org.winehq.Wine")
            return False
        if steps and not system.sudo_prefix() and os.geteuid() != 0:
            _log(log, "Installing Wine needs administrator rights, but neither sudo nor doas was found.")
            return False
        _log(log, "Installing Wine with %s (you may be asked for your password)..." % pm)
        ok = _run_steps(steps, log, dry_run=dry_run)
        if dry_run:
            return ok
    found = find_wine()
    if found:
        _log(log, "Wine is ready: %s (%s)" % (found, wine_version(found) or "unknown version"))
        return True
    _log(log, "Wine installation did not finish successfully.")
    return False
