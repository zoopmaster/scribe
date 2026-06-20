#!/usr/bin/env python3
"""Canonical copyright / permission notices for Bible versions, keyed by version label.

Speaker-agnostic data. `finalize.py` appends the notice for a chapter's default version plus
any alternate actually cited. A speaker project may override or add notices with a
`bible-permissions.tsv` at its root: one `version<TAB>notice` line per version (walk-up
resolved), which takes precedence over the shipped text below.

NOTE: publishers revise their required wording; verify the notice against the current
publisher statement before sending a book to print.

CLI:  bible_permissions.py <version>            # print one notice ("" if unknown)
      bible_permissions.py --list               # list known version labels
"""
import sys, re, pathlib

# Keyed by a normalized token (see _norm). Display labels carry the year/edition.
NOTICES = {
    "NASB1977": ("New American Standard Bible (1977)",
        "Scripture quotations taken from the New American Standard Bible®, "
        "Copyright © 1960, 1962, 1963, 1968, 1971, 1972, 1973, 1975, 1977 by The Lockman "
        "Foundation. Used by permission. www.Lockman.org"),
    "NASB1995": ("New American Standard Bible (1995)",
        "Scripture quotations taken from the New American Standard Bible®, "
        "Copyright © 1960, 1962, 1963, 1968, 1971, 1972, 1973, 1975, 1977, 1995 by The "
        "Lockman Foundation. Used by permission. www.Lockman.org"),
    "NASB2020": ("New American Standard Bible (2020)",
        "Scripture quotations taken from the New American Standard Bible®, "
        "Copyright © 1960, 1971, 1977, 1995, 2020 by The Lockman Foundation. Used by "
        "permission. www.Lockman.org"),
    "KJV": ("King James Version",
        "Scripture quotations marked KJV are from the King James Version, which is in the "
        "public domain in the United States. (In the United Kingdom the KJV is under "
        "perpetual Crown copyright, administered by Cambridge University Press.)"),
    "ESV": ("English Standard Version",
        "Scripture quotations are from the ESV® Bible (The Holy Bible, English Standard "
        "Version®), copyright © 2001 by Crossway, a publishing ministry of Good News "
        "Publishers. Used by permission. All rights reserved."),
    "NIV": ("New International Version",
        "Scripture quotations taken from The Holy Bible, New International Version®, NIV®. "
        "Copyright © 1973, 1978, 1984, 2011 by Biblica, Inc.® Used by permission. All "
        "rights reserved worldwide."),
    "NKJV": ("New King James Version",
        "Scripture taken from the New King James Version®. Copyright © 1982 by Thomas "
        "Nelson. Used by permission. All rights reserved."),
    "CSB": ("Christian Standard Bible",
        "Scripture quotations marked CSB are taken from the Christian Standard Bible®, "
        "Copyright © 2017 by Holman Bible Publishers. Used by permission."),
}


def _norm(label):
    """'NASB 1977' / 'nasb-1977' / 'NASB1977' → 'NASB1977'; 'KJV' → 'KJV'."""
    return re.sub(r"[^A-Za-z0-9]", "", (label or "")).upper()


def _overrides(start):
    """Per-speaker bible-permissions.tsv (walk-up): {normalized version: (label, notice)}."""
    out = {}
    p = pathlib.Path(start).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        f = d / "bible-permissions.tsv"
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.lstrip().startswith("#") or "\t" not in line:
                    continue
                ver, notice = line.split("\t", 1)
                out[_norm(ver)] = (ver.strip(), notice.strip())
            break
    return out


def notice(label, start="."):
    """(display_label, notice_text) for a version, honoring per-speaker overrides; or None."""
    key = _norm(label)
    ov = _overrides(start)
    if key in ov:
        return ov[key]
    if key in NOTICES:
        disp, text = NOTICES[key]
        return (label.strip() or disp, text)
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        for k, (disp, _) in NOTICES.items():
            print(f"{k}\t{disp}")
    elif len(sys.argv) > 1:
        n = notice(sys.argv[1])
        print(n[1] if n else "")
    else:
        sys.exit(__doc__)
