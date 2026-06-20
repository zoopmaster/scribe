#!/usr/bin/env bash
# Build the single-file review HTML, then print it to one PDF via headless Chrome.
# Chrome honors @page size/margins and CSS page breaks; no extra install needed.
set -euo pipefail

SCRIPTDIR="$(cd "$(dirname "$0")" && pwd)"
SERIES_DIR="${1:?usage: build_book_pdf.sh <series-dir>}"
SERIES_DIR="$(cd "$SERIES_DIR" && pwd)"
HTML="$SERIES_DIR/REVIEW-BOOK.html"
# PDF name from the series folder (e.g. covenants-of-promise -> Covenants-Of-Promise-REVIEW.pdf)
SLUG="$(basename "$SERIES_DIR")"
TITLE="$(echo "$SLUG" | awk -F- '{for(i=1;i<=NF;i++){$i=toupper(substr($i,1,1)) substr($i,2)}}1' OFS=-)"
PDF="$SERIES_DIR/${TITLE}-REVIEW.pdf"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

python3 "$SCRIPTDIR/build_book.py" "$SERIES_DIR" "$HTML"

"$CHROME" --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$PDF" "file://$HTML" 2>/dev/null

echo "wrote $PDF"
ls -la "$PDF"
