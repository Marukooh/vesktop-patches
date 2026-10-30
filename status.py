#!/usr/bin/env python3
"""Show which local Vesktop patches are applied to the installed app.asar, and what re-applies them after updates."""
import filecmp, hashlib, json, os, platform, struct

ASAR    = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
HERE    = os.path.dirname(os.path.abspath(__file__))
SYSLIB  = os.environ.get("VESKTOP_PATCH_LIB", "/usr/local/lib/vesktop-patches")
HOOKS   = os.environ.get("VESKTOP_HOOK_DIR", "/etc/pacman.d/hooks")
UNITS   = os.environ.get("VESKTOP_UNIT_DIR", "/etc/systemd/system")
ARCH    = {"x86_64": "x64", "aarch64": "arm64"}.get(platform.machine(), "x64")

with open(ASAR, "rb") as f:
    raw = f.read()
_, header_size = struct.unpack_from("<II", raw, 0)
_, json_len    = struct.unpack_from("<Ii", raw, 8)
header         = json.loads(raw[16:16 + json_len])
data           = raw[8 + header_size:]

def entry(*path):
    node = header
    for part in path:
        node = node["files"][part]
    if node.get("unpacked"):
        return open(os.path.join(ASAR + ".unpacked", *path), "rb").read()
    return data[int(node["offset"]):int(node["offset"]) + node["size"]]

renderer = entry("dist", "js", "renderer.js")
venmic   = hashlib.sha256(entry("static", "dist", f"venmic-{ARCH}.node")).hexdigest()
fixpath  = next(p for p in (os.path.join(HERE, f"venmic-{ARCH}.node"), os.path.join(HERE, "venmic", f"venmic-{ARCH}.node")) if os.path.exists(p))
fixnode  = hashlib.sha256(open(fixpath, "rb").read()).hexdigest()

# name, script, pacman hook, applied?
PATCHES = [
    ("venmic crash fix",        "patch-venmic.py",          "vesktop-venmic-fix.hook",          venmic == fixnode),
    ("stream thumbnail mute",   "patch-stream-preview.py",  "vesktop-stream-preview-fix.hook",  b"vesktopPreviewMute" in renderer),
    ("Go Live bitrate",         "patch-stream-bitrate.py",  "vesktop-stream-bitrate-fix.hook",  b"bitrateMin:15e5,bitrateMax:12e6,bitrateTarget:5e6" in renderer),
    ("Go Live resolution",      "patch-stream-quality.py",  "vesktop-stream-quality-fix.hook",  b"vesktopGoliveFix" in renderer),
    ("Go Live start bitrate",   "patch-stream-start.py",    "vesktop-stream-start-fix.hook",    b"vesktopStartBitrate" in renderer),
    ("webcams with HW accel",   "patch-no-hevc.py",         "vesktop-no-hevc-fix.hook",         b"vesktopNoHevc" in renderer),
]

def same(a, b):
    return os.path.exists(a) and os.path.exists(b) and filecmp.cmp(a, b, shallow=False)

# One systemd path unit re-applies every patch; on Arch each patch has its own pacman hook instead.
unit = os.path.exists(os.path.join(UNITS, "vesktop-patches.path"))
print(f"Vesktop {json.loads(entry('package.json'))['version']} ({ASAR})\n")
print(f"{'patch':24} {'applied':8} {'re-apply':9} {'installed script'}")
for name, script, hook, applied in PATCHES:
    installed = os.path.join(SYSLIB, script)
    state = "up to date" if same(installed, os.path.join(HERE, script)) else ("OUTDATED" if os.path.exists(installed) else "missing")
    reapply = "pacman" if os.path.exists(os.path.join(HOOKS, hook)) else "systemd" if unit else "NO"
    print(f"{name:24} {'yes' if applied else 'NO':8} {reapply:9} {state}")
