#!/bin/sh
# Apply every patcher installed next to this script to VESKTOP_ASAR. Used by install-all.sh and by the systemd unit that
# re-applies the patches after Vesktop updates. Each patcher skips what is already done, so re-running is harmless.
dir="$(cd "$(dirname "$0")" && pwd)"
for p in "$dir"/patch-*.py; do
    python3 "$p" || true
done
