// Paste in Vesktop DevTools console (Ctrl+Shift+I) while watching or streaming.
(async () => {
    const seen = new Set(), pcs = [];
    const walk = (o, d) => {
        if (!o || typeof o !== "object" || seen.has(o) || d > 6) return;
        seen.add(o);
        if (o instanceof RTCPeerConnection) return void pcs.push(o);
        if (o instanceof Map || o instanceof Set) for (const v of o.values()) walk(v, d + 1);
        for (const k of Object.keys(o)) try { walk(o[k], d + 1); } catch { }
    };
    walk(Vencord.Webpack.findStore("MediaEngineStore").getMediaEngine(), 0);

    const snap = async () => Promise.all(pcs.map(pc => pc.getStats()));
    const a = await snap();
    await new Promise(r => setTimeout(r, 3000));
    const b = await snap();

    const rows = [];
    b.forEach((stats, i) => stats.forEach(s => {
        if (s.kind !== "video" || !/^(inbound|outbound)-rtp$/.test(s.type)) return;
        const prev = a[i].get(s.id);
        const bytes = s.type === "inbound-rtp" ? "bytesReceived" : "bytesSent";
        rows.push({
            dir: s.type.split("-")[0],
            res: `${s.frameWidth}x${s.frameHeight}`,
            fps: s.framesPerSecond,
            kbps: prev ? Math.round((s[bytes] - prev[bytes]) * 8 / 3000) : "?",
            codec: stats.get(s.codecId)?.mimeType,
            impl: s.decoderImplementation ?? s.encoderImplementation,
            limit: s.qualityLimitationReason,
            limitTime: s.qualityLimitationDurations && JSON.stringify(s.qualityLimitationDurations),
            lost: s.packetsLost,
            freezes: s.freezeCount,
            qpAvg: s.qpSum && s.framesDecoded ? (s.qpSum / s.framesDecoded).toFixed(1) : s.qpSum && s.framesEncoded ? (s.qpSum / s.framesEncoded).toFixed(1) : undefined
        });
    }));
    console.table(rows);
})();
