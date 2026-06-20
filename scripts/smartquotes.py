#!/usr/bin/env python3
"""Convert straight quotes to curly typographic quotes in the book Markdown,
in place. Leaves Markdown syntax and already-curly characters untouched."""
import pathlib, sys

# Smarten EVERY file passed (was: only argv[1] — so `smartquotes.py BOOK.md emph.md`
# silently skipped emph.md, the render source; that shipped straight quotes in ch.36).
paths = [pathlib.Path(a) for a in sys.argv[1:]]
if not paths:
    sys.exit("usage: smartquotes.py <file.md> [file.md …]")

OPENERS = set(' \t\n([{“‘—–-/')   # chars before an OPENING quote
for p in paths:
    text = p.read_text(encoding="utf-8")
    out = []
    prev = '\n'
    for c in text:
        if c == '"':
            out.append('“' if (prev in OPENERS) else '”')
        elif c == "'":
            if prev.isalnum():            # apostrophe / possessive / contraction
                out.append('’')
            elif prev in OPENERS:
                out.append('‘')
            else:
                out.append('’')
        else:
            out.append(c)
        prev = out[-1]
    p.write_text("".join(out), encoding="utf-8")
    straight = "".join(out).count('"') + "".join(out).count("'")
    print(f"smartened {p}; remaining straight quotes: {straight}")
