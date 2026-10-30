#!/usr/bin/env python3
"""Keep other people's webcams loading with Vesktop's hardware video acceleration on.

On Linux, Discord's web client asks navigator.mediaCapabilities.decodingInfo() whether HEVC decodes in hardware and, if
it does, tells the voice server it can receive H.265. With hardware acceleration on (VA-API, e.g. NVIDIA's
libva-nvidia-driver) Chromium says yes, the server then sends no camera video to this client at all, and webcams stay
stuck loading. This makes HEVC decode queries answer "unsupported", so Discord keeps to H.264/VP8/VP9/AV1 while the
hardware decoder still handles those.
"""
import hashlib, json, os, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"vesktopNoHevc"
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

if MARKER in js:
    sys.exit("vesktop-no-hevc-fix: already patched")
fix = js + b"\n" + GUARD
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
print("vesktop-no-hevc-fix: HEVC hidden from Discord, webcams load with hardware acceleration on - restart Vesktop")
