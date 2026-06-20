#!/usr/bin/env bash
# Transcribe a LOCAL sermon audio file with mlx-whisper (Apple GPU) at large-v3 and
# word-level timestamps, producing the per-sermon working dir the pipeline expects:
#   <out>/audio.{txt,srt,json,tsv,vtt}  +  <out>/emphasis_full/audio.{wav,json}
#
# Usage: transcribe_local.sh <audio-file> <out-dir>
# On this M3 Max, large-v3 runs ~10x realtime (a 1-hr sermon in ~6 min, incl. word ts).
# Override the model with MLX_WHISPER_MODEL=… (e.g. mlx-community/whisper-medium.en-mlx).
set -euo pipefail
SRC="${1:?usage: transcribe_local.sh <audio-file> <out-dir>}"
OUT="${2:?usage: transcribe_local.sh <audio-file> <out-dir>}"
MODEL="${MLX_WHISPER_MODEL:-mlx-community/whisper-large-v3-mlx}"
mkdir -p "$OUT/emphasis_full"

# 1. canonical copy of the source audio
cp "$SRC" "$OUT/audio.mp3"

# 2. 16k mono wav for the emphasis (acoustic prominence) pass
#    </dev/null: ffmpeg reads stdin for interactive keys; under a `while read … | …` batch
#    loop it would otherwise swallow lines of the piped work-list and corrupt the next iter.
ffmpeg -y -i "$OUT/audio.mp3" -ac 1 -ar 16000 "$OUT/emphasis_full/audio.wav" -loglevel error </dev/null

# 3. transcribe with word timestamps (mlx flag names use dashes, value after --word-timestamps)
#    the proper-noun seed comes from the series' series.config (walk-up); WHISPER_PROMPT overrides.
SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT="${WHISPER_PROMPT:-$(python3 "$SCRIPTDIR/series_config.py" "$OUT" whisper_prompt)}"
# --condition-on-previous-text False is the key anti-repetition guard: with the default True,
# large-v3 can latch onto a phrase and emit it for the rest of a long sermon (a "repetition
# collapse" — silently corrupted CP07/09/10 on the first run). False stops the looped output
# from feeding back as context. hallucination-silence-threshold skips silent-gap hallucinations.
TEMP="${MLX_WHISPER_TEMPERATURE:-0}"   # batch bumps this to 0.4 on a collapse retry
PYTHONUNBUFFERED=1 mlx_whisper "$OUT/audio.mp3" --model "$MODEL" --language en \
  --word-timestamps True --output-format all --output-dir "$OUT" \
  --initial-prompt "$PROMPT" \
  --condition-on-previous-text False \
  --hallucination-silence-threshold 2.0 \
  --temperature "$TEMP" \
  > "$OUT/whisper.log" 2>&1 </dev/null

# 4. word-timestamp json feeds the emphasis detector
cp "$OUT/audio.json" "$OUT/emphasis_full/audio.json"

# 5. repetition-collapse gate: if one line dominates the transcript, large-v3 looped — fail loudly
#    so the batch/orchestrator never feeds a degenerate transcript to the editorial stage.
python3 - "$OUT/audio.txt" <<'PY'
import sys, collections
lines=[l.strip() for l in open(sys.argv[1]) if l.strip()]
if lines:
    top,cnt=collections.Counter(lines).most_common(1)[0]
    pct=cnt*100//len(lines)
    if pct>=25:
        sys.stderr.write(f"COLLAPSE: top line is {pct}% of {len(lines)} lines: {top[:60]!r}\n")
        sys.exit(3)
print(f"transcript OK ({len(set(lines))}/{len(lines)} unique lines)")
PY
echo "Done. Verbatim transcript: $OUT/audio.txt   word-ts json: $OUT/emphasis_full/audio.json"
