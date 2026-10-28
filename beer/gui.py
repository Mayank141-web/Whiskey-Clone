"""The Beer window (Tkinter, so it works on macOS, Linux and FreeBSD without extra installs)."""

import os
import queue
import sys
import threading
import traceback

from . import APP_NAME, __version__, bottles, desktop, games, system, wine

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:  # pragma: no cover - depends on the host
    tk = None

PROGRAM_TYPES = [("Windows programs", "*.exe *.msi *.bat *.lnk"), ("All files", "*")]
GAME_TYPES = [("Games / archives", "*.exe *.zip *.rar *.7z *.tar.gz *.tgz *.tar.xz"), ("All files", "*")]


class App(object):
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.busy = 0
        root.title(APP_NAME)
        root.geometry("900x600")
        root.minsize(720, 480)
        self._build()
        self.refresh()
        self.refresh_wine()
        root.after(100, self._pump)
        root.after(800, self.offer_install)
        if system.is_macos():
            root.createcommand("::tk::mac::OpenDocument", lambda *paths: self.open_files(paths))

    # ----------------------------------------------------------------- layout
    def _build(self):
        style = ttk.Style()
        if "clam" in style.theme_names() and not system.is_macos():
            style.theme_use("clam")
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="x")
        ttk.Label(top, text=APP_NAME, font=("TkDefaultFont", 18, "bold")).pack(side="left")
        self.wine_label = ttk.Label(top, text="Checking Wine...")
        self.wine_label.pack(side="left", padx=12)
        self.install_btn = ttk.Button(top, text="Install Wine", command=self.install_wine)
        self.install_btn.pack(side="right")

        body = ttk.PanedWindow(outer, orient="horizontal")
        body.pack(fill="both", expand=True, pady=(10, 6))

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        ttk.Label(left, text="Bottles").pack(anchor="w")
        self.bottle_list = tk.Listbox(left, exportselection=False, height=10, activestyle="none")
        self.bottle_list.pack(fill="both", expand=True)
        self.bottle_list.bind("<<ListboxSelect>>", lambda e: self.show_programs())
        row = ttk.Frame(left)
        row.pack(fill="x", pady=4)
        ttk.Button(row, text="New", command=self.new_bottle).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Delete", command=self.delete_bottle).pack(side="left", expand=True, fill="x")
        body.add(left, weight=1)

        right = ttk.Frame(body)
        ttk.Label(right, text="Games & Programs").pack(anchor="w")
        self.programs = ttk.Treeview(right, columns=("path",), show="tree headings", height=10)
        self.programs.heading("#0", text="Name")
        self.programs.heading("path", text="Location")
        self.programs.column("#0", width=200)
        self.programs.pack(fill="both", expand=True)
        self.programs.bind("<Double-1>", lambda e: self.play())
        row = ttk.Frame(right)
        row.pack(fill="x", pady=4)
        ttk.Button(row, text="▶ Play", command=self.play).pack(side="left")
        poke = ttk.Menubutton(row, text="Add Pokémon Game")
        menu = tk.Menu(poke, tearoff=False)
        menu.add_command(label="From a folder...", command=lambda: self.add_pokemon(folder=True))
        menu.add_command(label="From a .zip / .rar / .7z or Game.exe...", command=lambda: self.add_pokemon(folder=False))
        poke["menu"] = menu
        poke.pack(side="left", padx=4)
        ttk.Button(row, text="Add Program...", command=self.add_program).pack(side="left")
        ttk.Button(row, text="Run .exe...", command=self.run_exe).pack(side="left", padx=4)
        ttk.Button(row, text="Remove", command=self.remove_program).pack(side="left")
        body.add(right, weight=3)

        tools = ttk.Frame(outer)
        tools.pack(fill="x")
        ttk.Label(tools, text="Windows version:").pack(side="left")
        self.winver = tk.StringVar()
        box = ttk.Combobox(tools, textvariable=self.winver, values=bottles.WINDOWS_VERSIONS,
                           state="readonly", width=8)
        box.pack(side="left", padx=(4, 10))
        box.bind("<<ComboboxSelected>>", lambda e: self.set_windows_version())
        for text, cmd in (("Wine Settings", lambda: self.bottle_tool("winecfg")),
                          ("Winetricks...", self.winetricks),
                          ("Open C: Drive", self.open_drive),
                          ("Force Quit", self.kill)):
            ttk.Button(tools, text=text, command=cmd).pack(side="left", padx=2)

        self.log_box = tk.Text(outer, height=8, state="disabled", wrap="word")
        self.log_box.pack(fill="x", pady=(8, 0))
        self.log("%s %s on %s" % (APP_NAME, __version__, system.describe()))

    # ----------------------------------------------------------------- helpers
    def log(self, msg):
        self.events.put(("log", msg))

    def _write_log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _pump(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._write_log(payload)
                elif kind == "call":
                    payload()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def background(self, fn, done=None):
        """Run slow work (installing, unpacking, wineboot) without freezing the window."""
        def worker():
            try:
                fn()
            except Exception as exc:
                self.log("Error: %s" % exc)
                if not isinstance(exc, (bottles.BottleError, wine.WineNotFound, RuntimeError)):
                    self.log(traceback.format_exc())
                self.events.put(("call", lambda: messagebox.showerror(APP_NAME, str(exc))))
            finally:
                self.events.put(("call", self.refresh))
                if done:
                    self.events.put(("call", done))
        threading.Thread(target=worker, daemon=True).start()

    def selected_bottle(self, create=True):
        name = self.selected_name()
        if name:
            return bottles.get_bottle(name)
        if create:
            return bottles.get_or_create_bottle(bottles.default_bottle_name(), log=self.log)
        return None

    def selected_name(self):
        """Must be called on the UI thread; worker threads get the name passed in."""
        sel = self.bottle_list.curselection()
        return self.bottle_list.get(sel[0]) if sel else None

    def bottle_by_name(self, name):
        """Safe to call from worker threads."""
        return bottles.get_or_create_bottle(name or bottles.default_bottle_name(), log=self.log)

    def require_wine(self):
        if wine.find_wine():
            return True
        if messagebox.askyesno(APP_NAME, "Wine isn't installed yet. Install it now?"):
            self.install_wine()
        return False

    # ----------------------------------------------------------------- refresh
    def refresh(self):
        current = None
        sel = self.bottle_list.curselection()
        if sel:
            current = self.bottle_list.get(sel[0])
        self.bottle_list.delete(0, "end")
        names = [b.name for b in bottles.list_bottles()]
        for name in names:
            self.bottle_list.insert("end", name)
        if names:
            idx = names.index(current) if current in names else 0
            self.bottle_list.selection_set(idx)
        self.show_programs()

    def refresh_wine(self):
        def check():
            exe = wine.find_wine()
            text = wine.wine_version(exe) if exe else None
            def update():
                if exe:
                    self.wine_label.configure(text="Wine: %s" % (text or "installed"))
                    self.install_btn.configure(text="Reinstall Wine" if system.is_macos() else "Wine OK",
                                               state="normal" if system.is_macos() else "disabled")
                else:
                    self.wine_label.configure(text="Wine is not installed")
                    self.install_btn.configure(text="Install Wine", state="normal")
            self.events.put(("call", update))
        threading.Thread(target=check, daemon=True).start()

    def show_programs(self):
        self.programs.delete(*self.programs.get_children())
        bottle = self.selected_bottle(create=False)
        if not bottle:
            self.winver.set("")
            return
        self.winver.set(bottle.config["windows_version"])
        for p in bottle.programs:
            self.programs.insert("", "end", text=p["name"], values=(p["path"],))

    # ----------------------------------------------------------------- first run
    def offer_install(self):
        suggestion = desktop.install_suggestion()
        if suggestion == "appimage":
            if messagebox.askyesno(APP_NAME, "Add Beer to your app menu?\n\n"
                                   "Beer will be copied to ~/Applications so you can delete the download."):
                try:
                    desktop.install_appimage()
                    self.log("Beer was added to your app menu.")
                except OSError as exc:
                    messagebox.showerror(APP_NAME, "Could not add Beer to the app menu: %s" % exc)
            else:
                # Don't ask again: an empty marker file is enough.
                try:
                    path = desktop.desktop_entry_path()
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    if not os.path.exists(path):
                        with open(path, "w") as fh:
                            fh.write("[Desktop Entry]\nType=Application\nName=Beer\nNoDisplay=true\nHidden=true\n")
                except OSError:
                    pass
        elif suggestion == "mac-move":
            messagebox.showinfo(APP_NAME, "Tip: drag Beer into your Applications folder so it's "
                                "always there in Launchpad. You can then eject the Beer disk image.")
        if not wine.find_wine():
            if messagebox.askyesno(APP_NAME, "Beer needs Wine to run Windows programs. Install it now?\n\n"
                                   "(You may be asked for your password.)"):
                self.install_wine()

    # ----------------------------------------------------------------- actions
    def install_wine(self):
        self.install_btn.configure(state="disabled")
        self.log("Installing Wine. This can take a few minutes; you may be asked for your password.")
        self.background(lambda: wine.install_wine(log=self.log), done=self.refresh_wine)

    def new_bottle(self):
        name = simpledialog.askstring(APP_NAME, "Name for the new bottle:", parent=self.root)
        if not name or not self.require_wine():
            return
        self.background(lambda: bottles.create_bottle(name, log=self.log)
                        and self.log("Bottle '%s' is ready." % name))

    def delete_bottle(self):
        bottle = self.selected_bottle(create=False)
        if bottle and messagebox.askyesno(
                APP_NAME, "Delete bottle '%s' and everything installed in it?" % bottle.name):
            bottles.delete_bottle(bottle.name)
            self.refresh()

    def add_pokemon(self, folder):
        if folder:
            path = filedialog.askdirectory(title="Choose the Pokémon game folder")
        else:
            path = filedialog.askopenfilename(title="Choose the downloaded game", filetypes=GAME_TYPES)
        if not path or not self.require_wine():
            return
        self.background(lambda: games.setup_pokemon_game(path, log=self.log))

    def add_program(self):
        path = filedialog.askopenfilename(title="Choose a program or game", filetypes=GAME_TYPES)
        if not path or not self.require_wine():
            return
        name = self.selected_name()
        def work():
            exe = games.resolve_game(path, log=self.log)
            bottle = self.bottle_by_name(name)
            self.log("Added '%s' to bottle '%s'." % (bottle.add_program(exe), bottle.name))
        self.background(work)

    def run_exe(self):
        path = filedialog.askopenfilename(title="Run a Windows program", filetypes=PROGRAM_TYPES)
        if path:
            self.open_files([path])

    def open_files(self, paths):
        if not self.require_wine():
            return
        name = self.selected_name()
        def work():
            bottle = self.bottle_by_name(name)
            for path in paths:
                self.log("Starting %s in bottle '%s'..." % (os.path.basename(path), bottle.name))
                bottle.run(games.resolve_game(path, log=self.log))
        self.background(work)

    def play(self):
        sel = self.programs.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "Pick a game or program first, or add one.")
            return
        if not self.require_wine():
            return
        name = self.programs.item(sel[0], "text")
        bottle_name = self.selected_name()
        self.log("Starting %s..." % name)
        self.background(lambda: self.bottle_by_name(bottle_name).launch_program(name))

    def remove_program(self):
        sel = self.programs.selection()
        bottle = self.selected_bottle(create=False)
        if sel and bottle:
            bottle.remove_program(self.programs.item(sel[0], "text"))
            self.show_programs()

    def set_windows_version(self):
        bottle = self.selected_bottle(create=False)
        version = self.winver.get()
        if bottle and version:
            self.background(lambda: bottle.set_windows_version(version)
                            or self.log("'%s' now reports %s." % (bottle.name, version)))

    def bottle_tool(self, tool):
        if self.require_wine():
            name = self.selected_name()
            self.background(lambda: self.bottle_by_name(name).tool(tool))

    def winetricks(self):
        if not self.require_wine():
            return
        verbs = simpledialog.askstring(
            APP_NAME, "Components to install (space separated),\ne.g. corefonts vcrun2019 d3dx9 dotnet48:",
            parent=self.root)
        if verbs:
            name = self.selected_name()
            self.log("Running winetricks %s (this can take a while)..." % verbs)
            self.background(lambda: self.log("winetricks finished with code %s"
                                             % self.bottle_by_name(name).winetricks(verbs.split(), log=self.log)))

    def open_drive(self):
        bottle = self.selected_bottle(create=False)
        if bottle:
            os.makedirs(bottle.c_drive, exist_ok=True)
            system.open_path(bottle.c_drive)

    def kill(self):
        bottle = self.selected_bottle(create=False)
        if bottle:
            self.background(lambda: bottle.kill() or self.log("Stopped everything in '%s'." % bottle.name))


def main(files=None):
    if tk is None:
        print("The Beer window needs Tkinter. Install it (Debian/Ubuntu: sudo apt install python3-tk, "
              "Fedora: sudo dnf install python3-tkinter, Arch: sudo pacman -S tk, FreeBSD: sudo pkg install "
              "py311-tkinter, macOS: brew install python-tk), or use the commands shown by 'beer --help'.",
              file=sys.stderr)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print("Could not open a window (%s). Use 'beer --help' for terminal commands." % exc, file=sys.stderr)
        return 1
    app = App(root)
    if files:
        root.after(500, lambda: app.open_files([os.path.abspath(f) for f in files]))
    root.mainloop()
    return 0
