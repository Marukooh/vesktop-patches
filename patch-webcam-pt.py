#!/usr/bin/env python3
"""Keep every webcam loading when several are on, with Electron 45 (Chromium 156) and newer.

Discord's web client answers every video receiver with H.264 on payload type 102, declared as Constrained Baseline
(profile-level-id=42e01f), while Chromium offered 102 as Baseline (42001f). Newer Chromium treats that as a payload type
conflict and gives Baseline a new payload type (127) in every video receiver added after the first. The voice server
still sends 102, so Chromium drops those packets: only the first webcam loads, the others stay stuck loading.

The fix wraps setRemoteDescription and copies the profile from Chromium's own offer into Discord's answer for each
payload type both sides already agree on, so the conflict never comes up and 102 stays H.264 in every receiver.
"""
import hashlib, json, os, struct, sys

ASAR   = os.environ.get("VESKTOP_ASAR", "/usr/lib/vesktop/resources/app.asar")
ENTRY  = ["dist", "js", "renderer.js"]
MARKER = b"vesktopPtFix*/"
# renderer.js runs in the page's main world before Discord's own scripts, so this wraps the API Discord calls.
GUARD  = rb''';(()=>{/*vesktopPtFix*/const P=globalThis.RTCPeerConnection?.prototype,srd=P?.setRemoteDescription;if(!srd)return;
const K=["profile-level-id","profile-id","profile"],sec=s=>s.split(/\r\n(?=m=)/),mid=s=>s.match(/\r\na=mid:(\S+)/)?.[1];
const fix=(r,l)=>{const loc={};for(const s of sec(l)){const m=mid(s);if(m!=null)loc[m]=s}
return sec(r).map(s=>{const L=loc[mid(s)];if(!L)return s;const name=(t,p)=>t.match(new RegExp("\\r\\na=rtpmap:"+p+" ([^/\\s]+)"))?.[1]?.toLowerCase();
return s.replace(/(\r\na=fmtp:(\d+) )([^\r]*)/g,(all,a,pt,f)=>{const n=name(s,pt);if(!n||n!==name(L,pt))return all;
const lf=L.match(new RegExp("\\r\\na=fmtp:"+pt+" ([^\\r]*)"))?.[1]??"";
for(const k of K){const v=lf.match(new RegExp("(?:^|;)"+k+"=([^;]*)"))?.[1],re=new RegExp("((?:^|;)"+k+"=)[^;]*");if(v!=null&&re.test(f))f=f.replace(re,"$1"+v)}return a+f})}).join("\r\n")};
globalThis.__vesktopPtFix=fix;
P.setRemoteDescription=function(d,...a){try{const l=this.localDescription?.sdp;if(d?.sdp&&l){const sdp=fix(d.sdp,l);if(sdp!==d.sdp)d={type:d.type,sdp}}}catch(e){console.warn("vesktopPtFix",e)}return srd.call(this,d,...a)}})();
'''
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
    sys.exit("vesktop-webcam-pt-fix: already patched")
fix = js + b"\n" + GUARD
node.update(offset=str(len(data)), size=len(fix), integrity=integrity(fix))

payload = json.dumps(header, separators=(",", ":")).encode()
pickle  = struct.pack("<i", len(payload)) + payload
pickle += b"\0" * (-len(pickle) % 4)
pickle  = struct.pack("<I", len(pickle)) + pickle

tmp = ASAR + ".webcam-pt-fix.tmp"
with open(tmp, "wb") as f:
    f.write(struct.pack("<II", 4, len(pickle)) + pickle + data + fix)
os.chmod(tmp, 0o644)
os.replace(tmp, ASAR)
print("vesktop-webcam-pt-fix: H.264 payload types kept in sync, every webcam loads - restart Vesktop")
