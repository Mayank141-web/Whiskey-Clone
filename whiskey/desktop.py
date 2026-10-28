"""Desktop integration: a Whiskey.app on macOS, a menu entry + 'Open with' on Linux/FreeBSD."""

import os
import plistlib
import shutil
import stat
import subprocess
import sys

from . import APP_NAME, __version__, system

ICON_SVG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "whiskey.svg")

EXE_MIME_TYPES = [
    "application/x-ms-dos-executable",
    "application/x-msdownload",
    "application/x-msi",
    "application/x-ms-shortcut",
    "application/vnd.microsoft.portable-executable",
]


def launcher_command():
    """The command that starts Whiskey as it is installed right now."""
    exe = shutil.which("whiskey")
    if exe:
        return [os.path.abspath(exe)]
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return ["env", "PYTHONPATH=" + pkg_parent, sys.executable, "-m", "whiskey"]


def _sh_quote(arg):
    return "'" + arg.replace("'", "'\\''") + "'"


def make_macos_app(dest_dir=None):
    """Build ~/Applications/Whiskey.app. Built locally, so Gatekeeper never quarantines it."""
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
        "CFBundleIdentifier": "io.github.mayank141-web.whiskey",
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
    """Install a menu entry so Whiskey shows up in the app launcher and in 'Open with'."""
    data = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    apps_dir = apps_dir or os.path.join(data, "applications")
    os.makedirs(apps_dir, exist_ok=True)
    cmd = " ".join(_sh_quote(a) if " " in a else a for a in launcher_command())
    icon = "whiskey"
    if os.path.exists(ICON_SVG):
        icon_dir = os.path.join(data, "icons", "hicolor", "scalable", "apps")
        os.makedirs(icon_dir, exist_ok=True)
        shutil.copy2(ICON_SVG, os.path.join(icon_dir, "whiskey.svg"))
    path = os.path.join(apps_dir, "whiskey.desktop")
    with open(path, "w") as fh:
        fh.write(desktop_entry(cmd + " gui", icon))
    if shutil.which("update-desktop-database"):
        subprocess.call(["update-desktop-database", apps_dir],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def desktop_entry(exec_cmd="whiskey gui", icon="whiskey"):
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Whiskey\n"
        "GenericName=Windows Program Runner\n"
        "Comment=Run Windows apps and games (like Pokemon fan games) with Wine\n"
        "Exec=%s %%f\n"
        "Icon=%s\n"
        "Terminal=false\n"
        "Categories=Game;Utility;Emulator;\n"
        "MimeType=%s;\n"
        "Keywords=wine;windows;exe;pokemon;games;\n" % (exec_cmd, icon, ";".join(EXE_MIME_TYPES))
    )


def make_shortcut():
    if system.is_macos():
        return make_macos_app()
    return make_linux_desktop_entry()
