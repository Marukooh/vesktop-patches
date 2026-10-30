#!/usr/bin/env python3
"""Swap Vesktop's bundled venmic 7.2.3 (loopback double-destroy crash) for the official venmic 7.2.5 prebuilds.

The 7.2.5 binaries are the unmodified x64/arm64 prebuilds from the @vencord/venmic npm package. They only need
glibc 2.30 and libpipewire, so they load on any current distro.
"""
import hashlib, json, os, struct, sys

ASAR    = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
HERE    = os.path.dirname(os.path.abspath(__file__))
ARCHES  = ("x64", "arm64")
BUGGY   = {"x64":   {"6c10a6d33ab59f2c3f13994e2572f653cf7c26961454b6300ed9add777e142ce",   # upstream venmic 7.2.3
                     "9d6f5da90bc63f53192275217e09c9b46ee66d7a574368e92f086234da44b262",   # earlier local fix (#45 only)
                     "96005f9f661f51615de8a5a5c2d59ef7c898cf4426af7115ef21b0018b192cda",   # earlier local fix (#45 + #46)
                     "f72dba66aba78729d04aa6916e042cd029237d17f2f4a054d69b89de633e616e",   # earlier local fix (PR #47 build)
                     "a59bab7baf7eb258747e0c3518e5f41054961c5d36859f60e4c6b2a5ff9e794a"},  # earlier local 7.2.4 build (needs GCC 15 libstdc++)
           "arm64": {"25950db4749fb28e54fdcde2b663d2ce9c0afabafb1804e0f1974d9eeb1558f0"}}  # upstream venmic 7.2.3
BLOCK   = 4 * 1024 * 1024

def integrity(data):
    blocks = [hashlib.sha256(data[i:i + BLOCK]).hexdigest() for i in range(0, max(len(data), 1), BLOCK)]
    return {"algorithm": "SHA256", "hash": hashlib.sha256(data).hexdigest(), "blockSize": BLOCK, "blocks": blocks}

def fix_file(arch):
    for p in (os.path.join(HERE, f"venmic-{arch}.node"), os.path.join(HERE, "venmic", f"venmic-{arch}.node")):
        if os.path.exists(p):
            return p

with open(ASAR, "rb") as f:
    raw = f.read()

_, header_size = struct.unpack_from("<II", raw, 0)
_, json_len    = struct.unpack_from("<Ii", raw, 8)
header         = json.loads(raw[16:16 + json_len])
data           = raw[8 + header_size:]
dist           = header["files"]["static"]["files"]["dist"]["files"]

appended, changed = b"", []
for arch in ARCHES:
    name = f"venmic-{arch}.node"
    node, path = dist.get(name), fix_file(arch)
    if node is None or path is None:
        continue
    fix      = open(path, "rb").read()
    # Release builds may keep native modules outside the archive, in app.asar.unpacked.
    unpacked = os.path.join(ASAR + ".unpacked", "static", "dist", name) if node.get("unpacked") else None
    current  = hashlib.sha256(open(unpacked, "rb").read() if unpacked else
                              data[int(node["offset"]):int(node["offset"]) + node["size"]]).hexdigest()
    if current == hashlib.sha256(fix).hexdigest():
        print(f"vesktop-venmic-fix: {name} already patched")
        continue
    if current not in BUGGY[arch]:
        print(f"vesktop-venmic-fix: {name} is not a known-buggy build ({current[:12]}), not touching it - "
              "Vesktop probably ships venmic 7.2.5 or newer already")
        continue
    if unpacked:
        tmp = unpacked + ".venmic-fix.tmp"
        with open(tmp, "wb") as f:
            f.write(fix)
        os.chmod(tmp, 0o755)
        os.replace(tmp, unpacked)
        node.update(size=len(fix), integrity=integrity(fix))
    else:
        node.update(offset=str(len(data) + len(appended)), size=len(fix), integrity=integrity(fix))
        appended += fix
    changed.append(name)

if not changed:
    sys.exit(0)

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".venmic-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + appended)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print(f"vesktop-venmic-fix: venmic 7.2.5 installed ({', '.join(changed)}) - restart Vesktop")
