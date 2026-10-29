#!/usr/bin/env python3
"""Make Discord encode Go Live at the resolution picked in Vesktop's picker.

Discord's web setDesktopInput() reads the capture track's constraints when the stream starts, before Vesktop's
applyConstraints() runs, and calls setGoliveQuality() with that (~720p). The encoder then scales the capture down
to 1280 wide whatever resolution was picked. This routes that call through Vesktop's own patchStreamQuality().
"""
import hashlib, json, os, re, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"vesktopGoliveFix"
PATCH  = (b'{find:"setDesktopInput=e=>{",/*vesktopGoliveFix*/replacement:{match:'
          b'/this\\.videoQualityManager\\.setGoliveQuality\\(\\{encode:(\\i),capture:\\1,bitrateMax:(\\i)\\}\\)/,'
          b'replace:"this.videoQualityManager.setGoliveQuality($self.patchStreamQuality({encode:{...$1},capture:{...$1},bitrateMax:$2}))"}},')
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
    sys.exit("vesktop-stream-quality-fix: already patched")
m = ANCHOR.search(js)
if not m:
    sys.exit("vesktop-stream-quality-fix: patchStreamQuality patch not found, not touching it - check ScreenSharePicker upstream")
fix = js[:m.start()] + PATCH + js[m.start():]
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".quality-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-stream-quality-fix: Go Live now encodes at the picker resolution - restart Vesktop")
