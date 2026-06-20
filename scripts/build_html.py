#!/usr/bin/env python3
"""Render the sermon book-edition Markdown into a styled, book-like HTML page.
Tailored to the constrained Markdown subset this document uses."""
import re, sys, html, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_config

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not _args:
    sys.exit("usage: build_html.py <…-BOOK-emph.md> [out.html] [--review]")
SRC = pathlib.Path(_args[0])
OUT = pathlib.Path(_args[1]) if len(_args) > 1 else SRC.with_suffix(".html")
REVIEW = "--review" in sys.argv

CFG = series_config.load(SRC)
DOC_TITLE = CFG["series_title"] or "Book Edition"
BOOK_LABEL = CFG["book_label"]

text = SRC.read_text(encoding="utf-8")
lines = text.split("\n")

# --- 1. pull out footnote definitions: lines like [^id]: text ---
footnotes = {}          # id -> raw markdown text
body_lines = []
def_re = re.compile(r'^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$')
for ln in lines:
    m = def_re.match(ln)
    if m:
        footnotes[m.group(1)] = m.group(2)
    else:
        body_lines.append(ln)

# --- 2. assign footnote numbers by order of first reference in body ---
order = []
for ln in body_lines:
    for fid in re.findall(r'\[\^([A-Za-z0-9_-]+)\]', ln):
        if fid not in order:
            order.append(fid)
fn_num = {fid: i + 1 for i, fid in enumerate(order)}

def inline(s):
    s = html.escape(s, quote=False)
    # footnote refs
    def fnref(m):
        fid = m.group(1)
        n = fn_num.get(fid)
        if not n:
            return ""
        return (f'<sup class="fnref" id="fnref-{fid}">'
                f'<a href="#fn-{fid}">{n}</a></sup>')
    s = re.sub(r'\[\^([A-Za-z0-9_-]+)\]', fnref, s)
    # bold then italic
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    # ==highlight== → note-sourced material (screen-only review aid; neutralized in print).
    # Marks text merged in from the companion sermon notes so it can be eyeballed against the
    # spoken transcript. Strip the == markers at sign-off (the highlight never reaches the book).
    s = re.sub(r'==(.+?)==', r'<mark class="from-notes">\1</mark>', s)
    return s

# --- 3. block-level parse ---
out = []
i = 0
n = len(body_lines)
seen_h2 = False
in_header = False
emitted_header = False
pending_epi = False

def open_header():
    global in_header, emitted_header
    if not emitted_header:
        out.append('<header class="titleblock">')
        in_header = True
        emitted_header = True

def close_header():
    global in_header
    if in_header:
        out.append('</header>')
        in_header = False

first_para_after_h2 = False
while i < n:
    ln = body_lines[i]
    stripped = ln.strip()

    if stripped == "":
        i += 1
        continue

    # epigraph trigger comment (renders the following blockquote as an epigraph)
    if stripped == "<!-- epigraph -->":
        pending_epi = True
        i += 1
        continue
    # proof-checklist block: <!-- proof-checklist ... --> (screen-only proofing aid;
    # hidden in print, so it never reaches the final book). Each "- " line is an item.
    if stripped.startswith("<!-- proof-checklist"):
        items = []
        i += 1
        while i < n and "-->" not in body_lines[i]:
            s = body_lines[i].strip()
            if s.startswith("- "):
                items.append(s[2:].strip())
            elif s and not s.startswith("-->"):
                items.append(s.lstrip("- ").strip())
            i += 1
        if i < n:               # consume the closing -->
            i += 1
        if items:
            lis = "".join(f"<li>{inline(it)}</li>" for it in items)
            out.append(
                '<aside class="proofcheck" role="note">'
                '<p class="proofcheck-title">Proofing checklist '
                '<span>· screen only · delete from the .md before final</span></p>'
                f'<ul>{lis}</ul></aside>')
        continue
    # HTML comment (figure note) — drop
    if stripped.startswith("<!--"):
        i += 1
        continue

    # headings
    if stripped.startswith("# "):
        open_header()
        out.append(f"<h1>{inline(stripped[2:].strip())}</h1>")
        i += 1
        continue
    if stripped.startswith("### ") and not seen_h2:
        # subtitle inside the title block
        open_header()
        out.append(f'<p class="subtitle">{inline(stripped[4:].strip())}</p>')
        i += 1
        continue
    if stripped.startswith("## "):
        close_header()
        seen_h2 = True
        first_para_after_h2 = True
        out.append(f"<h2>{inline(stripped[3:].strip())}</h2>")
        i += 1
        continue
    if stripped.startswith("### "):
        out.append(f"<h3>{inline(stripped[4:].strip())}</h3>")
        i += 1
        continue
    # h4–h6 (deeper headings). House style is H2/H3, but render any deeper level rather than
    # falling through to the paragraph gatherer below, which would break on a leading "#"
    # without consuming the line and spin forever (a stray "#### " once hung the whole build).
    m_hx = re.match(r'^(#{4,6}) +(.*)$', stripped)
    if m_hx:
        lvl = len(m_hx.group(1))
        out.append(f"<h{lvl}>{inline(m_hx.group(2).strip())}</h{lvl}>")
        i += 1
        continue

    # horizontal rule / section break
    if stripped == "---":
        close_header()
        out.append('<hr class="break">')
        i += 1
        continue

    # standalone figure:  ![caption](src)   — placeholder or final image
    m_img = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
    if m_img:
        alt, src = m_img.group(1), m_img.group(2)
        is_ph = "PLACEHOLDER" in src.upper()
        fig_cls = "figure placeholder" if is_ph else "figure"
        cap = f'<figcaption>{inline(alt)}</figcaption>' if alt else ""
        out.append(f'<figure class="{fig_cls}">'
                   f'<img src="{html.escape(src, quote=True)}" '
                   f'alt="{html.escape(alt, quote=True)}">{cap}</figure>')
        i += 1
        continue

    # blockquote (possibly multi-paragraph with ">" blank lines)
    if stripped.startswith(">"):
        buf = []
        while i < n and body_lines[i].lstrip().startswith(">"):
            content = body_lines[i].lstrip()[1:]
            if content.startswith(" "):
                content = content[1:]
            buf.append(content)
            i += 1
        # split into paragraphs on blank lines
        paras, cur = [], []
        for b in buf:
            if b.strip() == "":
                if cur:
                    paras.append(" ".join(cur)); cur = []
            else:
                cur.append(b.strip())
        if cur:
            paras.append(" ".join(cur))
        bq_cls = ' class="epigraph"' if (in_header or pending_epi) else ""
        pending_epi = False
        out.append(f"<blockquote{bq_cls}>")
        for p in paras:
            out.append(f"<p>{inline(p)}</p>")
        out.append("</blockquote>")
        continue

    # paragraph: gather until blank line / block start
    buf = []
    while i < n:
        s = body_lines[i]
        st = s.strip()
        if st == "" or st.startswith(("#", ">", "---", "<!--")):
            break
        buf.append(st)
        i += 1
    # Backstop: if the very first line broke the loop (a block-marker variant not handled by
    # any branch above, e.g. "----" or "--- text"), nothing was consumed — emit it verbatim
    # and advance, so i can never stall the outer `while i < n` loop.
    if not buf:
        out.append(f"<p>{inline(body_lines[i].strip())}</p>")
        i += 1
        continue
    para = " ".join(buf)
    # detect a fully-italic standalone line in the title block (byline / note)
    if in_header and para.startswith("*") and para.endswith("*"):
        out.append(f'<p class="byline">{inline(para)}</p>')
    else:
        cls = ' class="lead"' if first_para_after_h2 else ""
        first_para_after_h2 = False
        out.append(f"<p{cls}>{inline(para)}</p>")

close_header()

# --- 4. footnotes section ---
if order:
    out.append('<section class="footnotes"><hr><ol>')
    for fid in order:
        body = inline(footnotes.get(fid, ""))
        out.append(f'<li id="fn-{fid}">{body} '
                   f'<a class="fnback" href="#fnref-{fid}">↩</a></li>')
    out.append('</ol></section>')

body_html = "\n".join(out)

CSS = """
:root{
  --ink:#211c15; --soft:#5b5345; --accent:#7a5c2e; --rule:#d9cfbc;
  --paper:#f7f3ea;
}
*{box-sizing:border-box;}
html{-webkit-text-size-adjust:100%;}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  font-size:20px; line-height:1.72; font-kerning:normal;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}
.page{max-width:39rem; margin:0 auto; padding:5rem 1.5rem 6rem;}
.titleblock{text-align:center; margin-bottom:2.5rem;}
h1{
  font-size:2.5rem; line-height:1.12; font-weight:600; margin:0 0 .9rem;
  letter-spacing:.005em;
}
.subtitle{font-size:1.04rem; color:var(--soft); font-style:italic; margin:.2rem 0;}
.byline{font-size:.92rem; color:var(--soft); font-style:italic; margin:.35rem 0;}
.titleblock .byline:last-child{
  margin-top:1.1rem; font-size:.8rem; letter-spacing:.02em;
  padding-top:1rem; border-top:1px solid var(--rule); display:inline-block;
}
h2{
  font-size:1.5rem; font-weight:600; line-height:1.2;
  margin:3rem 0 1.1rem; letter-spacing:.005em;
}
h3{
  font-size:1.06rem; font-weight:600; font-style:italic; color:var(--accent);
  margin:2rem 0 .6rem;
}
p{margin:0 0 1.15rem; hyphens:auto;}
p.lead::first-letter{
  float:left; font-size:3.4rem; line-height:.82; padding:.05em .08em 0 0;
  color:var(--accent); font-weight:600;
}
blockquote{
  margin:1.4rem 0 1.6rem; padding:.2rem 0 .2rem 1.4rem;
  border-left:3px solid var(--rule);
  color:#3c352a; font-size:.97rem; line-height:1.62;
}
blockquote p{margin:0 0 .7rem;}
blockquote p:last-child{margin-bottom:0;}
blockquote.epigraph{
  border:0; font-style:italic; color:var(--soft);
  max-width:30rem; margin:1.8rem auto 0; padding:0; text-align:left;
  font-size:.95rem; line-height:1.6;
}
strong{font-weight:700;}
figure.figure{margin:2rem 0; text-align:center;}
figure.figure img{max-width:100%; height:auto; border-radius:6px;}
figure.figure figcaption{
  font-size:.82rem; color:var(--soft); font-style:italic;
  margin-top:.6rem; line-height:1.5;
}
figure.placeholder figcaption::before{
  content:"Placeholder — "; font-style:normal; font-weight:600; color:var(--accent);
}
hr.break{
  border:0; height:1.4rem; margin:2.4rem 0; text-align:center;
}
hr.break::before{
  content:"\\2766"; color:var(--rule); font-size:1.3rem; letter-spacing:.4em;
}
sup.fnref{font-size:.62em; line-height:0; vertical-align:super;}
sup.fnref a{
  text-decoration:none; color:var(--accent); padding:0 .1em; font-weight:600;
}
.footnotes{margin-top:3.5rem; font-size:.82rem; color:var(--soft); line-height:1.55;}
.footnotes hr{border:0; border-top:1px solid var(--rule); margin-bottom:1.2rem;}
.footnotes ol{padding-left:1.2rem;}
.footnotes li{margin-bottom:.7rem;}
.fnback{text-decoration:none; color:var(--accent);}
.reviewbar{
  position:sticky; top:0; z-index:10; background:#2b2620; color:#f1ead9;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:.74rem; letter-spacing:.04em; text-align:center;
  padding:.5rem 1rem;
}
.proofcheck{
  max-width:34rem; margin:0 auto 3rem; padding:.85rem 1.1rem .9rem;
  border:1px dashed var(--rule); border-radius:7px; background:rgba(122,92,46,.05);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:.76rem; line-height:1.55; color:var(--soft);
}
.proofcheck-title{
  margin:0 0 .5rem; font-weight:700; letter-spacing:.03em;
  text-transform:uppercase; font-size:.66rem; color:var(--accent);
}
.proofcheck-title span{font-weight:400; text-transform:none; letter-spacing:0; color:var(--soft);}
.proofcheck ul{margin:0; padding:0; list-style:none;}
.proofcheck li{margin:0 0 .45rem; padding-left:1.4rem; position:relative;}
.proofcheck li:last-child{margin-bottom:0;}
.proofcheck li::before{
  content:""; position:absolute; left:0; top:.4em;
  width:.6rem; height:.6rem; border:1.5px solid var(--accent); border-radius:2px;
}
mark.from-notes{
  background:linear-gradient(transparent 55%, rgba(122,92,46,.28) 55%);
  color:inherit; padding:0 .04em; border-radius:1px;
}
.from-notes-key{
  max-width:34rem; margin:0 auto 2.4rem; padding:.6rem 1.1rem;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:.74rem; color:var(--soft); text-align:center;
}
.from-notes-key mark{font-size:.9em;}
@media print{ .proofcheck,.from-notes-key{display:none;} mark.from-notes{background:none;} }
@media (max-width:480px){ body{font-size:18px;} .page{padding:3rem 1.1rem 4rem;} h1{font-size:2rem;} }
.review em{ color:var(--accent); }
@media print{ .reviewbar{display:none;} body{background:#fff;} }
"""

doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(DOC_TITLE)} — Book Edition (review draft)</title>
<style>{CSS}</style>
</head>
<body class="{'review' if REVIEW else ''}">
<div class="reviewbar">{'REVIEW · emphasis tinted' if REVIEW else 'REVIEW DRAFT'} · {html.escape(BOOK_LABEL)}</div>
<main class="page">
{'<p class="from-notes-key">Passages <mark class="from-notes">highlighted like this</mark> are merged from the companion sermon notes (reworded to the spoken voice) — not in the delivered audio.</p>' if '==' in text else ''}
{body_html}
</main>
</body>
</html>
"""

OUT.write_text(doc, encoding="utf-8")
print(f"wrote {OUT} ({len(doc):,} bytes); {len(order)} footnotes")
