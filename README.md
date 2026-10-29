# Patch locali di Vesktop

Patch per Vesktop su Linux (pensate per Arch e derivate). Tutte modificano il file `resources/app.asar` di Vesktop.

## Installazione

```sh
git clone <questo repo> vesktop-patches
cd vesktop-patches
./install-all.sh
```

Lo script chiede `sudo` e poi:

1. trova Vesktop: il pacchetto pacman (`vesktop-git`, `vesktop` o `vesktop-bin`) che contiene un `resources/app.asar`, oppure uno dei percorsi standard;
2. copia gli script in `/usr/local/lib/vesktop-venmic-fix/` e fa un backup di `app.asar` nella stessa cartella;
3. installa un hook pacman per ogni patch, così le patch vengono riapplicate a ogni aggiornamento di Vesktop;
4. applica tutte le patch e mostra lo stato.

Poi va riavviato Vesktop. Si può rilanciare quante volte si vuole: le patch già applicate vengono saltate. Dopo un `git pull` va rilanciato per aggiornare gli script installati.

Se Vesktop non viene trovato: `VESKTOP_ASAR=/percorso/resources/app.asar ./install-all.sh`.
La versione Flatpak non si può patchare, perché i suoi file sono in sola lettura.
Senza pacman gli hook non vengono installati, e lo script va rilanciato a mano dopo ogni aggiornamento.

Per controllare lo stato in qualsiasi momento: `./status.py`.

Per disinstallare: `./install-all.sh --uninstall` rimuove hook e script, poi va reinstallato Vesktop (es. `paru -S vesktop-git`) per riavere l'app originale.

## Patch

| Patch | Script | Cosa fa |
|---|---|---|
| venmic crash fix | `patch-asar.py` | Sostituisce `venmic-x64.node` (crash SIGSEGV della loopback audio con venmic 7.2.3) con una build di venmic main (7.2.4). Agisce solo se trova una delle build difettose note, quindi su versioni di Vesktop che hanno già il fix non fa niente. Sorgenti delle patch originali in `venmic-pr47/`. |
| Stream thumbnail mute | `patch-stream-preview.py` | Silenzia il `<video>` temporaneo che Discord usa ogni 5 minuti per l'anteprima della live (prima si sentiva l'audio della propria live). |
| Go Live bitrate | `patch-stream-bitrate.py` | `patchStreamQuality` di Vesktop: bitrate min/target/max da 0,5/0,6/8 a 1,5/5/12 Mbps. |
| Go Live resolution | `patch-stream-quality.py` | Discord tara l'encoder sulla risoluzione iniziale della traccia (~720p) prima che Vesktop applichi quella scelta, e la live finisce a 1280 di larghezza. Con la patch l'encoder segue il selettore di Vesktop. |

Gli hook sono in `hooks/*.hook.in`: lo script sostituisce `@PKG@` e `@ASAR@` con quelli rilevati.

Aggiungere una patch: script `patch-*.py` idempotente che legge `VESKTOP_ASAR`, template in `hooks/`, voce in `PATCHERS` di `install-all.sh` e in `PATCHES` di `status.py`.

## Diagnostica

- `diagnostics/stream-stats.js`: da incollare nella console di Vesktop (Ctrl+Shift+I). Mostra risoluzione, fps, kbps e motivo di limitazione della live in entrata e in uscita.
- `diagnostics/stream-debug.js`: lo stato interno della qualità Go Live di Discord (lato chi streamma).
- `diagnostics/trace-stream-audio.sh` + `analyze-trace.py`: registra il grafo PipeWire e segnala collegamenti audio sospetti.
