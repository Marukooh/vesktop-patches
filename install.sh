#!/bin/sh
# Run with sudo. Copies the fix to a root-owned location, installs the pacman hook and patches the current Vesktop.
set -e
cd "$(dirname "$0")"
install -Dm644 venmic-x64.node /usr/local/lib/vesktop-venmic-fix/venmic-x64.node
install -Dm755 patch-asar.py   /usr/local/lib/vesktop-venmic-fix/patch-asar.py
install -Dm644 vesktop-venmic-fix.hook /etc/pacman.d/hooks/vesktop-venmic-fix.hook
cp -n /usr/lib/vesktop/resources/app.asar /usr/local/lib/vesktop-venmic-fix/app.asar.orig || true
/usr/bin/python3 /usr/local/lib/vesktop-venmic-fix/patch-asar.py
