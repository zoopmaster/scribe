#!/usr/bin/env python3
"""Series consistency linter for scribe sermon book editions (any speaker, any series).

Checks every chapter's curated `…-BOOK-emph.md` against the series' own conventions —
the front-matter pattern from the layered config (title, speaker byline, scripture note) and
*cross-chapter* consistency (a reused figure must keep one caption; a cited book must keep
one publisher/year form). Nothing speaker- or series-specific is hard-coded here; the engine
is shared and only `speaker.config` / `series.config` + the SERIES-*.md files change.

Usage:  python3 scripts/lint_series.py                 # every series under CWD
        python3 scripts/lint_series.py <series-or-chapter-dir> …
FAIL → exit 1 (structural); WARN → drift to reconcile. Run after each wave, before commit.
"""
import sys, re, glob, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_config

YEAR = re.compile(r"\b(1[6-9]\d{2}|20\d{2})\b")
PARENS_W_YEAR = re.compile(r"\(([^()]*(?:1[6-9]\d{2}|20\d{2})[^()]*)\)")

def chapters_of(series_root):
    return sorted(glob.glob(str(pathlib.Path(series_root) / "*" / "SERMON-*-BOOK-emph.md")))

def lint_chapter(path, cfg):
    fails, warns = [], []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    prose = re.sub(r"<!-- proof-checklist.*?-->", "", text, flags=re.S)  # screen-only meta

    # --- front matter (driven by series.config) ---
    title = cfg.get("series_title", "")
    if title:
        if f"# {title}" not in lines:
            fails.append(f'H1 "# {title}" missing (series_title)')
    elif not any(l.startswith("# ") for l in lines):
        fails.append("H1 title line missing")
    if not any(l.startswith("### ") and l[4:].strip() for l in lines):
        fails.append("subtitle (### …) missing")
    speaker = re.escape(cfg.get("speaker", ""))
    if speaker and not any(re.match(rf"^\*{speaker} · on .+\*$", l) for l in lines):
        fails.append(f'byline *{cfg["speaker"]} · on <ref>* missing/malformed')
    note = cfg.get("scripture_note", "")
    if note and note not in text:
        fails.append("scripture-note line missing or altered")

    # --- epigraph + checklist ---
    if "<!-- epigraph -->" not in text:
        warns.append("no closing-epigraph trigger (<!-- epigraph -->)")
    if "<!-- proof-checklist" not in text:
        warns.append("no proof-checklist block (ok only if signed off)")

    # --- flag discipline: ⚑ lives ONLY in the proof-checklist block, never in the body ---
    if "⚑" in prose:
        fails.append("flag marker ⚑ in body — flags belong in the proof-checklist block only")

    # --- smart quotes (book prose only) ---
    if '"' in prose:
        warns.append(f'{prose.count(chr(34))} straight double-quote(s) — run smartquotes.py')
    return fails, warns

def cross_chapter(files):
    """General consistency: a reused figure → one caption; a cited book → one pub/year form."""
    warns = []
    fig_caps, book_forms = {}, {}
    for f in files:
        for ln in pathlib.Path(f).read_text(encoding="utf-8").split("\n"):
            m = re.match(r"^!\[(.*?)\]\((.*?)\)$", ln.strip())          # standalone figure
            if m:
                fig_caps.setdefault(m.group(2), set()).add(m.group(1))
            fn = re.match(r"^\[\^[A-Za-z0-9_-]+\]:\s*(.*)$", ln)         # footnote def
            if fn:
                defn = fn.group(1)
                t = re.search(r"\*([^*]+)\*", defn)
                for paren in PARENS_W_YEAR.findall(defn):               # pub/year parentheticals
                    if t:
                        book_forms.setdefault(t.group(1).strip(" ,."), set()).add(paren.strip())
    for src, caps in fig_caps.items():
        if len(caps) > 1:
            warns.append(f'figure "{src}" has {len(caps)} different captions across the series')
    for title, forms in book_forms.items():
        if len(forms) > 1:
            warns.append(f'"{title}" cited with {len(forms)} different publisher/year forms: '
                         + " | ".join(sorted(forms)))
    return warns

def main():
    args = sys.argv[1:]
    roots = []
    if args:
        for a in args:
            c = series_config.find_config(a)
            if c:
                roots.append(str(c.parent))
            else:
                print(f"lint_series: no series.config at/above {a}")
    else:
        roots = sorted({str(pathlib.Path(c).parent) for c in glob.glob("**/series.config", recursive=True)})
        if pathlib.Path("series.config").is_file():
            roots.append(".")
    roots = sorted(set(roots))
    if not roots:
        print("lint_series: no series.config found"); return 1

    total_f = total_w = 0
    for root in roots:
        cfg = series_config.load(root)
        files = chapters_of(root)
        print(f"\n=== series: {cfg.get('series_title') or root}  ({len(files)} chapter[s]) ===")
        for f in files:
            p = pathlib.Path(f)
            fails, warns = lint_chapter(p, cfg)
            total_f += len(fails); total_w += len(warns)
            status = "FAIL" if fails else ("WARN" if warns else "PASS")
            print(f"[{status}] {p.parent.name}")
            for x in fails: print(f"   FAIL  {x}")
            for x in warns: print(f"   warn  {x}")
        xw = cross_chapter(files)
        total_w += len(xw)
        for x in xw: print(f"[warn] (series) {x}")
    print(f"\n{total_f} fail, {total_w} warn")
    return 1 if total_f else 0

if __name__ == "__main__":
    sys.exit(main())
