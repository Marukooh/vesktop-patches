#!/usr/bin/env python3
"""Mute the temporary <video> Discord uses to grab the stream thumbnail every 5 minutes (Vesktop#1355, Equibop#130)."""
import hashlib, json, os, re, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"ApplicationStreamPreviewUploadManager"
# Same patch as Equibop#130, injected into the patches array of Vesktop's hideVenmicInput patch.
PATCH  = (b'{find:"ApplicationStreamPreviewUploadManager",replacement:{match:/(\\i)\\.srcObject=(\\i),\\1\\.play\\(\\)/,'
          b'replace:"$1.muted=true,$1.srcObject=$2,$1.play()"}},')
ANCHOR = re.compile(rb"""\{find:['"]setSinkId"in['"]""")
# Fallback that doesn't depend on Discord's minified code: mute any detached <video> playing a stream with audio.
GUARD_MARKER = b"vesktopPreviewMute"
GUARD  = (b';(()=>{/*vesktopPreviewMute*/const p=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){'
          b'try{if(this instanceof HTMLVideoElement&&!this.isConnected&&this.srcObject instanceof MediaStream&&this.srcObject.getAudioTracks().length)this.muted=true}catch{}'
          b'return p.apply(this,arguments)}})();\n')
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
        print("vesktop-stream-preview-fix: anchor not found, only installing the play() guard")
if GUARD_MARKER not in fix:
    fix = fix + b"\n" + GUARD
if fix == js:
    sys.exit("vesktop-stream-preview-fix: already patched (or upstream fixed it)")
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".preview-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-stream-preview-fix: stream thumbnail muted - restart Vesktop")
