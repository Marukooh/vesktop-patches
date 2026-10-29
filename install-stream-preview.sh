#!/bin/sh
# Run with sudo. Installs the stream-thumbnail mute patch + its pacman hook and patches the current Vesktop.
set -e
cd "$(dirname "$0")"
install -Dm755 patch-stream-preview.py          /usr/local/lib/vesktop-venmic-fix/patch-stream-preview.py
install -Dm644 vesktop-stream-preview-fix.hook  /etc/pacman.d/hooks/vesktop-stream-preview-fix.hook
cp -n /usr/lib/vesktop/resources/app.asar /usr/local/lib/vesktop-venmic-fix/app.asar.pre-preview-fix
/usr/bin/python3 /usr/local/lib/vesktop-venmic-fix/patch-stream-preview.py
