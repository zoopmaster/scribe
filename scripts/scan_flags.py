#!/usr/bin/env python3
"""Surface candidate flag sites by scanning a draft against the speaker's flag-terms watchlist.

A NON-DESTRUCTIVE filter: it never edits and never decides — it greps the speaker's
`flag-terms.tsv` (walk-up resolved) against a chapter draft and lists every hit with line
number and context, so the editorial pass (Step 3) can judge each one against the speaker's
profile rules and raise a flag where warranted. The watchlist is review prompts, not a
blocklist.

`flag-terms.tsv` lines:  category<TAB>term-or-regex<TAB>note    (`#` comments, blanks ignored)
Categories are the agnostic flag taxonomy (SENSITIVE, ATTRIBUTION, VERSION, …).

Usage:  scan_flags.py <chapter-dir-or-.md-file> [speaker-or-series-root]
Exit 0 always; prints "no watchlist hits" when clean.
"""
import re, sys, pathlib

def _watchlist(start):
    p = pathlib.Path(start).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        f = d / "flag-terms.tsv"
        if f.is_file():
            rows = []
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    cat, term = parts[0].strip(), parts[1].strip()
                    note = parts[2].strip() if len(parts) > 2 else ""
                    rows.append((cat, term, note))
            return rows, f
    return [], None

def _target(arg):
    p = pathlib.Path(arg)
    if p.is_file():
        return p
    # prefer the curated emph draft, then the book md, then the raw transcript
    for pat in ("*-BOOK-emph.md", "*-BOOK.md", "audio.txt"):
        hits = sorted(p.glob(pat))
        if hits:
            return hits[0]
    return None

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: scan_flags.py <chapter-dir-or-.md> [speaker-or-series-root]")
    target = _target(sys.argv[1])
    if not target:
        print(f"scan_flags: no draft found at {sys.argv[1]}"); return 0
    root = sys.argv[2] if len(sys.argv) > 2 else target
    rows, src = _watchlist(root)
    if not rows:
        print("scan_flags: no flag-terms.tsv watchlist found (nothing to scan)"); return 0

    lines = target.read_text(encoding="utf-8").splitlines()
    total = 0
    print(f"scan: {target}   watchlist: {src}")
    for cat, term, note in rows:
        try:
            rx = re.compile(term, re.I)
        except re.error:
            rx = re.compile(re.escape(term), re.I)
        for i, ln in enumerate(lines, 1):
            if rx.search(ln):
                total += 1
                ctx = ln.strip()
                if len(ctx) > 100:
                    m = rx.search(ln)
                    a = max(0, m.start() - 40); ctx = "…" + ln[a:m.end() + 40].strip() + "…"
                tail = f"  — {note}" if note else ""
                print(f"  [{cat}] line {i}: {ctx}{tail}")
    print(f"{total} watchlist hit(s) — judge each against SPEAKER-PROFILE.md; flag or keep.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
