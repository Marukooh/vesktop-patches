# vesktop-patches

Fixes for [Vesktop](https://github.com/Vencord/Vesktop) on Linux that haven't landed upstream yet. The main ones are
**blurry Go Live streams** and **your own stream audio blasting every 5 minutes**. One script installs them all, and on
Arch-based distros a pacman hook re-applies each one after every Vesktop update.

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
| **Go Live bitrate** | Streams start soft and take a long time to sharpen. | Vesktop hard-codes min/target/max bitrates of 0.5/0.6/8 Mbps. The patch raises them to 1.5/5/12 Mbps. |
| **Stream thumbnail mute** | Every 5 minutes, while streaming, you hear a burst of your own stream's audio. | Discord grabs the stream thumbnail by playing the stream, audio included, in a hidden unmuted `<video>`. The patch mutes it (same approach as [Equibop#130](https://github.com/Equicord/Equibop/pull/130), see [Vesktop#1355](https://github.com/Vencord/Vesktop/issues/1355)). |
| **venmic crash fix** | Vesktop crashes (SIGSEGV in `pw_impl_module_destroy`) while screen sharing with audio. | venmic 7.2.3 destroys a PipeWire loopback module twice. The patch swaps in a venmic 7.2.4 build (upstream `main`, [Vencord/venmic@aec88fc](https://github.com/Vencord/venmic/commit/aec88fc)). It only replaces known-buggy builds, so it does nothing once Vesktop ships the fix. |

Patches only matter on the side they affect. The Go Live patches help **whoever is streaming**, so everyone in your group
who streams should install them.

## Requirements

- Vesktop installed as a regular package with a writable `resources/app.asar`: `vesktop-git`, `vesktop` or
  `vesktop-bin` from the AUR, or any other install if you pass `VESKTOP_ASAR=/path/to/resources/app.asar`.
  **Flatpak isn't supported**, because its files are read-only.
- `python3` and `sudo`.
- pacman for the auto re-apply hooks. Without it the patches still apply, but you have to run `./install-all.sh`
  again after each Vesktop update.

## Usage

```sh
./install-all.sh              # install or update everything (safe to re-run)
./status.py                   # what's applied, whether the hooks are in place, whether installed scripts are current
./install-all.sh --uninstall  # remove the hooks and scripts, then reinstall Vesktop for a clean app
```

`install-all.sh` finds Vesktop, copies the patchers to `/usr/local/lib/vesktop-patches/`, backs up `app.asar` there, installs
one pacman hook per patch and applies everything. Each patcher is idempotent: when its change is already in place, or
when the code it targets has changed upstream, it leaves the file alone and says why.

After a `git pull`, run `./install-all.sh` again to update the installed patchers.

## Checking a stream

`diagnostics/stream-stats.js` prints the live resolution, fps, bitrate, encoder and quality-limitation reason of the
streams you send and receive. Paste it into Vesktop's DevTools console (Ctrl+Shift+I; type `allow pasting` first if
asked). `diagnostics/stream-debug.js` dumps Discord's internal Go Live quality state on the streamer's side.

## How it works

Vesktop's UI and its Discord patches live in `resources/app.asar`. The patchers rewrite single entries in that archive
(`dist/js/renderer.js`, `static/dist/venmic-x64.node`) and update the asar header's size and integrity hashes. The
resolution and thumbnail fixes are injected as extra entries in Vesktop's own Vencord-style patch list, so they run
through the same find/replace machinery as Vesktop's built-in patches.

Adding a patch: write an idempotent `patch-*.py` that reads `VESKTOP_ASAR`, add a hook template in `hooks/`, then list it
in `PATCHERS` in `install-all.sh` and in `PATCHES` in `status.py`.

## Disclaimer

Not affiliated with Vesktop, Vencord or Discord. Client modifications are against Discord's Terms of Service, as is
Vesktop itself. Use at your own risk. Tested with `vesktop-git` 1.6.8 on Arch-based CachyOS.

## License

GPL-3.0, the same as Vesktop and Vencord, which the injected patch code is derived from.
