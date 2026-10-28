"""Bottles: isolated Windows environments (Wine prefixes), each with its own C: drive."""

import json
import os
import re
import shutil
import subprocess
import time

from . import system, wine

WINDOWS_VERSIONS = ["win11", "win10", "win81", "win8", "win7", "vista", "winxp"]
DEFAULT_WINDOWS_VERSION = "win10"
CONFIG_NAME = "bottle.json"


class BottleError(RuntimeError):
    pass


def safe_name(name):
    name = re.sub(r"[^\w .+-]", "", name.strip())
    if not name or name in (".", ".."):
        raise BottleError("Please give the bottle a name made of letters or numbers.")
    return name


class Bottle(object):
    def __init__(self, path):
        self.path = path
        self.config = {
            "name": os.path.basename(path),
            "windows_version": DEFAULT_WINDOWS_VERSION,
            "env": {},
            "dll_overrides": {},
            "programs": [],
            "created": None,
        }
        cfg = os.path.join(path, CONFIG_NAME)
        if os.path.exists(cfg):
            with open(cfg) as fh:
                self.config.update(json.load(fh))

    # ----------------------------------------------------------------- basics
    @property
    def name(self):
        return self.config["name"]

    @property
    def prefix(self):
        return os.path.join(self.path, "prefix")

    @property
    def c_drive(self):
        return os.path.join(self.prefix, "drive_c")

    @property
    def logs_dir(self):
        return os.path.join(self.path, "logs")

    @property
    def programs(self):
        return self.config["programs"]

    def save(self):
        os.makedirs(self.path, exist_ok=True)
        tmp = os.path.join(self.path, CONFIG_NAME + ".tmp")
        with open(tmp, "w") as fh:
            json.dump(self.config, fh, indent=2, sort_keys=True)
        os.replace(tmp, os.path.join(self.path, CONFIG_NAME))

    def is_initialized(self):
        return os.path.exists(os.path.join(self.prefix, "system.reg"))

    # ----------------------------------------------------------------- environment
    def environment(self, extra=None):
        env = dict(os.environ)
        env["WINEPREFIX"] = self.prefix
        env.setdefault("WINEDEBUG", "-all")
        overrides = ";".join("%s=%s" % kv for kv in sorted(self.config["dll_overrides"].items()))
        if overrides:
            env["WINEDLLOVERRIDES"] = overrides
        if system.is_macos():
            # Faster synchronisation primitives on macOS builds that support it.
            env.setdefault("WINEMSYNC", "1")
        else:
            env.setdefault("WINEESYNC", "1")
        env.update(self.config["env"])
        if extra:
            env.update(extra)
        return env

    def _wine_call(self, args, wait=True, cwd=None, log_name=None):
        exe = wine.require_wine()
        cmd = [exe] + list(args)
        if wait:
            return subprocess.call(cmd, env=self.environment(), cwd=cwd)
        os.makedirs(self.logs_dir, exist_ok=True)
        log_path = os.path.join(self.logs_dir, "%s-%s.log" % (
            time.strftime("%Y%m%d-%H%M%S"), log_name or "run"))
        log = open(log_path, "w")
        proc = subprocess.Popen(cmd, env=self.environment(), cwd=cwd, stdout=log, stderr=log,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        log.close()
        return proc

    # ----------------------------------------------------------------- actions
    def initialize(self, log=None):
        """Create the Wine prefix (the fake Windows install) for this bottle."""
        os.makedirs(self.prefix, exist_ok=True)
        if log:
            log("Setting up Windows environment in bottle '%s' (first time takes a minute)..." % self.name)
        env = self.environment({"WINEDLLOVERRIDES": "mscoree,mshtml="})  # skip Mono/Gecko popups
        code = subprocess.call([wine.require_wine(), "wineboot", "--init"], env=env)
        wait_for_wineserver(self)
        if code != 0:
            raise BottleError("Wine failed to set up the bottle (exit code %d)." % code)
        self.set_windows_version(self.config["windows_version"])

    def set_windows_version(self, version):
        if version not in WINDOWS_VERSIONS:
            raise BottleError("Unknown Windows version %r. Choose one of: %s"
                              % (version, ", ".join(WINDOWS_VERSIONS)))
        self.config["windows_version"] = version
        self.save()
        if self.is_initialized():
            self._wine_call(["winecfg", "-v", version])

    def run(self, exe_path, args=None, wait=False):
        """Launch a Windows program (.exe, .msi, .bat, .lnk) inside this bottle."""
        exe_path = os.path.abspath(exe_path)
        if not os.path.exists(exe_path):
            raise BottleError("File not found: %s" % exe_path)
        if not self.is_initialized():
            self.initialize()
        cwd = os.path.dirname(exe_path)  # games look for their data next to the .exe
        lower = exe_path.lower()
        if lower.endswith(".msi"):
            wine_args = ["msiexec", "/i", exe_path]
        elif lower.endswith((".bat", ".cmd", ".lnk")):
            wine_args = ["start", "/unix", exe_path]
        else:
            wine_args = [exe_path]
        wine_args += list(args or [])
        name = os.path.splitext(os.path.basename(exe_path))[0]
        return self._wine_call(wine_args, wait=wait, cwd=cwd, log_name=re.sub(r"\W", "_", name))

    def tool(self, name, args=None, wait=False):
        """Run a built-in Wine tool such as winecfg, regedit, taskmgr, control or explorer."""
        if not self.is_initialized():
            self.initialize()
        return self._wine_call([name] + list(args or []), wait=wait, log_name=name)

    def winetricks(self, verbs, log=None):
        tricks = wine.install_winetricks(log)
        if not self.is_initialized():
            self.initialize(log)
        env = self.environment()
        env["WINE"] = wine.require_wine()
        return subprocess.call([tricks, "-q"] + list(verbs), env=env)

    def kill(self):
        server = wine.wineserver_for(wine.require_wine())
        if server:
            subprocess.call([server, "-k"], env=self.environment())

    def install_fonts(self, font_files):
        """Copy fonts into the bottle's Windows\\Fonts folder (Pokemon fan games ship their own)."""
        dest = os.path.join(self.c_drive, "windows", "Fonts")
        os.makedirs(dest, exist_ok=True)
        copied = 0
        for path in font_files:
            target = os.path.join(dest, os.path.basename(path))
            if not os.path.exists(target):
                shutil.copy2(path, target)
                copied += 1
        return copied

    # ----------------------------------------------------------------- program library
    def add_program(self, exe_path, name=None, args=None):
        exe_path = os.path.abspath(exe_path)
        name = name or default_program_name(exe_path)
        self.config["programs"] = [p for p in self.programs if p["path"] != exe_path]
        self.config["programs"].append({"name": name, "path": exe_path, "args": list(args or [])})
        self.config["programs"].sort(key=lambda p: p["name"].lower())
        self.save()
        return name

    def remove_program(self, name):
        before = len(self.programs)
        self.config["programs"] = [p for p in self.programs if p["name"] != name]
        self.save()
        return len(self.programs) != before

    def find_program(self, name):
        for program in self.programs:
            if program["name"].lower() == name.lower():
                return program
        return None

    def launch_program(self, name):
        program = self.find_program(name)
        if not program:
            raise BottleError("No program called %r in bottle %r." % (name, self.name))
        return self.run(program["path"], program.get("args"))


def default_program_name(exe_path):
    """'Game.exe' isn't a helpful name, so use the game's folder name for generic exe names."""
    base = os.path.splitext(os.path.basename(exe_path))[0]
    if base.lower() in ("game", "play", "start", "launcher", "main", "app"):
        folder = os.path.basename(os.path.dirname(os.path.abspath(exe_path)))
        if folder:
            return folder
    return base


def wait_for_wineserver(bottle, timeout=120):
    try:
        server = wine.wineserver_for(wine.require_wine())
        if server:
            subprocess.call([server, "-w"], env=bottle.environment(), timeout=timeout)
    except (subprocess.TimeoutExpired, wine.WineNotFound):
        pass


# --------------------------------------------------------------------------- collection

def list_bottles():
    root = system.bottles_dir()
    if not os.path.isdir(root):
        return []
    result = []
    for entry in sorted(os.listdir(root), key=str.lower):
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            result.append(Bottle(path))
    return result


def get_bottle(name):
    path = os.path.join(system.bottles_dir(), safe_name(name))
    if not os.path.isdir(path):
        raise BottleError("There is no bottle called %r. Create it with: beer bottle create %s"
                          % (name, name))
    return Bottle(path)


def create_bottle(name, windows_version=DEFAULT_WINDOWS_VERSION, initialize=True, log=None):
    name = safe_name(name)
    path = os.path.join(system.bottles_dir(), name)
    if os.path.exists(path):
        raise BottleError("A bottle called %r already exists." % name)
    bottle = Bottle(path)
    bottle.config["windows_version"] = windows_version
    bottle.config["created"] = time.strftime("%Y-%m-%d %H:%M:%S")
    bottle.save()
    if initialize:
        bottle.initialize(log)
    return bottle


def get_or_create_bottle(name, log=None):
    try:
        return get_bottle(name)
    except BottleError:
        return create_bottle(name, log=log)


def delete_bottle(name):
    bottle = get_bottle(name)
    try:
        bottle.kill()
    except wine.WineNotFound:
        pass
    shutil.rmtree(bottle.path)


def default_bottle_name():
    bottles = list_bottles()
    return bottles[0].name if bottles else "Default"
