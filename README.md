# 🍺 Beer

**Run Windows apps and games on macOS, Linux and FreeBSD.** Beer is a free replacement for the discontinued *Whisky* app. It's built for people who want to play Pokémon fan games (Pokémon Essentials / RPG Maker games such as Reborn, Rejuvenation, Insurgence and Uranium) without touching Windows.

Like Whisky, Beer uses [Wine](https://www.winehq.org), the open-source layer that translates Windows calls into macOS/Linux/FreeBSD calls as the program runs. Beer installs Wine for you, keeps each set of games in its own **bottle** (a separate pretend Windows install), and gives you a simple window with a **Play** button.

## Install

### macOS (Homebrew)
```bash
brew tap mayank141-web/whiskey-clone https://github.com/Mayank141-web/Whiskey-Clone
```
```bash
brew install beer
```
```bash
beer install-wine
```
```bash
beer shortcut
```
`install-wine` downloads Wine, plus Rosetta 2 on Apple Silicon Macs. `shortcut` adds **Beer.app** to `~/Applications` so you can open it from Launchpad or Spotlight.

### Linux (any distro) and FreeBSD (sudo)
```bash
curl -fsSL https://github.com/Mayank141-web/Whiskey-Clone/releases/latest/download/install.sh | sudo sh
```
This installs Python/Tk, Beer and Wine using your system's package manager. It supports apt, dnf/yum, pacman, zypper, apk, xbps, emerge, eopkg, urpmi, swupd, nix and FreeBSD `pkg`. On FreeBSD without curl, use `fetch -o - <url> | sudo sh`.

Prefer a package? Get one from the [Releases page](https://github.com/Mayank141-web/Whiskey-Clone/releases):

| Distro | Command |
|---|---|
| Debian, Ubuntu, Mint, Pop!_OS | `sudo apt install ./beer_1.0.0_all.deb` |
| Fedora, RHEL, Rocky | `sudo dnf install ./beer-1.0.0-1.noarch.rpm` |
| openSUSE | `sudo zypper install ./beer-1.0.0-1.noarch.rpm` |
| Arch, Manjaro, EndeavourOS | put `PKGBUILD` in an empty folder and run `makepkg -si` |
| From source (any OS) | `sudo make install` |

After installing a package, run `beer install-wine` once if Wine isn't already installed.

Uninstall with `sudo sh install.sh --uninstall`, `sudo apt remove beer` or `brew uninstall beer`. Your bottles are kept.

## Play a Pokémon fan game

1. Download the game (the `.zip`, `.rar` or `.7z` file, or an already unpacked folder).
2. Open **Beer**, click **Add Pokémon Game** and choose the download or the folder.
3. Beer unpacks the game, finds `Game.exe`, makes a `Pokemon` bottle set to Windows 10, installs the game's own fonts so text shows up properly, adds the game to your library and starts it.
4. Next time, pick the game and press **▶ Play**.

The same thing works from a terminal:
```bash
beer pokemon ~/Downloads/Pokemon_Reborn.zip
```
```bash
beer launch "Pokemon Reborn"
```

### If a game doesn't work
- **Missing or garbled text:** `beer winetricks corefonts`
- **Game needs DirectX 9 / Visual C++:** `beer winetricks d3dx9 vcrun2019`
- **Japanese game:** `beer bottle env Pokemon LANG=ja_JP.UTF-8`
- **Try another Windows version:** use the *Windows version* menu, or `beer bottle set-windows Pokemon win7`
- **Frozen game:** click **Force Quit**, or run `beer kill`
- **Logs:** each launch writes a log to the bottle's `logs` folder

## Everything Beer can do

| | Window | Terminal |
|---|---|---|
| Install Wine | **Install Wine** | `beer install-wine` |
| Check setup | | `beer doctor` |
| Run any `.exe` / `.msi` | **Run .exe…** or *Open With → Beer* | `beer run setup.exe` |
| Add a game to the library | **Add Program…** | `beer add Game.exe -n "My Game"` |
| Bottles | **New** / **Delete** | `beer bottle create/delete/info NAME` |
| Wine settings | **Wine Settings** | `beer winecfg` |
| Install Windows components | **Winetricks…** | `beer winetricks vcrun2019` |
| Browse the C: drive | **Open C: Drive** | `beer drive --open` |
| Registry, task manager, cmd | | `beer regedit` / `taskmgr` / `cmd` |
| DLL overrides | | `beer bottle dll NAME d3d9=native,builtin` |

Most commands take `-b BOTTLE` to pick a bottle.

**Where things live:** `~/Library/Application Support/Beer` on macOS, `~/.local/share/beer` on Linux/FreeBSD. Set `BEER_HOME` to use a different folder, or `BEER_WINE` to use a specific Wine binary.

## How Wine is installed

| OS | Source |
|---|---|
| macOS | The latest Wine build from [Gcenx/macOS_Wine_builds](https://github.com/Gcenx/macOS_Wine_builds), downloaded into Beer's folder. Beer also installs Rosetta 2 on Apple Silicon and clears the quarantine flag. If that fails, it falls back to Homebrew or MacPorts. |
| Linux | Your distro's `wine` package. On Debian/Ubuntu, Beer also enables 32-bit support, which most RPG Maker games need. |
| FreeBSD | `pkg install wine`, plus the 32-bit add-on (`pkg32.sh`) |

## Development

```bash
make test           # run the unit tests
make dist           # build dist/ (tar.gz, .deb, .rpm, PKGBUILD, formula, checksums)
python3 -m beer  # run from the source checkout
```

Pushing a commit with a new version number in `beer/__init__.py` (or a `v*` tag) runs `.github/workflows/release.yml`, which tests the code, builds every package and publishes a GitHub release.

Beer is written in plain Python 3.8+ with Tkinter and has no other dependencies. Licensed under MIT. Beer is not affiliated with Whisky, CodeWeavers, WineHQ, Nintendo or The Pokémon Company.
