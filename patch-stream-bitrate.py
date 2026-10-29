#!/usr/bin/env python3
"""Raise Vesktop's Go Live bitrates: it hardcodes a 600 kbps start target, so streams start (and recover) blurry."""
import hashlib, json, os, re, struct, sys

ASAR    = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY   = ["dist", "js", "renderer.js"]
# patchStreamQuality() in src/renderer/components/ScreenSharePicker.tsx
STOCK   = re.compile(rb"bitrateMin:[0-9.e]+,bitrateMax:[0-9.e]+,bitrateTarget:[0-9.e]+")
WANTED  = b"bitrateMin:15e5,bitrateMax:12e6,bitrateTarget:5e6"
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

js = data[int(node["offset"]):int(node["offset"]) + node["size"]]

if WANTED in js:
    sys.exit("vesktop-stream-bitrate-fix: already patched")
fix, n = STOCK.subn(WANTED, js)
if n != 1:
    sys.exit(f"vesktop-stream-bitrate-fix: found {n} bitrate blocks, not touching it - check patchStreamQuality upstream")
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".bitrate-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-stream-bitrate-fix: Go Live bitrate raised (start 5 Mbps, min 1.5, max 12) - restart Vesktop")
