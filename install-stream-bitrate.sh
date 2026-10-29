#!/bin/sh
# Run with sudo. Installs the Go Live bitrate patch + its pacman hook and patches the current Vesktop.
set -e
cd "$(dirname "$0")"
install -Dm755 patch-stream-bitrate.py          /usr/local/lib/vesktop-venmic-fix/patch-stream-bitrate.py
install -Dm644 vesktop-stream-bitrate-fix.hook  /etc/pacman.d/hooks/vesktop-stream-bitrate-fix.hook
cp -n /usr/lib/vesktop/resources/app.asar /usr/local/lib/vesktop-venmic-fix/app.asar.pre-bitrate-fix
/usr/bin/python3 /usr/local/lib/vesktop-venmic-fix/patch-stream-bitrate.py
