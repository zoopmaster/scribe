#!/usr/bin/env bash
# Download a SermonAudio sermon and transcribe it with word-level timestamps.
# Usage: transcribe.sh <sermonaudio-url> <out-dir>
#
# Engine: mlx-whisper (Apple GPU) at large-v3 — ~10x realtime on this M3 Max (a 1-hr
# sermon in ~6 min). For a LOCAL audio file, use transcribe_local.sh instead.
set -euo pipefail
URL="${1:?usage: transcribe.sh <url> <out-dir>}"
OUT="${2:?usage: transcribe.sh <url> <out-dir>}"
mkdir -p "$OUT/emphasis_full"

# 1. audio (yt-dlp uses SermonAudio's generic html5 extractor -> cloud.sermonaudio.com)
yt-dlp --no-playlist -f bestaudio -o "$OUT/audio.%(ext)s" "$URL"
AUDIO=$(ls "$OUT"/audio.* | grep -v '\.json$\|\.srt$\|\.txt$\|\.vtt$\|\.tsv$' | head -1)

# 2. 16k mono wav for the emphasis pass
ffmpeg -y -i "$AUDIO" -ac 1 -ar 16000 "$OUT/emphasis_full/audio.wav" -loglevel error

# 3. transcribe with word timestamps (mlx-whisper, Apple GPU, large-v3)
#    proper-noun seed from the series' series.config (walk-up); WHISPER_PROMPT overrides.
MODEL="${MLX_WHISPER_MODEL:-mlx-community/whisper-large-v3-mlx}"
SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT="${WHISPER_PROMPT:-$(python3 "$SCRIPTDIR/series_config.py" "$OUT" whisper_prompt)}"
PYTHONUNBUFFERED=1 mlx_whisper "$AUDIO" --model "$MODEL" --language en \
  --word-timestamps True --output-format all --output-dir "$OUT" \
  --initial-prompt "$PROMPT" \
  > "$OUT/whisper.log" 2>&1

# 4. word-timestamp json feeds the emphasis detector
cp "$OUT/audio.json" "$OUT/emphasis_full/audio.json"
echo "Done. Verbatim transcript: $OUT/audio.txt   word-ts json: $OUT/emphasis_full/audio.json"
