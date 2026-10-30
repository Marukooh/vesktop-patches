# vesktop-patches

Fixes for [Vesktop](https://github.com/Vencord/Vesktop) on Linux that haven't landed upstream yet. The main ones are
**blurry Go Live streams** and **your own stream audio blasting every 5 minutes**. One script installs them all on any
distro and sets up their automatic re-application after every Vesktop update: pacman hooks on Arch-based distros, a
systemd unit everywhere else.

```sh
git clone https://github.com/Marukooh/vesktop-patches
cd vesktop-patches
./install-all.sh
```

Then restart Vesktop.

## What's fixed

| Patch | Symptom | Cause and fix |
|---|---|---|
| **Go Live resolution** | Streams look blurry the whole time, whatever resolution you pick. On a 21:9 monitor the viewer gets 1280×536. | When the stream starts, Discord's web client sizes the encoder from the capture track's constraints (about 720p). Vesktop only applies the resolution you picked 100 ms later, so the encoder keeps scaling the capture down to 1280 px wide. The patch passes the picker's resolution, framerate and bitrate straight to Discord. |
| **Go Live start bitrate** | Every stream looks awful for roughly its first minute, then slowly sharpens. | Discord's SDP sets only `x-google-max-bitrate`, so Chromium starts its bandwidth estimate at about 300 kbps and ramps up from there. The patch adds `x-google-start-bitrate=3000` (3 Mbps); the estimate still drops if the link can't keep up. |
| **Go Live bitrate** | Streams start soft and take a long time to sharpen. | Vesktop hard-codes min/target/max bitrates of 0.5/0.6/8 Mbps. The patch raises them to 1.5/5/12 Mbps. |
| **Stream thumbnail mute** | Every 5 minutes, while streaming, you hear a burst of your own stream's audio. | Discord grabs the stream thumbnail by playing the stream, audio included, in a hidden unmuted `<video>`. The patch mutes it (same approach as [Equibop#130](https://github.com/Equicord/Equibop/pull/130), see [Vesktop#1355](https://github.com/Vencord/Vesktop/issues/1355)). |
| **Webcams with hardware acceleration** | With *Hardware video acceleration* on, other people's webcams stay stuck loading. The voice server sends no video at all (0 kbps, `video-stream-receiver-ready-timeout` in the console). | With hardware decoding through VA-API (e.g. NVIDIA's `libva-nvidia-driver`) Chromium puts H.265 in its WebRTC SDP. Accounts in Discord's "browser HEVC" experiment then announce H.265 as their first video codec, and the camera video never arrives. The patch makes Discord read that experiment as off, and also answers HEVC `navigator.mediaCapabilities.decodingInfo()` queries as "unsupported" (Discord's other HEVC check). The hardware decoder keeps handling H.264, VP8 and VP9. See also [Vesktop#1207](https://github.com/Vencord/Vesktop/issues/1207). **On NVIDIA this isn't enough**, especially with several webcams on: see the FAQ. |
| **venmic crash fix** | Vesktop crashes (SIGSEGV in `pw_impl_module_destroy`) while screen sharing with audio. | venmic 7.2.3 destroys a PipeWire loopback module twice. The patch swaps in venmic 7.2.5, which has the fix ([Vencord/venmic@aec88fc](https://github.com/Vencord/venmic/commit/aec88fc)) and two routing fixes. The binaries in `venmic/` are the unmodified x64 and arm64 prebuilds from the [`@vencord/venmic` 7.2.5 npm package](https://www.npmjs.com/package/@vencord/venmic), which need only glibc 2.30 and PipeWire. It only replaces known-buggy builds, so it does nothing once Vesktop ships 7.2.5 or newer. |

Patches only matter on the side they affect. The Go Live patches help **whoever is streaming**, so everyone in your group
who streams should install them. The webcam patch helps **whoever is watching** with hardware acceleration on.

## Requirements

- Linux on x86_64 or arm64, with Vesktop installed so that its `resources/app.asar` is writable:

  | Install | Found automatically at | Supported |
  |---|---|---|
  | AUR (`vesktop-git`, `vesktop`, `vesktop-bin`) or another distro package | wherever the package puts it (asked to pacman, dpkg or rpm) | yes |
  | Official `.deb` / `.rpm` from [Vesktop's releases](https://github.com/Vencord/Vesktop/releases) | `/opt/Vesktop` | yes |
  | Official `.tar.gz` | via the `vesktop` command, `/opt`, or `~/Applications`, `~/.local/share`, `~/opt`, `~` | yes |
  | Anywhere else | pass `VESKTOP_ASAR=/path/to/resources/app.asar` | yes |
  | Flatpak, Snap, AppImage, NixOS | | **no**: their files are read-only |

- `python3`, and `sudo`, `doas` or `pkexec`.
- To re-apply the patches after Vesktop updates: pacman (one hook per patch) or systemd (one path unit that watches
  `app.asar`, so it works with apt, dnf, zypper or a new tarball unpacked over the old one). Without either, the patches
  still apply, but you have to run `./install-all.sh` again after each Vesktop update. `VESKTOP_REAPPLY=pacman|systemd|none`
  forces a method.

## Usage

```sh
./install-all.sh              # install or update everything (safe to re-run)
./status.py                   # what's applied, what re-applies it after updates, whether installed scripts are current
./install-all.sh --uninstall  # remove the hooks, unit and scripts, then reinstall Vesktop for a clean app
```

`install-all.sh` finds Vesktop, copies the patchers to `/usr/local/lib/vesktop-patches/`, backs up `app.asar` there, installs
the pacman hooks or the `vesktop-patches.path` systemd unit, and applies everything. Each patcher is idempotent: when its change is already in place, or
when the code it targets has changed upstream, it leaves the file alone and says why.

After a `git pull`, run `./install-all.sh` again to update the installed patchers.

## Checking a stream

`diagnostics/stream-stats.js` prints one row per video stream you send (`outbound`) or receive (`inbound`). Paste it
into Vesktop's DevTools console (Ctrl+Shift+I; type `allow pasting` first if asked) while a stream is running.

| Column | Meaning |
|---|---|
| `res`, `fps`, `kbps` | What is actually being sent or received right now. |
| `impl` | Encoder or decoder in use (`OpenH264` = software encoding). |
| `limit`, `limitTime` | Why WebRTC is holding quality back (`bandwidth`, `cpu` or `none`), and the seconds spent in each state. |
| `qpAvg` | Average quantizer: lower is sharper. Around 15 or less looks good for H.264. |
| `bweKbps` | WebRTC's current estimate of the available upload bandwidth. |
| `rttMs`, `lossPct`, `nacks`, `retxKbps` | Round-trip time, packet loss and retransmissions reported by Discord's server. Non-zero loss or a climbing RTT point to the network (often WiFi), not the client. |

What to look for:

- `res` far below the resolution you picked: install the **Go Live resolution** patch.
- Many seconds of `bandwidth` in `limitTime` right after going live, with no loss and a low RTT: that's the slow
  bandwidth-estimate ramp, fixed by the **Go Live start bitrate** patch.
- `bandwidth` with real loss or a high RTT: a network problem. Try ethernet, 30 fps instead of 60, or a narrower WiFi
  channel.
- `cpu`: the software encoder can't keep up. Lower the resolution or the fps.

`diagnostics/stream-debug.js` dumps Discord's internal Go Live quality state on the streamer's side.

## FAQ

**Can Vesktop encode the stream on the GPU (NVENC)?** Not on NVIDIA. Chromium encodes on the GPU on Linux only through
VA-API, and NVIDIA's VA-API driver (`libva-nvidia-driver`) only decodes. On AMD and Intel, VA-API encoding may work
through Chromium flags, but these patches don't touch it. In practice the CPU is rarely the limit: check that `limit`
isn't `cpu` before chasing hardware encoding.

**Webcams still don't load on NVIDIA, especially with several on. What now?** Turn off *Hardware video acceleration* in
Vesktop's settings (keep *Hardware acceleration* on) and restart Vesktop. On NVIDIA that option only enables decoding
through `libva-nvidia-driver` (`vainfo` lists only `VAEntrypointVLD`, no encoder), which Chromium doesn't officially
support and which fails with several video streams at once. Streams are encoded in software either way, and decoding a
few webcams costs the CPU very little, so turning it off loses nothing in practice.

**Why not use the official Discord client?** Its native media engine does use NVENC, but on Linux it doesn't let you
pick which apps' audio goes into the stream. Vesktop (via venmic) does.

## How it works

Vesktop's UI and its Discord patches live in `resources/app.asar`. The patchers rewrite single entries in that archive
(`dist/js/renderer.js`, `static/dist/venmic-{x64,arm64}.node`) and update the asar header's size and integrity hashes. The
resolution, start-bitrate, thumbnail and webcam fixes are injected as extra entries in Vesktop's own Vencord-style patch list, so
they run through the same find/replace machinery as Vesktop's built-in patches, and they apply in any order. The thumbnail and
webcam fixes also append a fallback guard to `renderer.js`, which Vesktop runs in the page before Discord's own scripts.

The systemd unit runs `apply-all.sh`, which runs every installed `patch-*.py`. The patchers' own writes trigger the unit
once more, and that run finds nothing left to do.

Adding a patch: write an idempotent `patch-*.py` that reads `VESKTOP_ASAR`, add a pacman hook template in `hooks/`, and
list it in `PATCHES` in `status.py`. `install-all.sh` and `apply-all.sh` pick up every `patch-*.py` on their own.

## Disclaimer

Not affiliated with Vesktop, Vencord or Discord. Client modifications are against Discord's Terms of Service, as is
Vesktop itself. Use at your own risk. Tested with `vesktop-git` 1.6.8 on Arch-based CachyOS, and against the official 1.6.8 release
archive.

## License

GPL-3.0, the same as Vesktop and Vencord, which the injected patch code is derived from.
