Beer runs Windows apps and games, including Pokémon fan games, on **macOS, Linux and FreeBSD**. It works like the discontinued Whisky app. [Wine](https://www.winehq.org) does the actual work of running Windows programs, and Beer sets Wine up and manages it for you.

## Install

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

## Play a Pokémon fan game
Open Beer, click **Add Pokémon Game** and pick the game's folder or the `.zip`, `.rar` or `.7z` file you downloaded. You can also use the terminal:
```bash
beer pokemon ~/Downloads/YourGame.zip
```

## Files
| File | What it is |
|---|---|
| `install.sh` | Installer for any Linux distro, FreeBSD and macOS (run it with `sudo sh`) |
| `beer_*_all.deb` | Debian/Ubuntu package |
| `beer-*.noarch.rpm` | Fedora/RHEL/openSUSE package |
| `PKGBUILD` | Arch Linux build recipe |
| `beer.rb` | Homebrew formula |
| `beer.tar.gz` | Source code |
| `SHA256SUMS` | Checksums |
