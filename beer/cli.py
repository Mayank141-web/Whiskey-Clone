"""Command line interface. Run 'beer --help' for usage."""

import argparse
import os
import sys

from . import APP_NAME, REPO_URL, __version__, bottles, desktop, games, system, wine

EPILOG = """examples:
  beer                               open the app window
  beer install-wine                  install Wine (one time)
  beer pokemon ~/Downloads/Pokemon_Reborn.zip
                                        unpack, set up and play a Pokemon fan game
  beer run setup.exe                 run any Windows program
  beer launch "Pokemon Reborn"       start a game you already added
  beer list                          show bottles and their games
"""


def _log(msg):
    print(msg, flush=True)


def _bottle(args):
    name = getattr(args, "bottle", None) or bottles.default_bottle_name()
    return bottles.get_or_create_bottle(name, log=_log)


# --------------------------------------------------------------------------- commands

def cmd_gui(args):
    from . import gui
    return gui.main(args.files)


def cmd_doctor(args):
    print("%s %s" % (APP_NAME, __version__))
    print("System:      %s" % system.describe())
    print("Data folder: %s" % system.data_dir())
    exe = wine.find_wine()
    if exe:
        print("Wine:        %s (%s)" % (exe, wine.wine_version(exe) or "version unknown"))
    else:
        print("Wine:        NOT INSTALLED - run 'beer install-wine'")
    print("Winetricks:  %s" % (wine.find_winetricks() or "not installed (downloaded automatically when needed)"))
    pm = wine.detect_package_manager()
    print("Packages:    %s" % (pm or "no supported package manager found"))
    if system.is_apple_silicon():
        print("Note:        Apple Silicon Mac - Wine runs through Rosetta 2 (installed automatically).")
    try:
        import tkinter  # noqa: F401
        print("GUI:         available")
    except ImportError:
        print("GUI:         unavailable (install python3-tk / py3-tkinter / python-tk)")
    return 0 if exe else 1


def cmd_install_wine(args):
    return 0 if wine.install_wine(log=_log, dry_run=args.dry_run) else 1


def cmd_bottle(args):
    if args.action == "create":
        b = bottles.create_bottle(args.name, args.windows, initialize=not args.no_init, log=_log)
        _log("Created bottle '%s' at %s" % (b.name, b.path))
    elif args.action == "delete":
        bottles.delete_bottle(args.name)
        _log("Deleted bottle '%s'." % args.name)
    elif args.action == "info":
        b = bottles.get_bottle(args.name)
        print("Name:            %s" % b.name)
        print("Location:        %s" % b.path)
        print("C: drive:        %s" % b.c_drive)
        print("Windows version: %s" % b.config["windows_version"])
        print("Initialized:     %s" % ("yes" if b.is_initialized() else "no"))
        for p in b.programs:
            print("Program:         %s -> %s" % (p["name"], p["path"]))
    elif args.action == "set-windows":
        b = bottles.get_bottle(args.name)
        b.set_windows_version(args.version)
        _log("Bottle '%s' now pretends to be %s." % (b.name, args.version))
    elif args.action == "env":
        b = bottles.get_bottle(args.name)
        key, sep, value = args.assignment.partition("=")
        if not sep:
            raise bottles.BottleError("Use KEY=VALUE (or KEY= to remove).")
        if value:
            b.config["env"][key] = value
        else:
            b.config["env"].pop(key, None)
        b.save()
    elif args.action == "dll":
        b = bottles.get_bottle(args.name)
        dll, sep, mode = args.assignment.partition("=")
        if mode:
            b.config["dll_overrides"][dll] = mode
        else:
            b.config["dll_overrides"].pop(dll, None)
        b.save()
    return 0


def cmd_list(args):
    all_bottles = bottles.list_bottles()
    if not all_bottles:
        print("No bottles yet. Create one with 'beer bottle create NAME' or just run a program.")
        return 0
    for b in all_bottles:
        print("%s  [%s]" % (b.name, b.config["windows_version"]))
        for p in b.programs:
            print("    %s" % p["name"])
    return 0


def cmd_run(args):
    path = games.resolve_game(args.file, log=_log) if not args.file.lower().endswith(
        (".exe", ".msi", ".bat", ".lnk", ".cmd")) else args.file
    b = _bottle(args)
    if args.add:
        _log("Added '%s' to bottle '%s'." % (b.add_program(path), b.name))
    proc = b.run(path, args.args, wait=args.wait)
    if args.wait:
        return proc
    _log("Started %s in bottle '%s'." % (os.path.basename(path), b.name))
    return 0


def cmd_pokemon(args):
    _, name, proc = games.setup_pokemon_game(
        args.path, bottle_name=args.bottle, name=args.name, launch=not args.no_launch, log=_log)
    _log("Next time just run:  beer launch \"%s\"" % name)
    return 0


def cmd_add(args):
    exe = games.resolve_game(args.path, log=_log)
    b = _bottle(args)
    _log("Added '%s' to bottle '%s'." % (b.add_program(exe, name=args.name, args=args.args), b.name))
    return 0


def cmd_remove(args):
    b = _bottle(args)
    if not b.remove_program(args.name):
        raise bottles.BottleError("No program called %r in bottle %r." % (args.name, b.name))
    return 0


def cmd_launch(args):
    candidates = [bottles.get_bottle(args.bottle)] if args.bottle else bottles.list_bottles()
    for b in candidates:
        if b.find_program(args.name):
            b.launch_program(args.name)
            _log("Started '%s' in bottle '%s'." % (args.name, b.name))
            return 0
    raise bottles.BottleError("No game or program called %r. See 'beer list'." % args.name)


def cmd_tool(args):
    b = _bottle(args)
    if args.command == "winetricks":
        return b.winetricks(args.verbs, log=_log)
    if args.command == "kill":
        b.kill()
        return 0
    if args.command == "drive":
        print(b.c_drive)
        if args.open:
            system.open_path(b.c_drive)
        return 0
    tool = {"winecfg": "winecfg", "regedit": "regedit", "taskmgr": "taskmgr",
            "control": "control", "explorer": "explorer", "cmd": "wineconsole"}[args.command]
    b.tool(tool, wait=True)
    return 0


def cmd_shortcut(args):
    _log("Created %s" % desktop.make_shortcut())
    return 0


def cmd_version(args):
    print("%s %s - %s" % (APP_NAME, __version__, REPO_URL))
    return 0


# --------------------------------------------------------------------------- parser

def build_parser():
    p = argparse.ArgumentParser(
        prog="beer", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=EPILOG,
        description="Run Windows apps and games on macOS, Linux and FreeBSD (powered by Wine).")
    p.add_argument("--version", action="version", version="%s %s" % (APP_NAME, __version__))
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    s = sub.add_parser("gui", help="open the Beer window")
    s.add_argument("files", nargs="*", help="Windows programs to open")
    s.set_defaults(func=cmd_gui)

    s = sub.add_parser("doctor", help="check that everything needed is installed")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("install-wine", help="download and install Wine for this computer")
    s.add_argument("--dry-run", action="store_true", help="only show what would be done")
    s.set_defaults(func=cmd_install_wine)

    s = sub.add_parser("bottle", help="create, delete and configure bottles")
    bsub = s.add_subparsers(dest="action", metavar="ACTION")
    bsub.required = True
    c = bsub.add_parser("create", help="create a new bottle")
    c.add_argument("name")
    c.add_argument("--windows", default=bottles.DEFAULT_WINDOWS_VERSION, choices=bottles.WINDOWS_VERSIONS)
    c.add_argument("--no-init", action="store_true", help="don't set up Windows until first use")
    for action, text in (("delete", "delete a bottle and everything in it"),
                         ("info", "show details about a bottle")):
        bsub.add_parser(action, help=text).add_argument("name")
    c = bsub.add_parser("set-windows", help="change which Windows version the bottle reports")
    c.add_argument("name")
    c.add_argument("version", choices=bottles.WINDOWS_VERSIONS)
    c = bsub.add_parser("env", help="set an environment variable for a bottle (KEY=VALUE)")
    c.add_argument("name")
    c.add_argument("assignment")
    c = bsub.add_parser("dll", help="set a DLL override for a bottle (e.g. d3d9=native,builtin)")
    c.add_argument("name")
    c.add_argument("assignment")
    s.set_defaults(func=cmd_bottle)

    s = sub.add_parser("list", help="list bottles and the games/programs in them")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("run", help="run a Windows program (.exe/.msi), game folder or archive")
    s.add_argument("file")
    s.add_argument("args", nargs=argparse.REMAINDER, help="arguments passed to the program")
    s.add_argument("-b", "--bottle", help="bottle to use (created if missing)")
    s.add_argument("--add", action="store_true", help="also add it to the bottle's library")
    s.add_argument("--wait", action="store_true", help="wait for the program to exit")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("pokemon", help="set up and play a Pokemon fan game (folder, .zip/.rar/.7z or Game.exe)")
    s.add_argument("path")
    s.add_argument("-b", "--bottle", default=games.POKEMON_BOTTLE)
    s.add_argument("-n", "--name", help="name to show in the library")
    s.add_argument("--no-launch", action="store_true", help="set up only, don't start the game")
    s.set_defaults(func=cmd_pokemon)

    s = sub.add_parser("add", help="add a program or game to a bottle's library")
    s.add_argument("path")
    s.add_argument("-b", "--bottle")
    s.add_argument("-n", "--name")
    s.add_argument("args", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_add)

    s = sub.add_parser("remove", help="remove a program from a bottle's library (files are kept)")
    s.add_argument("name")
    s.add_argument("-b", "--bottle")
    s.set_defaults(func=cmd_remove)

    s = sub.add_parser("launch", help="start a game/program from the library by name")
    s.add_argument("name")
    s.add_argument("-b", "--bottle")
    s.set_defaults(func=cmd_launch)

    for name, text in (("winecfg", "open Wine settings for a bottle"),
                       ("regedit", "open the registry editor"),
                       ("taskmgr", "open the task manager"),
                       ("control", "open the control panel"),
                       ("explorer", "open a Windows file explorer"),
                       ("cmd", "open a Windows command prompt"),
                       ("kill", "force-quit everything running in a bottle"),
                       ("drive", "print (or --open) the bottle's C: drive folder"),
                       ("winetricks", "install Windows components (e.g. vcrun2019 dotnet48 corefonts)")):
        s = sub.add_parser(name, help=text)
        s.add_argument("-b", "--bottle")
        if name == "winetricks":
            s.add_argument("verbs", nargs="*")
        if name == "drive":
            s.add_argument("--open", action="store_true")
        s.set_defaults(func=cmd_tool)

    s = sub.add_parser("shortcut", help="add Beer to Applications (macOS) or the app menu (Linux/FreeBSD)")
    s.set_defaults(func=cmd_shortcut)

    s = sub.add_parser("version", help="show the version")
    s.set_defaults(func=cmd_version)
    return p


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    # 'beer Game.exe' (e.g. from "Open with") behaves like 'beer gui Game.exe'.
    if argv and not argv[0].startswith("-") and argv[0] not in parser._subparsers._group_actions[0].choices:
        argv = ["gui"] + argv
    if not argv:
        if system.has_display():
            argv = ["gui"]
        else:
            parser.print_help()
            return 0
    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except (bottles.BottleError, wine.WineNotFound, FileNotFoundError, RuntimeError, ValueError) as exc:
        print("beer: %s" % exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
