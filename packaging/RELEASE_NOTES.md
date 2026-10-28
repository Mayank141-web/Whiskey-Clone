Beer runs Windows apps and games, including Pokémon fan games, on **macOS, Linux and FreeBSD**. It works like the discontinued Whisky app. [Wine](https://www.winehq.org) does the actual work of running Windows programs, and Beer sets Wine up and manages it for you.

## Install by downloading a file (no terminal needed)

| Your computer | Download | Then |
|---|---|---|
| **Mac** (Apple Silicon M1–M4, or Intel) | `Beer-macOS.dmg` | Open it and drag **Beer** into **Applications**. The first time, macOS may say it can't verify Beer: go to **System Settings → Privacy & Security** and click **Open Anyway**. |
| **Linux PC** (Intel/AMD, any distro) | `Beer-x86_64.AppImage` | Right-click it → **Properties → Permissions** → tick **Allow executing as program**, then double-click it. Beer offers to add itself to your app menu. |
| **Linux ARM** (Raspberry Pi 4/5, ARM laptops, any distro) | `Beer-aarch64.AppImage` | Same as above. |
| **Debian / Ubuntu / Mint** (any CPU) | `beer_*_all.deb` | Double-click it to open in your Software app, then click **Install**. |
| **Fedora / openSUSE** (any CPU) | `beer-*.noarch.rpm` | Double-click it to open in Software, then click **Install**. |
| **FreeBSD** (any CPU) | `beer-*.pkg` | Run `sudo pkg add beer-*.pkg` (FreeBSD has no double-click installer). |

When Beer first opens, it offers to install Wine. Click **Yes** and enter your password when asked.

## Install from the terminal

**macOS (Homebrew)**
```bash
brew tap mayank141-web/whiskey-clone https://github.com/Mayank141-web/Whiskey-Clone
brew install beer
beer install-wine
beer shortcut
```

**Linux (any distro) or FreeBSD, using sudo**
```bash
curl -fsSL https://github.com/Mayank141-web/Whiskey-Clone/releases/latest/download/install.sh | sudo sh
```

**Debian / Ubuntu / Mint:** download `beer_*_all.deb`, then run `sudo apt install ./beer_*_all.deb`
**Fedora / RHEL / openSUSE:** download the `.rpm`, then run `sudo dnf install ./beer-*.noarch.rpm` (or `sudo zypper install`)
**Arch / Manjaro:** download `PKGBUILD` into an empty folder, then run `makepkg -si`

## If the repository is private

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

## Play a Pokémon fan game
Open Beer, click **Add Pokémon Game** and pick the game's folder or the `.zip`, `.rar` or `.7z` file you downloaded. You can also use the terminal:
```bash
beer pokemon ~/Downloads/YourGame.zip
```

## Files
| File | What it is |
|---|---|
| `Beer-macOS.dmg` | Mac app (Apple Silicon and Intel), Python included |
| `Beer-x86_64.AppImage` / `Beer-aarch64.AppImage` | Linux app for any distro, Python included |
| `beer-*.pkg` | FreeBSD package |
| `install.sh` | Installer for any Linux distro, FreeBSD and macOS (run it with `sudo sh`) |
| `beer_*_all.deb` | Debian/Ubuntu package |
| `beer-*.noarch.rpm` | Fedora/RHEL/openSUSE package |
| `PKGBUILD` | Arch Linux build recipe |
| `beer.rb` | Homebrew formula |
| `beer.tar.gz` | Source code |
| `SHA256SUMS` | Checksums |
