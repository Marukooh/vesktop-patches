#!/usr/bin/env python3
"""Swap Vesktop's bundled venmic 7.2.3 (loopback double-destroy crash) for upstream main (7.2.4, rohrkabel 13.1.2)."""
import hashlib, json, os, struct, sys

ASAR    = "/usr/lib/vesktop/resources/app.asar"
FIX     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venmic-x64.node")
ENTRY   = ["static", "dist", "venmic-x64.node"]
BUGGY   = {"6c10a6d33ab59f2c3f13994e2572f653cf7c26961454b6300ed9add777e142ce",  # upstream venmic 7.2.3
           "9d6f5da90bc63f53192275217e09c9b46ee66d7a574368e92f086234da44b262",  # earlier local fix (#45 only)
           "96005f9f661f51615de8a5a5c2d59ef7c898cf4426af7115ef21b0018b192cda",  # earlier local fix (#45 + #46)
           "f72dba66aba78729d04aa6916e042cd029237d17f2f4a054d69b89de633e616e"}  # earlier local fix (PR #47 build)
BLOCK   = 4 * 1024 * 1024

def integrity(data):
    blocks = [hashlib.sha256(data[i:i + BLOCK]).hexdigest() for i in range(0, max(len(data), 1), BLOCK)]
    return {"algorithm": "SHA256", "hash": hashlib.sha256(data).hexdigest(), "blockSize": BLOCK, "blocks": blocks}

with open(ASAR, "rb") as f:
    raw = f.read()

_, header_size = struct.unpack_from("<II", raw, 0)
_, json_len    = struct.unpack_from("<Ii", raw, 8)
header         = json.loads(raw[16:16 + json_len])
data           = raw[8 + header_size:]

node = header
for part in ENTRY:
    node = node["files"][part]

fix     = open(FIX, "rb").read()
current = hashlib.sha256(data[int(node["offset"]):int(node["offset"]) + node["size"]]).hexdigest()

if current == hashlib.sha256(fix).hexdigest():
    sys.exit("vesktop-venmic-fix: already patched")
if current not in BUGGY:
    sys.exit(f"vesktop-venmic-fix: bundled venmic changed ({current[:12]}), not touching it - check if upstream fixed the crash")

node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".venmic-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-venmic-fix: patched venmic installed - restart Vesktop")
