# Works with both GNU make (Linux, macOS) and BSD make (FreeBSD).
PREFIX ?= /usr/local
DESTDIR ?=
PYTHON ?= python3

LIBDIR = $(DESTDIR)$(PREFIX)/lib/beer
BINDIR = $(DESTDIR)$(PREFIX)/bin
SHAREDIR = $(DESTDIR)$(PREFIX)/share

all: test

test:
	$(PYTHON) -m unittest discover -s tests

install:
	rm -rf $(LIBDIR)
	mkdir -p $(LIBDIR) $(BINDIR) $(SHAREDIR)/applications $(SHAREDIR)/icons/hicolor/scalable/apps
	cp -R beer $(LIBDIR)/
	find $(LIBDIR) -name __pycache__ -type d -prune -exec rm -rf {} +
	printf '#!/bin/sh\nPYTHONPATH="%s$${PYTHONPATH:+:$$PYTHONPATH}" exec python3 -m beer "$$@"\n' \
		"$(PREFIX)/lib/beer" > $(BINDIR)/beer
	chmod 755 $(BINDIR)/beer
	cp beer/resources/beer.svg $(SHAREDIR)/icons/hicolor/scalable/apps/beer.svg
	$(PYTHON) -c 'import sys; sys.path.insert(0, "."); from beer.desktop import desktop_entry; print(desktop_entry(), end="")' \
		> $(SHAREDIR)/applications/beer.desktop

uninstall:
	rm -rf $(LIBDIR) $(BINDIR)/beer $(SHAREDIR)/applications/beer.desktop \
		$(SHAREDIR)/icons/hicolor/scalable/apps/beer.svg

dist:
	sh scripts/build-release.sh

.PHONY: all test install uninstall dist
