#!/usr/bin/env python3
"""Fetch exact verse text from BibleHub for Scripture verification (Step 4).

Don't trust a transcript's quote wording — verify every quotation against the speaker's
versions before rendering a blockquote. This pulls a clean verse range from BibleHub for any
version slug it hosts (e.g. nasb77, kjv, nasb, esv, niv, nkjv), handling the poetry layout
(verses split across <br> lines) that a naive scrape mangles.

Usage:
    python3 bible_fetch.py <version> <book> <chapter> [verses]
    python3 bible_fetch.py nasb77 isaiah 40 1-11
    python3 bible_fetch.py kjv haggai 2 1-9
    python3 bible_fetch.py nasb77 1_corinthians 15 24-25     # underscores for spaces
    python3 bible_fetch.py nasb77 psalms 23                  # whole chapter

Book names: lowercase, underscore for spaces ("1_corinthians", "song_of_solomon"); Psalms is
"psalms". `verses` is N, N-M, or a comma list (1-3,9,11). Divine name prints as BibleHub sets
it; render small-caps LORD/GOD as CAPS and OT-in-NT quotes ALL-CAPS per house style. (Rarely a
BibleHub section header abuts the last verse of a range, e.g. "…blood of Abel. The Unshaken
Kingdom"; just eyeball/trim the trailing header.)
"""
import html
import re
import subprocess
import sys


# Public-domain versions come back clean from bible-api.com (JSON); copyrighted ones
# (nasb77, esv, niv, …) only live on BibleHub, whose poetry layout we parse below.
BIBLE_API = {"kjv", "web", "webbe", "bbe", "oeb-us", "oeb-cw", "clementine", "almeida", "rccv"}


def chapter_api(version, book, ch):
    ref = f"{book.replace('_', '+')}+{ch}"  # plus-encode spaces; a literal space breaks the URL
    raw = subprocess.run(
        ["curl", "-s", f"https://bible-api.com/{ref}?translation={version}&verse_numbers=false"],
        capture_output=True, text=True).stdout
    import json
    try:
        data = json.loads(raw)
    except Exception:
        sys.exit(f"bible-api: could not fetch {version} {book} {ch}")
    out = {}
    for v in data.get("verses", []):
        out[int(v["verse"])] = re.sub(r"\s+", " ", v["text"]).strip()
    if not out:
        sys.exit(f"bible-api returned no verses for {version} {book} {ch}")
    return out


def chapter(version, book, ch):
    if version in BIBLE_API:
        return chapter_api(version, book, ch)
    url = f"https://biblehub.com/{version}/{book}/{ch}.htm"
    raw = subprocess.run(["curl", "-s", url, "-H", "User-Agent: Mozilla/5.0"],
                         capture_output=True, text=True).stdout
    start = raw.find(f"{book}/{ch}-1.htm")
    if start == -1:
        sys.exit(f"no verses found at {url} (bad version/book/chapter, or layout changed?)")
    seg = raw[start - 60:]
    # cut the footer / cross-reference apparatus that follows the chapter text
    for stop in ("Treasury of Scripture", "Cross References", 'class="cross"',
                 "New American Standard", "King James Bible", "<!-- "):
        j = seg.find(stop)
        if j > 500:
            seg = seg[:j]
            break
    parts = re.split(r'<span class="reftext"><a href="[^"]*?/(\d+)-(\d+)\.htm"><b>\d+</b></a></span>', seg)
    out = {}
    for k in range(1, len(parts) - 2, 3):
        vno = int(parts[k + 1])
        text = parts[k + 2]
        t = re.sub(r"<br\s*/?>", " ", text)
        t = re.sub(r"<[^>]+>", "", t)
        t = html.unescape(t).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        out[vno] = t
    return out


def parse_verses(spec):
    want = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            want |= set(range(int(a), int(b) + 1))
        else:
            want.add(int(part))
    return want


def main():
    if len(sys.argv) < 4:
        sys.exit("usage: bible_fetch.py <version> <book> <chapter> [verses]")
    version, book, ch = sys.argv[1], sys.argv[2], sys.argv[3]
    data = chapter(version, book, ch)
    verses = sorted(parse_verses(sys.argv[4])) if len(sys.argv) > 4 else sorted(data)
    for v in verses:
        if v in data:
            print(f"{v}. {data[v]}")


if __name__ == "__main__":
    main()
