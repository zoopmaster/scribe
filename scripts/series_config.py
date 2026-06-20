#!/usr/bin/env python3
"""Layered config for the scribe sermon-to-book pipeline (speaker-agnostic engine).

Two config layers, both resolved by **walking up** from any chapter/file path:

  speaker.config   — speaker-wide knobs (name, scripture defaults, whisper-prompt base,
                     Bible version + lookup URL). Lives in the speaker's project root.
  series.config    — per-series knobs (series_title, numbered, whisper_prompt, …). Lives
                     in each series folder, beside its `SERIES-*.md` convention files and
                     `NN-slug/` chapter dirs.

Precedence:  DEFAULTS  <  speaker.config  <  series.config  (most specific wins).
One engine serves every speaker and series; only the config files change.

CLI:  python3 series_config.py <path> [key]    # print one value, or all key: value
"""
import sys, pathlib

# Neutral defaults. A speaker.config supplies the speaker-wide values; a series.config
# overrides per-series. Nothing here is speaker-specific.
DEFAULTS = {
    "series_title": "",     # the H1 / book title; "" → standalone sermon (H1 = its own title)
    "numbered": "true",     # true → chapters are "Part N — …" style installments
    "speaker": "",          # byline name
    "scripture_note": "",   # front-matter note, e.g. "*…NASB (1977) unless marked.*"
    "book_label": "Book edition",
    "whisper_prompt": "",   # proper-noun seed for transcription (speaker base + series nouns)
    "bible_version": "",    # default version label, e.g. "NASB 1977"
    "bible_url_base": "",   # lookup base for verification, e.g. "https://biblehub.com/nasb77"
    "alt_version": "",      # alternate version to switch to, e.g. "KJV"
}


def find_up(start, name):
    """Nearest `name` file at or above `start` (walking up the tree); None if absent."""
    p = pathlib.Path(start).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        c = d / name
        if c.is_file():
            return c
    return None


def find_config(start):
    """Backward-compatible: locate the nearest series.config (the series root marker)."""
    return find_up(start, "series.config")


def _merge(cfg, path):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        cfg[k.strip()] = v.strip()


def load(start="."):
    cfg = dict(DEFAULTS)
    sp = find_up(start, "speaker.config")
    if sp:
        _merge(cfg, sp)
        cfg["_speaker_root"] = str(sp.parent)
    se = find_up(start, "series.config")
    if se:
        _merge(cfg, se)
        cfg["_root"] = str(se.parent)
    return cfg


if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "."
    cfg = load(start)
    if len(sys.argv) > 2:
        print(cfg.get(sys.argv[2], ""))
    else:
        for k, v in cfg.items():
            print(f"{k}: {v}")
