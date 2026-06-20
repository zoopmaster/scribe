#!/usr/bin/env python3
"""Build a single navigation page (index.html) for a series folder: one styled, book-like
contents page linking every chapter's …-BOOK-emph.html, optionally grouped into sections.

Usage: build_index.py <series-dir>
Reuses the chapter pages' visual theme; reproducible — just re-run after adding chapters.

Sections are optional and series-specific: place a `sections.tsv` in the series folder with
one `lo<TAB>hi<TAB>Section name` line per group (inclusive chapter-number ranges). Any
chapter not covered by a section is still listed under "Other" — nothing is ever dropped.
With no sections.tsv, the contents is a single flat list.
"""
import re, sys, html, glob, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_config

if len(sys.argv) < 2:
    sys.exit("usage: build_index.py <series-dir>")
SERIES = pathlib.Path(sys.argv[1])

CFG = series_config.load(SERIES)
SERIES_TITLE = CFG.get("series_title") or SERIES.name.replace("-", " ").title()
SPEAKER = CFG.get("speaker", "")

# section groupings from <series>/sections.tsv (inclusive ranges): "lo<TAB>hi<TAB>name".
# Absent → no sections (flat list). Nothing is ever dropped (see the "Other" fallback below).
def _sections(series):
    f = series / "sections.tsv"
    out = []
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                out.append((int(parts[0]), int(parts[1]), parts[2].strip()))
    return out

SECTIONS = _sections(SERIES)

chapters = {}   # num -> (subtitle, byline, href, words)
total_words = 0
for d in sorted(glob.glob(str(SERIES / "[0-9][0-9]-*"))):
    dp = pathlib.Path(d)
    num = int(dp.name[:2])
    emph = glob.glob(str(dp / "SERMON-*-BOOK-emph.md"))
    src = glob.glob(str(dp / "SERMON-*-BOOK.md"))
    if not emph or not src:
        continue
    md = open(emph[0]).read()
    body = re.sub(r"<!--.*?-->", "", open(src[0]).read(), flags=re.S)
    sub = re.search(r"^###\s+(.*)$", md, flags=re.M)
    by = re.search(r"·\s*on\s+(.*?)\*", md)
    words = len(re.findall(r"\b[\w'’-]+\b", body))
    total_words += words
    href = str(pathlib.Path(emph[0]).with_suffix(".html").relative_to(SERIES))
    title = (sub.group(1).strip() if sub else dp.name)
    byline = (by.group(1).strip() if by else "")
    chapters[num] = (title, byline, href, words)

# split "Part N — Title" into label + title. Split ONLY on the em-dash separator (— or its
# en-dash variant), never on a plain hyphen — otherwise hyphenated ordinals like
# "Part Twenty-Three" truncate to "Part Twenty" and the leftover mangles the title.
def split_title(t):
    m = re.match(r"(Part .+?)\s*[—–]\s+(.*)", t)
    return (m.group(1).strip(), m.group(2).strip()) if m else ("", t)

def _li(n):
    title, byline, href, words = chapters[n]
    part, name2 = split_title(title)
    return (f'<li><a href="{html.escape(href, quote=True)}">'
            f'<span class="part">{html.escape(part)}</span>'
            f'<span class="ctitle">{html.escape(name2)}</span>'
            f'<span class="cmeta">{html.escape(byline)}'
            f'<span class="cwords">· {words:,} words</span></span></a></li>')

rows = []
emitted = set()
for lo, hi, name in SECTIONS:
    nums = [n for n in range(lo, hi + 1) if n in chapters]
    if not nums:
        continue
    rows.append(f'<h2 class="sect">{html.escape(name)}</h2>')
    rows.append('<ol class="toc">')
    for n in nums:
        rows.append(_li(n)); emitted.add(n)
    rows.append('</ol>')

# fallback: every chapter present but not placed by a section (or no sections defined) —
# never silently drop a chapter from the contents.
leftover = [n for n in sorted(chapters) if n not in emitted]
if leftover:
    if SECTIONS:
        rows.append('<h2 class="sect">Other</h2>')
    rows.append('<ol class="toc">')
    for n in leftover:
        rows.append(_li(n))
    rows.append('</ol>')

toc_html = "\n".join(rows)
nchap = len(chapters)

CSS = """
:root{--ink:#211c15;--soft:#5b5345;--accent:#7a5c2e;--rule:#d9cfbc;--paper:#f7f3ea;}
*{box-sizing:border-box;}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
 font-size:20px;line-height:1.6;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.page{max-width:41rem;margin:0 auto;padding:5rem 1.5rem 6rem;}
.titleblock{text-align:center;margin-bottom:1.4rem;}
h1{font-size:2.6rem;line-height:1.1;font-weight:600;margin:0 0 .6rem;}
.subtitle{font-size:1.05rem;color:var(--soft);font-style:italic;margin:.2rem 0;}
.meta{font-size:.82rem;color:var(--soft);letter-spacing:.02em;margin-top:1rem;
 padding-top:1rem;border-top:1px solid var(--rule);display:inline-block;}
h2.sect{font-size:1.18rem;font-weight:600;color:var(--accent);
 margin:2.6rem 0 .3rem;padding-bottom:.35rem;border-bottom:1px solid var(--rule);letter-spacing:.01em;}
ol.toc{list-style:none;margin:0;padding:0;}
ol.toc li{margin:0;}
ol.toc a{display:block;text-decoration:none;color:var(--ink);
 padding:.7rem .6rem;border-radius:6px;border:1px solid transparent;transition:background .12s,border-color .12s;}
ol.toc a:hover{background:rgba(122,92,46,.07);border-color:var(--rule);}
.part{display:inline-block;min-width:8.6rem;font-size:.8rem;color:var(--accent);
 font-variant:small-caps;letter-spacing:.04em;vertical-align:baseline;}
.ctitle{font-size:1.02rem;font-weight:600;}
.cmeta{display:block;margin:.15rem 0 0 8.6rem;font-size:.82rem;color:var(--soft);font-style:italic;}
.cwords{font-style:normal;margin-left:.5rem;color:#9b8f78;}
.foot{margin-top:3.5rem;padding-top:1.2rem;border-top:1px solid var(--rule);
 font-size:.8rem;color:var(--soft);text-align:center;line-height:1.6;}
@media (max-width:520px){
 body{font-size:18px;}.page{padding:3rem 1.1rem 4rem;}h1{font-size:2rem;}
 .part{display:block;min-width:0;}.cmeta{margin-left:0;}
}
"""

doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(SERIES_TITLE)} — Contents</title>
<style>{CSS}</style>
</head>
<body>
<main class="page">
<header class="titleblock">
<h1>{html.escape(SERIES_TITLE)}</h1>
<p class="subtitle">{html.escape(SPEAKER + " · ") if SPEAKER else ""}book edition</p>
<p class="meta">{nchap} chapters · {total_words:,} words</p>
</header>
{toc_html}
<p class="foot">Each chapter opens its own page. Review draft — proofing checklists are screen-only and hidden in print.</p>
</main>
</body>
</html>
"""

out = SERIES / "index.html"
out.write_text(doc, encoding="utf-8")
print(f"wrote {out} — {nchap} chapters, {total_words:,} words")
