#!/usr/bin/env python3
"""Combine every chapter's …-BOOK-emph.md into ONE minimal HTML for the pastor's
review PDF: each chapter starts on a new page, and each chapter keeps its own
proof-checklist at the top — visible in print, with real (printable) checkboxes.

Deliberately plain: Times New Roman body, Arial headings/checklist, black on white.
No drop caps, fleurons, or tinted paper. Render to PDF with build_book_pdf.sh.

Usage: python3 scripts/build_book.py <SERIES_DIR> [OUT.html]
  e.g.  build_book.py covenants-of-promise  ->  covenants-of-promise/REVIEW-BOOK.html
"""
import re, sys, html, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_config

if len(sys.argv) < 2:
    sys.exit("usage: build_book.py <SERIES_DIR> [OUT.html]")
SERIES_DIR = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else SERIES_DIR / "REVIEW-BOOK.html"

# Title + speaker from the layered config (series.config over speaker.config).
_CFG = series_config.load(SERIES_DIR)
SERIES_TITLE = _CFG.get("series_title") or SERIES_DIR.name.replace("-", " ").title()
SPEAKER = _CFG.get("speaker", "")


def chapter_files():
    """All …-BOOK-emph.md, ordered by the SERMON-NN number in the filename."""
    files = []
    for p in SERIES_DIR.glob("*/SERMON-*-BOOK-emph.md"):
        m = re.search(r"SERMON-(\d+)-", p.name)
        if m:
            files.append((int(m.group(1)), p))
    return [p for _, p in sorted(files)]


def inline(s, fn_num=None, idp=""):
    """Escape + bold/italic. If fn_num given, also resolve [^id] footnote refs."""
    s = html.escape(s, quote=False)
    if fn_num is not None:
        def fnref(m):
            fid = m.group(1)
            n = fn_num.get(fid)
            if not n:
                return ""
            return (f'<sup class="fnref" id="fnref-{idp}{fid}">'
                    f'<a href="#fn-{idp}{fid}">{n}</a></sup>')
        s = re.sub(r'\[\^([A-Za-z0-9_-]+)\]', fnref, s)
    else:
        s = re.sub(r'\[\^([A-Za-z0-9_-]+)\]', "", s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    return s


def render_chapter(src, idp):
    """Render one emph.md file to an HTML chapter fragment.
    idp = per-chapter id prefix so footnote ids don't collide across chapters."""
    ch_dir = src.parent.name
    text = src.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 1. pull footnote definitions
    footnotes, body_lines = {}, []
    def_re = re.compile(r'^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$')
    for ln in lines:
        m = def_re.match(ln)
        if m:
            footnotes[m.group(1)] = m.group(2)
        else:
            body_lines.append(ln)

    # 2. number footnotes by first reference
    order = []
    for ln in body_lines:
        for fid in re.findall(r'\[\^([A-Za-z0-9_-]+)\]', ln):
            if fid not in order:
                order.append(fid)
    fn_num = {fid: i + 1 for i, fid in enumerate(order)}

    def fix_src(s):
        s = s.strip()
        if re.match(r'^[a-z]+://', s) or s.startswith("/"):
            return s
        return f"{ch_dir}/{s}"

    out, i, n = [], 0, len(body_lines)
    seen_h2 = False
    in_header = emitted_header = False
    pending_epi = False
    first_para_after_h2 = False
    kicker_done = False

    def open_header():
        nonlocal in_header, emitted_header
        if not emitted_header:
            out.append('<header class="titleblock">')
            in_header, emitted_header = True, True

    def close_header():
        nonlocal in_header
        if in_header:
            out.append('</header>')
            in_header = False

    while i < n:
        stripped = body_lines[i].strip()
        if stripped == "":
            i += 1
            continue

        if stripped == "<!-- epigraph -->":
            pending_epi = True
            i += 1
            continue

        # proof-checklist -> VISIBLE checkbox list at the top of the chapter
        if stripped.startswith("<!-- proof-checklist"):
            items = []
            i += 1
            while i < n and "-->" not in body_lines[i]:
                s = body_lines[i].strip()
                if s.startswith("- "):
                    items.append(s[2:].strip())
                elif s:
                    items.append(s.lstrip("- ").strip())
                i += 1
            if i < n:
                i += 1
            if items:
                lis = "".join(f"<li>{inline(it)}</li>" for it in items)
                out.append(
                    '<aside class="proofcheck" role="note">'
                    '<p class="proofcheck-title">Proofing checklist — items to confirm</p>'
                    f'<ul>{lis}</ul></aside>')
            continue

        if stripped.startswith("<!--"):   # figure note etc. — drop
            i += 1
            continue

        # title block: "# series title" -> small kicker; first "### …" -> chapter title
        if stripped.startswith("# "):
            open_header()
            out.append(f'<p class="kicker">{inline(stripped[2:].strip())}</p>')
            i += 1
            continue
        if stripped.startswith("### ") and not seen_h2 and not kicker_done:
            open_header()
            kicker_done = True
            out.append(f'<h1>{inline(stripped[4:].strip())}</h1>')
            i += 1
            continue
        if stripped.startswith("## "):
            close_header()
            seen_h2 = True
            first_para_after_h2 = True
            out.append(f'<h2>{inline(stripped[3:].strip(), fn_num, idp)}</h2>')
            i += 1
            continue
        if stripped.startswith("### "):
            out.append(f'<h3>{inline(stripped[4:].strip(), fn_num, idp)}</h3>')
            i += 1
            continue
        if stripped.startswith("#### "):
            out.append(f'<h4>{inline(stripped[5:].strip(), fn_num, idp)}</h4>')
            i += 1
            continue

        if stripped == "---":
            close_header()
            out.append('<hr class="break">')
            i += 1
            continue

        m_img = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
        if m_img:
            alt, srcv = m_img.group(1), fix_src(m_img.group(2))
            cap = f'<figcaption>{inline(alt)}</figcaption>' if alt else ""
            out.append(f'<figure><img src="{html.escape(srcv, quote=True)}" '
                       f'alt="{html.escape(alt, quote=True)}">{cap}</figure>')
            i += 1
            continue

        if stripped.startswith(">"):
            buf = []
            while i < n and body_lines[i].lstrip().startswith(">"):
                content = body_lines[i].lstrip()[1:]
                if content.startswith(" "):
                    content = content[1:]
                buf.append(content)
                i += 1
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
                out.append(f"<p>{inline(p, fn_num, idp)}</p>")
            out.append("</blockquote>")
            continue

        # paragraph — always consume the current line first so an unhandled
        # token (e.g. a heading level we don't render) can never stall the loop
        buf = [stripped]
        i += 1
        while i < n:
            st = body_lines[i].strip()
            if st == "" or st.startswith(("#", ">", "---", "<!--")):
                break
            buf.append(st)
            i += 1
        para = " ".join(buf)
        if in_header and para.startswith("*") and para.endswith("*"):
            out.append(f'<p class="byline">{inline(para)}</p>')
        else:
            first_para_after_h2 = False
            out.append(f'<p>{inline(para, fn_num, idp)}</p>')

    close_header()

    if order:
        out.append('<section class="footnotes"><hr><ol>')
        for fid in order:
            body = inline(footnotes.get(fid, ""), fn_num, idp)
            out.append(f'<li id="fn-{idp}{fid}">{body} '
                       f'<a class="fnback" href="#fnref-{idp}{fid}">&#8617;</a></li>')
        out.append('</ol></section>')

    return '<section class="chapter">\n' + "\n".join(out) + '\n</section>'


CSS = """
@page { size: Letter; margin: 1in; }
* { box-sizing: border-box; }
body {
  font-family: "Times New Roman", Times, serif;
  font-size: 12pt; line-height: 1.5; color: #000; background: #fff;
  margin: 0;
}
h1, h2, h3, h4, .kicker, .byline, .proofcheck, figcaption, .footnotes {
  font-family: Arial, Helvetica, sans-serif;
}
.titlepage { text-align: center; page-break-after: always; padding-top: 2.5in; }
.titlepage .series { font-family: Arial, Helvetica, sans-serif; font-size: 28pt; font-weight: bold; margin: 0 0 .4in; }
.titlepage .sub { font-size: 14pt; font-style: italic; margin: 0 0 1.6in; }
.titlepage .meta { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; color: #000; line-height: 1.7; }
.chapter { page-break-before: always; }
.titleblock { margin-bottom: 2rem; }
.kicker { font-size: 10pt; letter-spacing: .08em; text-transform: uppercase; margin: 0 0 .15in; color: #000; }
h1 { font-size: 19pt; font-weight: bold; line-height: 1.2; margin: 0 0 .12in; }
.byline { font-size: 11pt; font-style: italic; margin: .05in 0; }
h2 { font-size: 14pt; font-weight: bold; margin: .35in 0 .12in; page-break-after: avoid; }
h3 { font-size: 12pt; font-weight: bold; font-style: italic; margin: .25in 0 .08in; page-break-after: avoid; }
h4 { font-size: 11pt; font-weight: bold; margin: .2in 0 .06in; page-break-after: avoid; }
p { margin: 0 0 .12in; text-align: left; orphans: 2; widows: 2; }
blockquote { margin: .15in 0 .15in .35in; padding-left: .2in; border-left: 2px solid #000;
  font-size: 11pt; line-height: 1.4; }
blockquote p { margin: 0 0 .08in; }
blockquote.epigraph { border: 0; font-style: italic; padding: 0; margin: .2in 0 0; }
hr.break { border: 0; text-align: center; margin: .2in 0; }
hr.break::before { content: "* * *"; letter-spacing: .3em; }
figure { text-align: center; margin: .2in 0; page-break-inside: avoid; }
figure img { max-width: 100%; height: auto; }
figcaption { font-size: 9.5pt; font-style: italic; margin-top: .06in; }
sup.fnref { font-size: .7em; line-height: 0; }
sup.fnref a { text-decoration: none; color: #000; }
.footnotes { margin-top: .4in; font-size: 10pt; line-height: 1.35; page-break-inside: avoid; }
.footnotes hr { border: 0; border-top: 1px solid #000; width: 2in; margin: 0 0 .12in; }
.footnotes ol { padding-left: .25in; margin: 0; }
.footnotes li { margin-bottom: .08in; }
.fnback { text-decoration: none; color: #000; }

/* Proofing checklist — visible in print, real checkboxes (not bullets). */
.proofcheck { border: 1px solid #000; padding: .14in .18in; margin: 0 0 .3in;
  page-break-inside: avoid; font-size: 10.5pt; line-height: 1.4; }
.proofcheck-title { font-weight: bold; font-size: 10pt; text-transform: uppercase;
  letter-spacing: .05em; margin: 0 0 .1in; }
.proofcheck ul { list-style: none; margin: 0; padding: 0; }
.proofcheck li { position: relative; padding-left: .32in; margin: 0 0 .1in; }
.proofcheck li:last-child { margin-bottom: 0; }
.proofcheck li::before { content: ""; position: absolute; left: 0; top: .02in;
  width: .16in; height: .16in; border: 1.5px solid #000; background: #fff; }
"""


def main():
    chapters = chapter_files()
    if not chapters:
        sys.exit(f"No …-BOOK-emph.md files under {SERIES_DIR}")

    parts = []
    for idx, src in enumerate(chapters, 1):
        parts.append(render_chapter(src, idp=f"c{idx:02d}-"))

    titlepage = (
        '<section class="titlepage">'
        f'<p class="series">{html.escape(SERIES_TITLE)}</p>'
        '<p class="sub">Book Edition &middot; Review Draft</p>'
        f'<p class="meta">{html.escape(SPEAKER)}<br>'
        f'{len(chapters)} chapters<br><br>'
        'For pastoral review &middot; checkboxes mark items to confirm</p>'
        '</section>'
    )

    doc = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        f'<title>{html.escape(SERIES_TITLE)} — Review Draft</title>\n'
        f'<style>{CSS}</style>\n</head>\n<body>\n'
        + titlepage + "\n"
        + "\n".join(parts)
        + "\n</body>\n</html>\n"
    )
    OUT.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} — {len(chapters)} chapters, {len(doc):,} bytes")


if __name__ == "__main__":
    main()
