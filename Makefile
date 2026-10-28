# Works with both GNU make (Linux, macOS) and BSD make (FreeBSD).
PREFIX ?= /usr/local
DESTDIR ?=
PYTHON ?= python3

LIBDIR = $(DESTDIR)$(PREFIX)/lib/whiskey
BINDIR = $(DESTDIR)$(PREFIX)/bin
SHAREDIR = $(DESTDIR)$(PREFIX)/share

all: test

test:
	$(PYTHON) -m unittest discover -s tests

install:
	rm -rf $(LIBDIR)
	mkdir -p $(LIBDIR) $(BINDIR) $(SHAREDIR)/applications $(SHAREDIR)/icons/hicolor/scalable/apps
	cp -R whiskey $(LIBDIR)/
	find $(LIBDIR) -name __pycache__ -type d -prune -exec rm -rf {} +
	printf '#!/bin/sh\nPYTHONPATH="%s$${PYTHONPATH:+:$$PYTHONPATH}" exec python3 -m whiskey "$$@"\n' \
		"$(PREFIX)/lib/whiskey" > $(BINDIR)/whiskey
	chmod 755 $(BINDIR)/whiskey
	cp whiskey/resources/whiskey.svg $(SHAREDIR)/icons/hicolor/scalable/apps/whiskey.svg
	$(PYTHON) -c 'import sys; sys.path.insert(0, "."); from whiskey.desktop import desktop_entry; print(desktop_entry(), end="")' \
		> $(SHAREDIR)/applications/whiskey.desktop

uninstall:
	rm -rf $(LIBDIR) $(BINDIR)/whiskey $(SHAREDIR)/applications/whiskey.desktop \
		$(SHAREDIR)/icons/hicolor/scalable/apps/whiskey.svg

dist:
	sh scripts/build-release.sh

.PHONY: all test install uninstall dist
