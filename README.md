# 🍺 Beer

**Run Windows apps and games on macOS, Linux and FreeBSD.** Beer is a free replacement for the discontinued *Whisky* app. It's built for people who want to play Pokémon fan games (Pokémon Essentials / RPG Maker games such as Reborn, Rejuvenation, Insurgence and Uranium) without touching Windows.

Like Whisky, Beer uses [Wine](https://www.winehq.org), the open-source layer that translates Windows calls into macOS/Linux/FreeBSD calls as the program runs. Beer installs Wine for you, keeps each set of games in its own **bottle** (a separate pretend Windows install), and gives you a simple window with a **Play** button.

## Install

### Easiest: download a file (no terminal)

Get the right file from the [Releases page](https://github.com/Mayank141-web/Whiskey-Clone/releases/latest):

| Your computer | Download | Then |
|---|---|---|
| **Mac**: Apple Silicon or Intel | `Beer-macOS.dmg` | Open it and drag **Beer** into **Applications**. If macOS says it can't verify Beer, go to **System Settings → Privacy & Security** and click **Open Anyway** (only needed once). |
| **Linux**: Intel/AMD PC, any distro | `Beer-x86_64.AppImage` | Right-click → **Properties → Permissions** → **Allow executing as program**, then double-click. Beer offers to add itself to your app menu. |
| **Linux**: ARM (Raspberry Pi 4/5, ARM laptops), any distro | `Beer-aarch64.AppImage` | Same as above. |
| **Debian / Ubuntu / Mint** | `beer_*_all.deb` | Double-click to open in your Software app, then click **Install**. |
| **Fedora / openSUSE** | `beer-*.noarch.rpm` | Double-click to open in Software, then click **Install**. |
| **FreeBSD** | `beer-*.pkg` | `sudo pkg add beer-*.pkg` |

The Mac app and the AppImages include their own Python, so nothing else is needed. The first time Beer opens, it offers to install Wine. Click **Yes** and enter your password in the pop-up.

**ARM computers:** on Apple Silicon Macs, Wine runs through Rosetta 2, which Beer installs. On ARM Linux with Debian/Ubuntu, Beer installs [Hangover](https://github.com/AndreRH/hangover) so that normal (x86) Windows games can run. On other ARM distros, you'll need Hangover, box64 or FEX-Emu yourself.

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

#### If the repository is private

Downloads from a private repo need you to be signed in to GitHub. Do this once with the [GitHub CLI](https://cli.github.com) (on macOS: `brew install gh`; on Linux: install the `gh` package).

```bash
gh auth login
```
```bash
gh auth setup-git
```

`setup-git` lets Homebrew and git use your GitHub sign-in, so the Homebrew commands above work unchanged.

**Linux / FreeBSD:**
```bash
gh release download -R Mayank141-web/Whiskey-Clone -p install.sh -p beer.tar.gz -D /tmp/beer --clobber
```
```bash
sudo sh /tmp/beer/install.sh
```

**Any download from the release (`.dmg`, `.AppImage`, `.deb` …):** you can click it on the Releases page while signed in to github.com in your browser, or run:
```bash
gh release download -R Mayank141-web/Whiskey-Clone -p 'Beer-macOS.dmg'
```

`install.sh` also accepts a token in `GITHUB_TOKEN`, and it automatically uses the GitHub CLI login of the person running `sudo`.

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
