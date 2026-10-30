#!/usr/bin/env bash
# Install every Vesktop patch in this repo, plus what re-applies them after Vesktop updates: one pacman hook per patch
# on Arch-based distros, a systemd path unit that watches app.asar everywhere else.
#   ./install-all.sh              install / update everything (asks for root via sudo, doas or pkexec)
#   ./install-all.sh --uninstall  remove the hooks, units and installed scripts (then reinstall Vesktop for a clean app)
# Overrides: VESKTOP_ASAR=/path/to/app.asar, VESKTOP_PKG=<package>, VESKTOP_REAPPLY=pacman|systemd|none.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SELF="$HERE/$(basename "$0")"
LIB="${VESKTOP_PATCH_LIB:-/usr/local/lib/vesktop-patches}"
HOOKS="${VESKTOP_HOOK_DIR:-/etc/pacman.d/hooks}"
UNITS="${VESKTOP_UNIT_DIR:-/etc/systemd/system}"
UNIT=vesktop-patches

if [[ $EUID -ne 0 && -z "${VESKTOP_PATCH_LIB:-}" ]]; then
    keep=()
    for v in VESKTOP_ASAR VESKTOP_PKG VESKTOP_REAPPLY; do
        [[ -n "${!v:-}" ]] && keep+=("$v=${!v}")
    done
    # The invoking user's home, to look for Vesktop installs there too.
    keep+=("VESKTOP_USER_HOME=$HOME")
    for elev in sudo doas pkexec; do
        command -v "$elev" >/dev/null && exec "$elev" env "${keep[@]}" "$SELF" "$@"
    done
    echo "Run this script as root (none of sudo, doas or pkexec was found)."
    exit 1
fi

# systemctl only on the real system, not when the paths are overridden for testing.
run_systemctl() { [[ -z "${VESKTOP_UNIT_DIR:-}" ]] && systemctl "$@" || true; }

remove_hooks() { rm -fv "$HOOKS"/vesktop-venmic-fix.hook "$HOOKS"/vesktop-stream-*-fix.hook "$HOOKS"/vesktop-no-hevc-fix.hook; }
remove_units() {
    if [[ -f "$UNITS/$UNIT.path" ]]; then
        run_systemctl disable --now "$UNIT.path"
        rm -fv "$UNITS/$UNIT.path" "$UNITS/$UNIT.service"
        run_systemctl daemon-reload
    fi
}

if [[ "${1:-}" == "--uninstall" ]]; then
    remove_hooks
    remove_units
    rm -rf "$LIB" /usr/local/lib/vesktop-venmic-fix
    echo "Hooks, units and scripts removed. Reinstall Vesktop with your package manager to get an unpatched app back."
    exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required: install it with your package manager"; exit 1; }

# The package that owns a file, if any (pacman, dpkg or rpm).
owner_of() {
    local out
    if command -v pacman >/dev/null && out="$(pacman -Qoq "$1" 2>/dev/null)"; then echo "$out"; return; fi
    if command -v dpkg >/dev/null && out="$(dpkg -S "$1" 2>/dev/null)"; then echo "${out%%:*}"; return; fi
    if command -v rpm >/dev/null && out="$(rpm -qf --qf '%{NAME}\n' "$1" 2>/dev/null)"; then echo "$out"; return; fi
    return 1
}

# Every place Vesktop's app.asar may be, most reliable first.
candidates() {
    local p r x home="${VESKTOP_USER_HOME:-$HOME}"
    for p in ${VESKTOP_PKG:-vesktop-git vesktop vesktop-bin}; do
        command -v pacman >/dev/null && pacman -Qlq "$p" 2>/dev/null | grep '/resources/app\.asar$' || true
        command -v dpkg   >/dev/null && dpkg -L "$p" 2>/dev/null | grep '/resources/app\.asar$' || true
        command -v rpm    >/dev/null && rpm -ql "$p" 2>/dev/null | grep '/resources/app\.asar$' || true
    done
    # The vesktop command: a symlink to the Electron binary, or a launcher script that names the install dir.
    for p in vesktop Vesktop; do
        x="$(command -v "$p" 2>/dev/null)" || continue
        r="$(readlink -f "$x")"
        echo "$(dirname "$r")/resources/app.asar"
        if [[ -f "$r" && $(stat -c %s "$r") -lt 65536 ]] && grep -Iq . "$r" 2>/dev/null; then
            grep -oE '/[^ "'"'"':;]+' "$r" | while read -r x; do
                [[ "$x" == *app.asar ]] && echo "$x"
                echo "$x/resources/app.asar"
                echo "$(dirname "$x")/resources/app.asar"
            done
        fi
    done
    printf '%s\n' /usr/lib/vesktop/resources/app.asar /usr/lib64/vesktop/resources/app.asar \
        /opt/Vesktop/resources/app.asar /opt/vesktop/resources/app.asar /usr/share/vesktop/resources/app.asar
    # Tarball installs in the user's home.
    for x in "$home"/{Applications,.local/share,.local/opt,.local/lib,opt,}/[Vv]esktop*/resources/app.asar; do
        echo "$x"
    done
}

ASAR="${VESKTOP_ASAR:-}"
if [[ -z "$ASAR" ]]; then
    while read -r x; do
        if [[ -f "$x" ]]; then ASAR="$(readlink -f "$x")"; break; fi
    done < <(candidates)
fi
if [[ -z "$ASAR" || ! -f "$ASAR" ]]; then
    home="${VESKTOP_USER_HOME:-$HOME}"
    if command -v flatpak >/dev/null && flatpak info dev.vencord.Vesktop >/dev/null 2>&1; then
        echo "Only the Flatpak Vesktop was found: its files are read-only, so these patches can't be applied to it."
    elif command -v snap >/dev/null && snap list vesktop >/dev/null 2>&1; then
        echo "Only the Snap Vesktop was found: its files are read-only, so these patches can't be applied to it."
    elif compgen -G "$home/*/[Vv]esktop*.AppImage" >/dev/null || compgen -G "$home/[Vv]esktop*.AppImage" >/dev/null; then
        echo "Only a Vesktop AppImage was found: AppImages are read-only, so these patches can't be applied to it."
    else
        echo "Vesktop's app.asar was not found."
    fi
    echo "Install Vesktop's .deb, .rpm or .tar.gz (https://github.com/Vencord/Vesktop/releases) or your distro's package,"
    echo "or run again with VESKTOP_ASAR=/path/to/resources/app.asar"
    exit 1
fi
if [[ ! -w "$(dirname "$ASAR")" ]]; then
    echo "$ASAR is on a read-only filesystem (Nix store, image-based distro...): these patches can't be applied to it."
    exit 1
fi

PKG="${VESKTOP_PKG:-$(owner_of "$ASAR" || true)}"
echo "Vesktop: $ASAR${PKG:+ (package $PKG)}"

# pacman hooks where pacman owns Vesktop, otherwise a systemd unit that notices any change to app.asar (apt, dnf, zypper,
# a new tarball unpacked over the old one...).
MODE="${VESKTOP_REAPPLY:-}"
if [[ -z "$MODE" ]]; then
    if [[ -n "$PKG" ]] && command -v pacman >/dev/null && pacman -Qq "$PKG" >/dev/null 2>&1; then MODE=pacman
    elif [[ -d /run/systemd/system ]]; then MODE=systemd
    else MODE=none
    fi
fi

install -d "$LIB"
# Earlier versions installed to /usr/local/lib/vesktop-venmic-fix: keep its backups, drop the rest.
OLD=/usr/local/lib/vesktop-venmic-fix
if [[ -z "${VESKTOP_PATCH_LIB:-}" && -d "$OLD" ]]; then
    mv -n "$OLD"/app.asar.* "$LIB/" 2>/dev/null || true
    rm -rf "$OLD"
fi
rm -f "$LIB"/patch-*.py
install -m755 "$HERE"/patch-*.py "$HERE/apply-all.sh" "$HERE/status.py" "$LIB/"
install -m644 "$HERE"/venmic/venmic-*.node "$LIB/"
backup="$LIB/app.asar.backup-$(date +%Y%m%d-%H%M%S)"
cp "$ASAR" "$backup" && echo "Backup: $backup"

fill() { sed -e "s|@PKG@|$PKG|" -e "s|@ASAR@|$ASAR|" -e "s|@LIB@|$LIB|" "$1" > "$2" && chmod 644 "$2"; }
case "$MODE" in
    pacman)
        remove_units
        install -d "$HOOKS"
        for t in "$HERE"/hooks/*.hook.in; do fill "$t" "$HOOKS/$(basename "$t" .in)"; done
        echo "pacman hooks installed in $HOOKS (re-applied after every $PKG update)"
        ;;
    systemd)
        remove_hooks >/dev/null
        install -d "$UNITS"
        for t in "$HERE"/systemd/*.in; do fill "$t" "$UNITS/$(basename "$t" .in)"; done
        run_systemctl daemon-reload
        run_systemctl enable --now "$UNIT.path"
        echo "systemd unit $UNIT.path installed (re-applies the patches whenever $ASAR changes)"
        ;;
    *)
        echo "Neither pacman nor systemd found: run this script again after every Vesktop update."
        ;;
esac

echo
VESKTOP_ASAR="$ASAR" "$LIB/apply-all.sh"
echo
VESKTOP_ASAR="$ASAR" VESKTOP_PATCH_LIB="$LIB" VESKTOP_HOOK_DIR="$HOOKS" VESKTOP_UNIT_DIR="$UNITS" python3 "$LIB/status.py"
echo
echo "Restart Vesktop to load the patches."
