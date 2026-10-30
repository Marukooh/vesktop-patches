#!/usr/bin/env python3
"""Keep other people's webcams loading with Vesktop's hardware video acceleration on.

With hardware acceleration on (VA-API, e.g. NVIDIA's libva-nvidia-driver) Chromium can decode H.265, so it puts H.265 in
its WebRTC SDP. When the account is in Discord's "browser HEVC" experiment, Discord's web client then announces H.265 as
its first video codec, and the voice server sends no camera video to this client at all: webcams stay stuck loading.

The main fix is a Vencord-style patch that makes Discord read that experiment flag as off, so it keeps to
H.264/VP8/VP9 (the hardware decoder still handles those). A fallback guard also makes HEVC decodingInfo() queries answer
"unsupported", which covers Discord's other HEVC check.
"""
import hashlib, json, os, re, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"vesktopNoBrowserHevc"
PATCH  = (b'{find:"parseLocalDescription(){",/*vesktopNoBrowserHevc*/replacement:{match:'
          b'/this\\.experimentFlags\\.has\\(\\i\\.\\i\\.BROWSER_HEVC\\)/g,replace:"!1"}},')
# Inserted right before the getDefaultGoliveQuality entry of Vesktop's ScreenSharePicker patch list, like the other
# patches injected here, so they can go in any order.
ANCHOR = re.compile(rb'\{find:"this\.getDefaultGoliveQuality\(\)"')
GUARD_MARKER = b"vesktopNoHevc*/"
# renderer.js runs in the page's main world before Discord's own scripts, so this wraps the API Discord calls.
GUARD  = (b';(()=>{/*vesktopNoHevc*/const P=globalThis.MediaCapabilities?.prototype,d=P?.decodingInfo;if(!d)return;'
          b'P.decodingInfo=function(c){try{if(/\\b(hev1|hvc1)\\b/i.test(c?.video?.contentType??""))'
          b'return Promise.resolve({supported:false,smooth:false,powerEfficient:false})}catch{}'
          b'return d.apply(this,arguments)}})();\n')
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

fix = js
if MARKER not in fix:
    m = ANCHOR.search(fix)
    if m:
        fix = fix[:m.start()] + PATCH + fix[m.start():]
    else:
        print("vesktop-no-hevc-fix: Vesktop patch list not found, only installing the decodingInfo guard")
if GUARD_MARKER not in fix:
    fix = fix + b"\n" + GUARD
if fix == js:
    sys.exit("vesktop-no-hevc-fix: already patched")
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".no-hevc-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-no-hevc-fix: H.265 hidden from Discord, webcams load with hardware acceleration on - restart Vesktop")
