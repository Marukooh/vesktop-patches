#!/usr/bin/env python3
"""Make Discord encode Go Live at the resolution picked in Vesktop's picker.

Up to 1.6.8: Discord's web setDesktopInput() reads the capture track's constraints when the stream starts, before
Vesktop's applyConstraints() runs, and calls setGoliveQuality() with that (~720p). The encoder then scales the capture
down to 1280 wide whatever resolution was picked. This routes that call through Vesktop's own patchStreamQuality().

1.6.9 fixes that itself, so this patch does nothing there. Earlier versions of it turned off 1.6.9's
scaleEncodeToSinkWants(), which scales the encode resolution down to the viewer's video tile; that made streams blurrier,
because Discord's getGoliveQuality() cuts the bitrate to the tile size anyway, and the server caps it too. On 1.6.9+ this
removes that old change.
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
ANCHOR = re.compile(rb'\{find:"(?:this\.)?getDefaultGoliveQuality\(\)')  # 1.6.9+ dropped "this."
# What earlier versions of this patch put at the top of 1.6.9's scaleEncodeToSinkWants().
OLD_SINK_FIX = re.compile(rb"return [\w$]+;/\*vesktopGoliveFix\*/")
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

if b"applyStreamQuality" in js:
    fix = OLD_SINK_FIX.sub(b"", js)
    if fix == js:
        sys.exit("vesktop-stream-quality-fix: not needed on Vesktop 1.6.9+")
    done = "removed the old override, Go Live scales to the viewer again"
else:
    if MARKER in js:
        sys.exit("vesktop-stream-quality-fix: already patched")
    m = ANCHOR.search(js)
    if not m:
        sys.exit("vesktop-stream-quality-fix: patchStreamQuality patch not found, not touching it - check ScreenSharePicker upstream")
    fix = js[:m.start()] + PATCH + js[m.start():]
    done = "Go Live now encodes at the picker resolution"
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
print(f"vesktop-stream-quality-fix: {done} - restart Vesktop")
