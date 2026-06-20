#!/usr/bin/env python3
"""Produce the final Markdown deliverable from a curated `…-BOOK-emph.md`.

Sign-off step: strips the screen-only `<!-- proof-checklist … -->` block and any other HTML
comment triggers (e.g. `<!-- epigraph -->`), then appends a Scripture-permissions footer with
the copyright notice for the chapter's default Bible version plus any alternate version that is
actually cited in the text. Writes `…-BOOK-final.md` (the deliverable); the curated emph.md
stays the editable source.

Usage:  finalize.py <…-BOOK-emph.md> [out.md]
"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import series_config, bible_permissions

if len(sys.argv) < 2:
    sys.exit("usage: finalize.py <…-BOOK-emph.md> [out.md]")
SRC = pathlib.Path(sys.argv[1])
if len(sys.argv) > 2:
    OUT = pathlib.Path(sys.argv[2])
else:
    stem = SRC.name[:-3]  # drop .md
    stem = stem[:-5] + "-final" if stem.endswith("-emph") else stem + "-final"
    OUT = SRC.with_name(stem + ".md")

CFG = series_config.load(SRC)
text = SRC.read_text(encoding="utf-8")

# 1. strip the proof-checklist block and any remaining HTML comments (epigraph trigger, notes)
text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
# collapse the blank-line runs the stripped comments leave behind
text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

# 2. which versions to credit: the default (always) + any alternate actually cited.
default = CFG.get("bible_version", "").strip()
used = []
def _add(label):
    if label and label not in used:
        used.append(label)
_add(default)
# any known version tagged in a citation, e.g. "(Acts 20:27, KJV)" or "(…, ESV)"
known = {k for k in [default, CFG.get("alt_version", "")] if k}
for _key, (disp, _t) in bible_permissions.NOTICES.items():
    known.add(disp)
known.add(CFG.get("alt_version", ""))
for label in list(known):
    if not label:
        continue
    token = re.escape(label)
    if re.search(rf",\s*{token}\s*\)", text) or re.search(rf"\b{token}\b", text):
        _add(label)
# only credit versions we actually cited beyond the default: keep default + cited alts
alt = CFG.get("alt_version", "").strip()
used = [v for v in used if v == default or v == alt or
        re.search(rf",\s*{re.escape(v)}\s*\)", text)]

# 3. build the footer
notices = []
for v in used:
    n = bible_permissions.notice(v, SRC)
    if n:
        notices.append((n[0], n[1]))
if notices:
    foot = ["", "---", "", "### Scripture permissions", ""]
    for disp, body in notices:
        foot.append(f"*{body}*")
        foot.append("")
    text = text.rstrip() + "\n" + "\n".join(foot).rstrip() + "\n"

OUT.write_text(text, encoding="utf-8")
creds = ", ".join(d for d, _ in notices) if notices else "none"
print(f"wrote {OUT} — permissions: {creds}")
