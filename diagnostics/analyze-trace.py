#!/usr/bin/env python3
"""Flag suspicious audio links in a trace-*.log written by trace-stream-audio.sh."""
import json, sys, glob, os

path = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trace-*.log")), key=os.path.getmtime)
names, cls, links = {}, {}, {}
buf, ts, depth = [], None, 0
ok_targets = ("vencord-sink",)

def handle(arr, t):
    for o in arr:
        oid = o.get("id")
        if o.get("info") is None:
            if oid in links:
                a, b, t0 = links.pop(oid)
                report(t, "-", a, b)
            continue
        p = o["info"].get("props") or {}
        if o["type"].endswith("Node"):
            if p.get("node.name"): names[oid] = p["node.name"]
            if p.get("media.class"): cls[oid] = p["media.class"]
        if o["type"].endswith("Link") and oid not in links:
            a, b = o["info"]["output-node-id"], o["info"]["input-node-id"]
            links[oid] = (a, b, t)
            report(t, "+", a, b)

def report(t, sign, a, b):
    an, bn = names.get(a, str(a)), names.get(b, str(b))
    venmic_src = an.startswith(("venmic-loopback-playback", "vencord-sink", "vencord-screen-share"))
    bad = (venmic_src and not bn.startswith(ok_targets) and not (an.startswith("vencord-") and bn in ("vencord-screen-share", "vesktop"))) \
          or (an.startswith("vencord-screen-share") and bn != "vesktop")
    tag = "!!" if bad else "  "
    if bad or an.startswith(("venmic", "vencord")) or bn.startswith(("venmic", "vencord")):
        print(f"{t} {tag} {sign} {an[:48]:48} -> {bn[:60]}")

for line in open(path, errors="replace"):
    t, _, rest = line.rstrip("\n").partition(" ")
    if rest == "[":
        buf, ts = [rest], t
        continue
    buf.append(rest)
    if rest == "]":
        try:
            handle(json.loads("\n".join(buf)), ts)
        except json.JSONDecodeError:
            pass
        buf = []
