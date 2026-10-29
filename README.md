# Patch locali di Vesktop

Patch applicate a `vesktop-git` (`/usr/lib/vesktop/resources/app.asar`). Ogni patch ha:

- uno script `patch-*.py` che modifica l'asar ed è idempotente (se è già applicata non fa nulla);
- un hook pacman che la riapplica dopo ogni aggiornamento di `vesktop-git`;
- un `install*.sh` da lanciare con `sudo`, che copia lo script in `/usr/local/lib/vesktop-venmic-fix/`, installa l'hook e applica la patch.

Per vedere lo stato attuale:

```sh
./status.py
```

| Patch | Script | Hook | Installer | Cosa fa |
|---|---|---|---|---|
| venmic crash fix | `patch-asar.py` | `vesktop-venmic-fix.hook` | `install.sh` | Sostituisce `venmic-x64.node` (crash SIGSEGV della loopback con venmic 7.2.3) con una build di venmic main (7.2.4). Si disattiva da sola quando Vesktop include venmic ≥ 7.2.4. Sorgenti delle patch originali in `venmic-pr47/`. |
| Stream thumbnail mute | `patch-stream-preview.py` | `vesktop-stream-preview-fix.hook` | `install-stream-preview.sh` | Silenzia il `<video>` temporaneo che Discord usa ogni 5 minuti per l'anteprima della live (prima si sentiva l'audio della propria live). |
| Go Live bitrate | `patch-stream-bitrate.py` | `vesktop-stream-bitrate-fix.hook` | `install-stream-quality.sh` | `patchStreamQuality` di Vesktop: bitrate min/target/max da 0,5/0,6/8 a 1,5/5/12 Mbps. |
| Go Live resolution | `patch-stream-quality.py` | `vesktop-stream-quality-fix.hook` | `install-stream-quality.sh` | Discord tara l'encoder sulla risoluzione iniziale della traccia (~720p) prima che Vesktop applichi quella scelta. Così l'encoder segue il selettore di Vesktop. |

Backup degli asar originali in `/usr/local/lib/vesktop-venmic-fix/app.asar.*`.

## Diagnostica

- `diagnostics/stream-stats.js`: da incollare nella console di Vesktop (Ctrl+Shift+I). Mostra risoluzione, fps, kbps e motivo di limitazione della live in entrata e in uscita.
- `diagnostics/stream-debug.js`: lo stato interno della qualità Go Live di Discord (lato chi streamma).
- `diagnostics/trace-stream-audio.sh` + `analyze-trace.py`: registra il grafo PipeWire e segnala collegamenti audio sospetti.

## Rimuovere una patch

Elimina il suo hook da `/etc/pacman.d/hooks/` e reinstalla `vesktop-git` (oppure ripristina un `app.asar.*` di backup).
