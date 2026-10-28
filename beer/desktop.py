"""Desktop integration: a Beer.app on macOS, a menu entry + 'Open with' on Linux/FreeBSD."""

import os
import plistlib
import shutil
import stat
import subprocess
import sys

from . import APP_NAME, __version__, system

ICON_SVG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "beer.svg")

EXE_MIME_TYPES = [
    "application/x-ms-dos-executable",
    "application/x-msdownload",
    "application/x-msi",
    "application/x-ms-shortcut",
    "application/vnd.microsoft.portable-executable",
]


def appimage_path():
    """Path of the Beer AppImage we are running from (Linux), if any."""
    return os.environ.get("APPIMAGE")


def mac_bundle_path():
    """Path of the Beer.app we are running from (macOS download), if any."""
    return os.environ.get("BEER_APP_BUNDLE")


def installed_appimage_path():
    return os.path.expanduser("~/Applications/Beer.AppImage")


def launcher_command():
    """The command that starts Beer as it is installed right now."""
    if appimage_path():
        installed = installed_appimage_path()
        return [installed if os.path.exists(installed) else appimage_path()]
    exe = shutil.which("beer")
    if exe:
        return [os.path.abspath(exe)]
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return ["env", "PYTHONPATH=" + pkg_parent, sys.executable, "-m", "beer"]


def _sh_quote(arg):
    return "'" + arg.replace("'", "'\\''") + "'"


def make_macos_app(dest_dir=None):
    """Build ~/Applications/Beer.app. Built locally, so Gatekeeper never quarantines it."""
    dest_dir = dest_dir or os.path.expanduser("~/Applications")
    app = os.path.join(dest_dir, APP_NAME + ".app")
    if os.path.exists(app):
        shutil.rmtree(app)
    macos = os.path.join(app, "Contents", "MacOS")
    os.makedirs(macos)
    os.makedirs(os.path.join(app, "Contents", "Resources"))
    script = os.path.join(macos, APP_NAME)
    cmd = " ".join(_sh_quote(a) for a in launcher_command())
    with open(script, "w") as fh:
        fh.write("#!/bin/sh\n"
                 "export PATH=\"/opt/homebrew/bin:/usr/local/bin:$PATH\"\n"
                 "exec %s gui \"$@\"\n" % cmd)
    os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "io.github.mayank141-web.beer",
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "CFBundleExecutable": APP_NAME,
        "CFBundlePackageType": "APPL",
        "LSMinimumSystemVersion": "10.15",
        "NSHighResolutionCapable": True,
        "CFBundleDocumentTypes": [{
            "CFBundleTypeName": "Windows Program",
            "CFBundleTypeRole": "Viewer",
            "LSHandlerRank": "Alternate",
            "CFBundleTypeExtensions": ["exe", "msi", "bat", "lnk"],
        }],
    }
    with open(os.path.join(app, "Contents", "Info.plist"), "wb") as fh:
        plistlib.dump(info, fh)
    subprocess.call(["touch", app])
    return app


def make_linux_desktop_entry(apps_dir=None):
    """Install a menu entry so Beer shows up in the app launcher and in 'Open with'."""
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    apps_dir = apps_dir or os.path.join(data, "applications")
    os.makedirs(apps_dir, exist_ok=True)
    cmd = " ".join('"%s"' % a if " " in a else a for a in launcher_command())
    icon = "beer"
    if os.path.exists(ICON_SVG):
        icon_dir = os.path.join(data, "icons", "hicolor", "scalable", "apps")
        os.makedirs(icon_dir, exist_ok=True)
        shutil.copy2(ICON_SVG, os.path.join(icon_dir, "beer.svg"))
    path = os.path.join(apps_dir, "beer.desktop")
    with open(path, "w") as fh:
        fh.write(desktop_entry(cmd + " gui", icon))
    if shutil.which("update-desktop-database"):
        subprocess.call(["update-desktop-database", apps_dir],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def desktop_entry(exec_cmd="beer gui", icon="beer"):
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Beer\n"
        "GenericName=Windows Program Runner\n"
        "Comment=Run Windows apps and games (like Pokemon fan games) with Wine\n"
        "Exec=%s %%f\n"
        "Icon=%s\n"
        "Terminal=false\n"
        "Categories=Game;Utility;Emulator;\n"
        "MimeType=%s;\n"
        "Keywords=wine;windows;exe;pokemon;games;\n" % (exec_cmd, icon, ";".join(EXE_MIME_TYPES))
    )


def desktop_entry_path():
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(data, "applications", "beer.desktop")


def install_appimage():
    """Copy the running AppImage to ~/Applications and add it to the app menu."""
    source = appimage_path()
    dest = installed_appimage_path()
    if source and os.path.abspath(source) != dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(source, dest + ".tmp")
        os.replace(dest + ".tmp", dest)
        os.chmod(dest, os.stat(dest).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return make_linux_desktop_entry()


def install_suggestion():
    """What the app should offer on start: 'appimage' (add to menu) or 'mac-move' (drag to Applications)."""
    if appimage_path() and not os.path.exists(desktop_entry_path()):
        return "appimage"
    bundle = mac_bundle_path()
    if bundle and (bundle.startswith("/Volumes/") or "/AppTranslocation/" in bundle):
        return "mac-move"
    return None


def make_shortcut():
    if system.is_macos():
        if mac_bundle_path():
            return mac_bundle_path()  # already a real app
        return make_macos_app()
    if appimage_path():
        return install_appimage()
    return make_linux_desktop_entry()
