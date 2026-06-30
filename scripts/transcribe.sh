#!/usr/bin/env bash
# Download a SermonAudio sermon, then transcribe it with word-level timestamps.
# Usage: transcribe.sh <sermonaudio-url> <out-dir>
#
# This is a thin wrapper: it ONLY fetches the audio, then hands off to transcribe_local.sh
# so the URL path and the local-file path share ONE transcription engine — identical
# hardening (--condition-on-previous-text False, hallucination threshold) and the same
# repetition-collapse gate. Engine: mlx-whisper (Apple GPU) at large-v3, ~10x realtime.
set -euo pipefail
URL="${1:?usage: transcribe.sh <url> <out-dir>}"
OUT="${2:?usage: transcribe.sh <url> <out-dir>}"
SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"

# 1. fetch audio to a scratch path OUTSIDE the out-dir (transcribe_local.sh copies SRC ->
#    $OUT/audio.mp3, so downloading straight to $OUT/audio.* would self-collide on that cp).
DL="$(mktemp -d "${TMPDIR:-/tmp}/scribe-dl.XXXXXX")"
trap 'rm -rf "$DL"' EXIT
yt-dlp --no-playlist -f bestaudio -o "$DL/audio.%(ext)s" "$URL"
AUDIO="$(ls "$DL"/audio.* | head -1)"

# 2. hand off to the single hardened transcription engine (ffmpeg wav + mlx + collapse gate).
#    Not exec'd, so the EXIT trap still fires to clean up the scratch download.
"$SCRIPTDIR/transcribe_local.sh" "$AUDIO" "$OUT"
