"""Host operating system detection, data directories and package managers."""

import os
import platform
import shutil
import subprocess
import sys


def os_name():
    """Return 'macos', 'linux', 'freebsd' or the raw lower-cased system name."""
    name = platform.system().lower()
    if name == "darwin":
        return "macos"
    return name


def is_macos():
    return os_name() == "macos"


def is_apple_silicon():
    return is_macos() and platform.machine() == "arm64"


def data_dir():
    """Where Beer keeps its bottles, Wine runtime and games."""
    override = os.environ.get("BEER_HOME")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    home = os.path.expanduser("~")
    if is_macos():
        return os.path.join(home, "Library", "Application Support", "Beer")
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    return os.path.join(xdg, "beer")


def bottles_dir():
    return os.path.join(data_dir(), "Bottles")


def runtime_dir():
    """Wine builds downloaded by Beer itself (used on macOS)."""
    return os.path.join(data_dir(), "Wine")


def games_dir():
    """Games extracted from archives by Beer."""
    return os.path.join(data_dir(), "Games")


def read_os_release():
    info = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path) as fh:
                for line in fh:
                    if "=" in line:
                        key, _, value = line.strip().partition("=")
                        info[key] = value.strip().strip('"')
            break
        except OSError:
            continue
    return info


def describe():
    """A one-line description of the host, e.g. 'Linux (Ubuntu 24.04 LTS, x86_64)'."""
    name = os_name()
    machine = platform.machine()
    if name == "macos":
        return "macOS %s (%s)" % (platform.mac_ver()[0] or "?", machine)
    if name == "linux":
        pretty = read_os_release().get("PRETTY_NAME", "unknown distro")
        return "Linux (%s, %s)" % (pretty, machine)
    if name == "freebsd":
        return "FreeBSD %s (%s)" % (platform.release(), machine)
    return "%s %s (%s)" % (platform.system(), platform.release(), machine)


def which(cmd):
    return shutil.which(cmd)


def has_display():
    if is_macos():
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def sudo_prefix():
    """['sudo'] when we are not root and sudo exists, otherwise []."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    for tool in ("sudo", "doas"):
        if which(tool):
            return [tool]
    return []


def open_path(path):
    """Open a folder or file in the desktop's file manager."""
    if is_macos():
        cmd = ["open", path]
    else:
        cmd = ["xdg-open", path]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


def python_executable():
    return sys.executable or "python3"
