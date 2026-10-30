#!/usr/bin/env bash
# Install every Vesktop patch in this repo, plus the pacman hooks that re-apply them after Vesktop updates.
#   ./install-all.sh              install / update everything (asks for sudo)
#   ./install-all.sh --uninstall  remove the hooks and installed scripts (then reinstall Vesktop for a clean app)
# Overrides: VESKTOP_ASAR=/path/to/app.asar, VESKTOP_PKG=<pacman package>.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="${VESKTOP_PATCH_LIB:-/usr/local/lib/vesktop-patches}"
HOOKS="${VESKTOP_HOOK_DIR:-/etc/pacman.d/hooks}"
PATCHERS=(patch-venmic.py patch-stream-preview.py patch-stream-bitrate.py patch-stream-quality.py patch-stream-start.py patch-no-hevc.py)

if [[ $EUID -ne 0 && -z "${VESKTOP_PATCH_LIB:-}" ]]; then
    exec sudo --preserve-env=VESKTOP_ASAR,VESKTOP_PKG "$0" "$@"
fi

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -fv "$HOOKS"/vesktop-venmic-fix.hook "$HOOKS"/vesktop-stream-*-fix.hook "$HOOKS"/vesktop-no-hevc-fix.hook
    rm -rf "$LIB" /usr/local/lib/vesktop-venmic-fix
    echo "Hooks and scripts removed. Reinstall Vesktop (e.g. paru -S vesktop-git) to get an unpatched app back."
    exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required"; exit 1; }

# Find the installed Vesktop: the pacman package that owns a resources/app.asar, or a known install path.
PKG="${VESKTOP_PKG:-}"
ASAR="${VESKTOP_ASAR:-}"
if [[ -z "$ASAR" ]] && command -v pacman >/dev/null; then
    for p in ${PKG:-vesktop-git vesktop vesktop-bin}; do
        a="$(pacman -Qlq "$p" 2>/dev/null | grep -m1 '/resources/app\.asar$' || true)"
        if [[ -n "$a" ]]; then PKG="$p"; ASAR="$a"; break; fi
    done
fi
if [[ -z "$ASAR" ]]; then
    for a in /usr/lib/vesktop/resources/app.asar /opt/Vesktop/resources/app.asar /opt/vesktop/resources/app.asar; do
        [[ -f "$a" ]] && { ASAR="$a"; break; }
    done
fi
if [[ -z "$ASAR" || ! -f "$ASAR" ]]; then
    if command -v flatpak >/dev/null && flatpak info dev.vencord.Vesktop >/dev/null 2>&1; then
        echo "Only the Flatpak Vesktop was found: its files are read-only, these patches can't be applied to it."
    else
        echo "Vesktop app.asar not found. Run again with VESKTOP_ASAR=/path/to/resources/app.asar"
    fi
    exit 1
fi
echo "Vesktop: $ASAR${PKG:+ (package $PKG)}"

install -d "$LIB"
# Earlier versions installed to /usr/local/lib/vesktop-venmic-fix: keep its backups, drop the rest.
OLD=/usr/local/lib/vesktop-venmic-fix
if [[ -z "${VESKTOP_PATCH_LIB:-}" && -d "$OLD" ]]; then
    mv -n "$OLD"/app.asar.* "$LIB/" 2>/dev/null || true
    rm -rf "$OLD"
fi
install -m755 "${PATCHERS[@]/#/$HERE/}" "$HERE/status.py" "$LIB/"
install -m644 "$HERE/venmic/venmic-x64.node" "$LIB/"
backup="$LIB/app.asar.backup-$(date +%Y%m%d-%H%M%S)"
cp "$ASAR" "$backup" && echo "Backup: $backup"

if [[ -n "$PKG" ]]; then
    install -d "$HOOKS"
    for t in "$HERE"/hooks/*.hook.in; do
        sed -e "s|@PKG@|$PKG|" -e "s|@ASAR@|$ASAR|" -e "s|@LIB@|$LIB|" "$t" > "$HOOKS/$(basename "$t" .in)"
        chmod 644 "$HOOKS/$(basename "$t" .in)"
    done
    echo "pacman hooks installed in $HOOKS (re-applied after every $PKG update)"
else
    echo "No pacman package found: no hooks installed. Run this script again after every Vesktop update."
fi

echo
for p in "${PATCHERS[@]}"; do
    VESKTOP_ASAR="$ASAR" python3 "$LIB/$p" || true
done
echo
VESKTOP_ASAR="$ASAR" VESKTOP_PKG="${PKG:-vesktop-git}" VESKTOP_PATCH_LIB="$LIB" VESKTOP_HOOK_DIR="$HOOKS" python3 "$LIB/status.py"
echo
echo "Restart Vesktop to load the patches."
