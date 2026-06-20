#!/usr/bin/env bash
# Prune intermediate artifacts from a sermon dir, keeping only what you asked for.
# DESTRUCTIVE — the SKILL asks the user first and prefers a --dry-run preview.
#
# Usage: prune_sermon.sh <sermon-dir> [--keep tok,tok,…] [--dry-run]
#   keep tokens (comma-separated):
#     final     the …-BOOK-final.md deliverable      (kept by default)
#     figures   figure-*, *.svg/*.png/*.jpg/*.jpeg   (kept by default — part of the deliverable)
#     html      the …-emph.html preview
#     emph      the …-BOOK-emph.md curated source
#     source    the …-BOOK.md transcript-revision source
#     logs      CORRECTIONS-LOG.md, SCRIPTURE-VERIFICATION.md, FLAGS.md
#     audio     audio.*, source.mp3, emphasis_full/, whisper.log, *.srt/*.vtt/*.tsv
#   Default when --keep is omitted:  final,figures,logs
# Anything in a known deletable category that is NOT kept is removed. Unrecognized files are
# left untouched. The …-BOOK-final.md is never deleted unless you explicitly omit `final`.
set -uo pipefail
DIR=""; KEEP="final,figures,logs"; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --keep) KEEP="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    *) DIR="$1"; shift ;;
  esac
done
[ -n "$DIR" ] && [ -d "$DIR" ] || { echo "usage: prune_sermon.sh <sermon-dir> [--keep …] [--dry-run]"; exit 2; }
case ",$KEEP," in *,final,*) : ;; *) KEEP="final,$KEEP" ;; esac   # never silently drop the deliverable unless asked
has(){ case ",$KEEP," in *,"$1",*) return 0;; *) return 1;; esac; }

cd "$DIR" || exit 2
del=()
add(){ for f in "$@"; do [ -e "$f" ] && del+=("$f"); done; }

has audio   || add audio.mp3 audio.wav source.mp3 whisper.log audio.json \
                  audio.srt audio.vtt audio.tsv audio.txt emphasis_full
has source  || add *-BOOK.md
has emph    || add *-BOOK-emph.md
has html    || add *.html
has logs    || add CORRECTIONS-LOG.md SCRIPTURE-VERIFICATION.md FLAGS.md
has final   || add *-BOOK-final.md
has figures || add figure-* *.svg *.png *.jpg *.jpeg

# de-dupe; never delete the final deliverable when `final` is kept
keep_final=1; has final && keep_final=1 || keep_final=0
printf '%s\n' "${del[@]:-}" | sort -u | while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ "$keep_final" = 1 ] && case "$f" in *-BOOK-final.md) continue;; esac
  if [ "$DRY" = 1 ]; then echo "would delete: $f"; else rm -rf -- "$f" && echo "deleted: $f"; fi
done
echo "keep set: $KEEP   ($([ "$DRY" = 1 ] && echo dry-run || echo done) in $DIR)"
