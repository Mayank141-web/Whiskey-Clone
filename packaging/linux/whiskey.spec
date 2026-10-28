Name:           whiskey
Version:        @VERSION@
Release:        1
Summary:        Run Windows apps and games (like Pokemon fan games) with Wine
License:        MIT
URL:            https://github.com/Mayank141-web/Whiskey-Clone
Source0:        whiskey-%{version}.tar.gz
BuildArch:      noarch
Requires:       python3
Recommends:     python3-tkinter
Recommends:     wine
Recommends:     winetricks

%description
Whiskey is a simple app for running Windows programs on Linux, FreeBSD and
macOS. It manages bottles (separate Windows environments), installs Wine for
you, and has a one-click setup for Pokemon Essentials / RPG Maker fan games.

%prep
%setup -q

%build

%install
make install DESTDIR=%{buildroot} PREFIX=/usr

%files
/usr/bin/whiskey
/usr/lib/whiskey
/usr/share/applications/whiskey.desktop
/usr/share/icons/hicolor/scalable/apps/whiskey.svg
