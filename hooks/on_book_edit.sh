#!/usr/bin/env bash
# PostToolUse hook (scribe): when a sermon book .md is edited, smart-quote it; and when the
# curated -BOOK-emph.md is edited, rebuild the single deliverable HTML. Never re-runs
# apply_emphasis (it would clobber hand-curated emphasis) and builds no review/base HTML.
# Reads the tool-call JSON on stdin; exits 0 silently for any edit that is not a sermon book
# file inside a scribe series (one with a series.config at/above it).
set -uo pipefail
input=$(cat)
fp=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null || true)

# Only sermon book markdown: SERMON-NN-…-BOOK.md / -BOOK-emph.md
case "$(basename "$fp")" in
  SERMON-*-BOOK*.md) : ;;
  *) exit 0 ;;
esac
[ -f "$fp" ] || exit 0

# Engine: the installed plugin's scripts, or the dev repo as a fallback.
SCR="${CLAUDE_PLUGIN_ROOT:-$HOME/Projects/scribe}/scripts"
[ -d "$SCR" ] || exit 0

# Guard: only act when the file sits inside a scribe series (series.config at/above it).
python3 "$SCR/series_config.py" "$fp" series_title >/dev/null 2>&1 || exit 0
python3 - "$fp" "$SCR" <<'PY' || exit 0
import sys, pathlib
sys.path.insert(0, sys.argv[2])
import series_config
sys.exit(0 if series_config.find_config(sys.argv[1]) else 1)
PY

dir=$(dirname "$fp"); base=$(basename "$fp" .md)
cd "$dir" || exit 0

python3 "$SCR/smartquotes.py" "$fp" >/dev/null 2>&1 || true

# HTML is an OPTIONAL preview, never assumed: only REFRESH a preview that already exists.
# If the editor never generated a preview for this chapter, the hook makes none. Editing the
# -BOOK.md source smart-quotes it but does NOT rebuild HTML and does NOT re-run apply_emphasis.
case "$fp" in
  *-BOOK-emph.md)
    [ -f "$base.html" ] && python3 "$SCR/build_html.py" "$fp" "$base.html" >/dev/null 2>&1
    : ;;
esac
exit 0
