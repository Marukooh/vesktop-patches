// Paste in the STREAMER's Vesktop DevTools console (Ctrl+Shift+I) while live.
(async () => {
    const me = Vencord.Webpack.Common.UserStore.getCurrentUser().id;
    const conn = [...Vencord.Webpack.findStore("MediaEngineStore").getMediaEngine().connections]
        .find(c => c.streamUserId === me);
    if (!conn) return console.log("No own stream connection found - are you live?");

    const vqm = conn.videoQualityManager;
    const q = vqm?.goliveMaxQuality;
    const track = conn.input?.stream?.getVideoTracks?.()[0];

    const seen = new Set();
    let pc = null;
    const walk = (o, d) => {
        if (pc || !o || typeof o !== "object" || seen.has(o) || d > 5) return;
        seen.add(o);
        if (o instanceof RTCPeerConnection) return void (pc = o);
        for (const k of Object.keys(o)) try { walk(o[k], d + 1); } catch { }
    };
    walk(conn, 0);
    const enc = pc?.getSenders().find(s => s.track?.kind === "video")?.getParameters().encodings;

    console.log(JSON.stringify({
        goliveMaxQuality: q && { capture: q.capture, encode: q.encode, bitrateMin: q.bitrateMin, bitrateMax: q.bitrateMax, bitrateTarget: q.bitrateTarget },
        currentQuality: (() => { try { const c = vqm.getQuality(conn.videoStreamParameters?.[0]?.ssrc); return { capture: c.capture, encode: c.encode, bitrateMax: c.bitrateMax }; } catch (e) { return String(e); } })(),
        streamParameters: conn.videoStreamParameters,
        remoteSinkWants: conn.remoteVideoSinkWants,
        trackSettings: track?.getSettings(),
        trackConstraints: track?.getConstraints(),
        senderEncodings: enc
    }, null, 2));
})();
