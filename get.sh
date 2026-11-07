#!/bin/sh
# One-line install, update or uninstall of vesktop-patches without cloning the repo:
#   curl -fsSL https://raw.githubusercontent.com/Marukooh/vesktop-patches/main/get.sh | sh
#   curl -fsSL https://raw.githubusercontent.com/Marukooh/vesktop-patches/main/get.sh | sh -s -- --uninstall
# Downloads the repo to a temporary folder, runs install-all.sh with the given arguments, then deletes the folder.
set -eu

# Wrapped in a function so a download cut off halfway runs nothing.
main() {
    for c in curl tar python3; do
        command -v "$c" >/dev/null || { echo "$c is required"; exit 1; }
    done
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    curl -fsSL "${VESKTOP_PATCHES_TARBALL:-https://github.com/Marukooh/vesktop-patches/archive/refs/heads/main.tar.gz}" \
        | tar -xz -C "$tmp" --strip-components=1
    bash "$tmp/install-all.sh" "$@"
}

main "$@"
