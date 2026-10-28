"""Game helpers: find a game's .exe, unpack downloaded archives and set up Pokemon fan games."""

import os
import re
import shutil
import subprocess
import zipfile

from . import bottles, system

POKEMON_BOTTLE = "Pokemon"

ARCHIVE_EXTS = (".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")
FONT_EXTS = (".ttf", ".otf", ".ttc", ".fon")

# Executables that are never the thing you want to play.
NOT_THE_GAME = re.compile(
    r"(unins|setup|install|update|patch|config|crash|vcredist|dxsetup|directx|"
    r"rtp|7z|unrar|winrar|redist|launcher_update|editor|rpgxp|rpgvx|rpgmaker)", re.I)
PREFERRED = ("game.exe", "play.exe", "start.exe")


def is_archive(path):
    return path.lower().endswith(ARCHIVE_EXTS)


def _candidate_exes(folder, max_depth=3):
    base_depth = folder.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(folder):
        depth = root.count(os.sep) - base_depth
        if depth >= max_depth:
            dirs[:] = []
        dirs.sort()
        for fname in sorted(files):
            if fname.lower().endswith(".exe"):
                yield depth, os.path.join(root, fname)


def find_game_exe(folder):
    """Guess which .exe in ``folder`` starts the game.

    Prefers Game.exe (what RPG Maker / Pokemon Essentials games use), then the
    shallowest, largest executable that isn't an installer or tool.
    """
    candidates = list(_candidate_exes(folder))
    if not candidates:
        return None
    for depth, path in sorted(candidates):
        if os.path.basename(path).lower() in PREFERRED:
            return path
    good = [(d, p) for d, p in candidates if not NOT_THE_GAME.search(os.path.basename(p))]
    pool = good or candidates
    pool.sort(key=lambda dp: (dp[0], -os.path.getsize(dp[1])))
    return pool[0][1]


def archive_stem(path):
    name = os.path.basename(path)
    for ext in sorted(ARCHIVE_EXTS, key=len, reverse=True):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return os.path.splitext(name)[0]


def extract_archive(path, dest_root=None, log=None):
    """Unpack a downloaded game archive into Whiskey's Games folder and return the folder."""
    dest_root = dest_root or system.games_dir()
    dest = os.path.join(dest_root, archive_stem(path))
    if os.path.isdir(dest) and os.listdir(dest):
        if log:
            log("Already unpacked: %s" % dest)
        return dest
    os.makedirs(dest, exist_ok=True)
    if log:
        log("Unpacking %s ..." % os.path.basename(path))
    lower = path.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                # Many fan games are zipped on Windows with cp437 names; keep them readable.
                if not info.flag_bits & 0x800:
                    try:
                        info.filename = info.filename.encode("cp437").decode("utf-8")
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass
                target = os.path.realpath(os.path.join(dest, info.filename))
                if not target.startswith(os.path.realpath(dest) + os.sep) and target != os.path.realpath(dest):
                    raise ValueError("Unsafe path in archive: %s" % info.filename)
                zf.extract(info, dest)
    elif lower.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
        shutil.unpack_archive(path, dest)
    else:
        tools = [
            ["7z", "x", "-y", "-o" + dest, path],
            ["7zz", "x", "-y", "-o" + dest, path],
            ["unar", "-q", "-o", dest, "-f", "-D", path],
            ["bsdtar", "-xf", path, "-C", dest],
            ["unrar", "x", "-o+", path, dest + os.sep],
        ]
        if system.is_macos():
            tools.append(["tar", "-xf", path, "-C", dest])  # macOS tar is bsdtar
        for cmd in tools:
            if system.which(cmd[0]) and subprocess.call(cmd) == 0:
                break
        else:
            shutil.rmtree(dest, ignore_errors=True)
            raise RuntimeError(
                "Can't unpack %s. Install 7-Zip (Linux/FreeBSD: p7zip or 7zip, macOS: brew install sevenzip) "
                "or unpack it yourself and choose the folder instead." % os.path.basename(path))
    return dest


def find_fonts(folder):
    fonts = []
    for root, dirs, files in os.walk(folder):
        for fname in files:
            if fname.lower().endswith(FONT_EXTS):
                fonts.append(os.path.join(root, fname))
    return fonts


def resolve_game(path, log=None):
    """Turn a folder, archive or .exe into the path of the game's executable."""
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(path):
        raise FileNotFoundError("Not found: %s" % path)
    if os.path.isfile(path) and is_archive(path):
        path = extract_archive(path, log=log)
    if os.path.isdir(path):
        exe = find_game_exe(path)
        if not exe:
            raise RuntimeError("No .exe file was found in %s" % path)
        return exe
    return path


def setup_pokemon_game(path, bottle_name=POKEMON_BOTTLE, name=None, launch=True, log=None):
    """One-step setup for a Pokemon fan game (Pokemon Essentials / RPG Maker based).

    1. Unpacks the download if it's an archive and finds Game.exe.
    2. Creates (or reuses) a 'Pokemon' bottle set to Windows 10.
    3. Installs the game's bundled fonts into the bottle so text renders correctly.
    4. Adds the game to the bottle's library and launches it.
    """
    exe = resolve_game(path, log=log)
    if log:
        log("Game executable: %s" % exe)
    bottle = bottles.get_or_create_bottle(bottle_name, log=log)
    game_dir = os.path.dirname(exe)
    fonts = find_fonts(game_dir)
    if fonts:
        copied = bottle.install_fonts(fonts)
        if log and copied:
            log("Installed %d font(s) from the game into the bottle." % copied)
    added = bottle.add_program(exe, name=name)
    if log:
        log("Added '%s' to bottle '%s'." % (added, bottle.name))
    proc = None
    if launch:
        if log:
            log("Launching... (logs: %s)" % bottle.logs_dir)
        proc = bottle.run(exe)
    return bottle, added, proc
