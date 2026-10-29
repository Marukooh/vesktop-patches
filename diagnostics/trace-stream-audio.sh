#!/bin/sh
# Records PipeWire graph changes with timestamps. Stop with Ctrl+C, then run analyze-trace.py.
out="$HOME/.local/share/vesktop-venmic-fix/trace-$(date +%Y%m%d-%H%M%S).log"
echo "Recording to $out - note the time when you hear the stream audio, then press Ctrl+C"
stdbuf -oL pw-dump -m -N | python3 -u -c '
import sys, datetime
for line in sys.stdin:
    sys.stdout.write(datetime.datetime.now().strftime("%H:%M:%S.%f")[:12] + " " + line)
' > "$out"
