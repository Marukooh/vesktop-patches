#!/bin/sh
# Run with sudo. Installs the Go Live resolution + bitrate patches and their pacman hooks, then patches the current Vesktop.
set -e
cd "$(dirname "$0")"
install -Dm755 patch-stream-quality.py          /usr/local/lib/vesktop-venmic-fix/patch-stream-quality.py
install -Dm755 patch-stream-bitrate.py          /usr/local/lib/vesktop-venmic-fix/patch-stream-bitrate.py
install -Dm644 vesktop-stream-quality-fix.hook  /etc/pacman.d/hooks/vesktop-stream-quality-fix.hook
install -Dm644 vesktop-stream-bitrate-fix.hook  /etc/pacman.d/hooks/vesktop-stream-bitrate-fix.hook
cp -n /usr/lib/vesktop/resources/app.asar /usr/local/lib/vesktop-venmic-fix/app.asar.pre-quality-fix
/usr/bin/python3 /usr/local/lib/vesktop-venmic-fix/patch-stream-quality.py || true
/usr/bin/python3 /usr/local/lib/vesktop-venmic-fix/patch-stream-bitrate.py || true
