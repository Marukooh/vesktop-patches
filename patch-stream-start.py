#!/usr/bin/env python3
"""Start WebRTC's bandwidth estimate at 3 Mbps instead of Chromium's ~300 kbps default.

Discord's SDP only sets x-google-max-bitrate, so every stream starts from a tiny estimate and stays blurry for the
first ~minute while it ramps up. This appends x-google-start-bitrate to the same fmtp line. It works whether or not
Vencord's WebScreenShareFixes has already rewritten the max-bitrate part.
"""
import hashlib, json, os, re, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"vesktopStartBitrate"
PATCH  = (b'{find:"x-google-max-bitrate",/*vesktopStartBitrate*/replacement:{match:'
          b'/`x-google-max-bitrate=\\$\\{\\i\\}`|"x-google-max-bitrate=80000"/,'
          b'replace:\'$&+";x-google-start-bitrate=3000"\'}},')
# Inserted right before the getDefaultGoliveQuality entry of Vesktop's ScreenSharePicker patch list (whose $self
# has patchStreamQuality()), so the other patches injected here can go in any order.
ANCHOR = re.compile(rb'\{find:"this\.getDefaultGoliveQuality\(\)"')
BLOCK  = 4 * 1024 * 1024

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

if MARKER in js:
    sys.exit("vesktop-stream-start-fix: already patched")
m = ANCHOR.search(js)
if not m:
    sys.exit("vesktop-stream-start-fix: Vesktop patch list not found, not touching it - check ScreenSharePicker upstream")
fix = js[:m.start()] + PATCH + js[m.start():]
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".start-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-stream-start-fix: streams now start at a 3 Mbps estimate - restart Vesktop")
