#!/usr/bin/env python3
"""Enumerate a SermonAudio series into a SERMON-MAP.tsv manifest.

The public SermonAudio API is auth-gated, so this reads the server-rendered pages instead:
the series page embeds every `/sermons/<id>` link; each sermon page's `application/ld+json`
AudioObject carries the title, preach date, and duration. Output is sorted by preach date and
numbered 01..N, with an auto-generated slug you can hand-tweak afterward.

Usage:
    python3 series_manifest.py <series-url> <out-dir> [--force]

Writes <out-dir>/SERMON-MAP.tsv. If that file already exists it writes
<out-dir>/SERMON-MAP.tsv.new instead (so hand-curated slugs are never clobbered) unless
--force is given. Columns: chapter, sermon_id, sermonaudio_url, slug, preach_date, title.
"""
import json
import os
import re
import subprocess
import sys

UA = "User-Agent: Mozilla/5.0"
STOPLEADERS = ("the-", "a-", "an-")


def curl(url):
    return subprocess.run(["curl", "-s", url, "-H", UA],
                          capture_output=True, text=True).stdout


def sermon_ids(series_html):
    """Unique /sermons/<id> in document order."""
    seen = []
    for m in re.findall(r"/sermons/(\d+)", series_html):
        if m not in seen:
            seen.append(m)
    return seen


def sermon_meta(sid):
    """(date, duration, title) from the sermon page's ld+json AudioObject (og fallback)."""
    raw = curl(f"https://www.sermonaudio.com/sermons/{sid}")
    title = date = dur = ""
    m = re.search(r'application/ld\+json">(.*?)</script>', raw, re.S)
    if m:
        try:
            for n in json.loads(m.group(1)).get("@graph", []):
                if n.get("@type") == "AudioObject":
                    date = (n.get("uploadDate", "") or "")[:10]
                    dur = n.get("duration", "") or ""
                    title = n.get("name", "") or title
        except Exception:
            pass
    if not title:
        mt = re.search(r'property="og:title" content="([^"]*)"', raw)
        if mt:
            import html as _h
            title = _h.unescape(mt.group(1))
    return date, dur, title


def slugify(title):
    s = title.lower().replace("&", " and ").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    for lead in STOPLEADERS:
        if s.startswith(lead):
            s = s[len(lead):]
            break
    words = s.split("-")
    # keep it short but whole-word: cap ~6 words / 45 chars
    out = []
    for w in words:
        if not w:
            continue
        if out and len("-".join(out + [w])) > 45:
            break
        out.append(w)
        if len(out) >= 6:
            break
    return "-".join(out) or "untitled"


def main():
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv
    if len(args) != 2:
        sys.exit("usage: series_manifest.py <series-url> <out-dir> [--force]")
    series_url, out_dir = args

    ids = sermon_ids(curl(series_url))
    if not ids:
        sys.exit(f"no /sermons/<id> links found at {series_url} (wrong URL, or page changed?)")
    sys.stderr.write(f"found {len(ids)} sermons; fetching metadata…\n")

    rows = []
    for sid in ids:
        date, dur, title = sermon_meta(sid)
        rows.append({"sid": sid, "date": date, "dur": dur, "title": title})
    rows.sort(key=lambda r: (r["date"] or "9999", r["sid"]))

    used = {}
    out = ["\t".join(["chapter", "sermon_id", "sermonaudio_url", "slug", "preach_date", "title"])]
    for i, r in enumerate(rows, 1):
        body = slugify(r["title"])
        n = used.get(body, 0) + 1
        used[body] = n
        if n > 1:
            body = f"{body}-{n}"
        slug = f"{i:02d}-{body}"
        url = f"https://www.sermonaudio.com/sermons/{r['sid']}"
        out.append("\t".join([f"{i:02d}", r["sid"], url, slug, r["date"], r["title"]]))

    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, "SERMON-MAP.tsv")
    if os.path.exists(dest) and not force:
        dest = os.path.join(out_dir, "SERMON-MAP.tsv.new")
        sys.stderr.write("SERMON-MAP.tsv exists — wrote SERMON-MAP.tsv.new (diff/merge; or rerun --force)\n")
    with open(dest, "w") as f:
        f.write("\n".join(out) + "\n")

    print("\n".join(out))
    sys.stderr.write(f"\nwrote {dest} ({len(rows)} chapters)\n")


if __name__ == "__main__":
    main()
