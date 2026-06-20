# scribe

A speaker-agnostic pipeline that turns a **sermon or theological lecture** into a finished,
typeset **book-edition chapter** — installable as a Claude Code plugin.

Give it a SermonAudio URL (or a local audio file) plus the speaker and series name. It then:

1. **Transcribes** the audio (mlx-whisper, Apple GPU, large-v3, word-level timestamps).
2. **Revises** the transcript faithfully in the speaker's own voice (a medium dial — smooths
   for a reader, keeps the rhetoric).
3. **Bookifies** it — strips oral deixis, converts handout references into figure pointers,
   derives headings from the speaker's own numbered points, and **flags** sensitive/uncertain
   material for review (see below).
4. **Cites Scripture** — verifies every quotation against the speaker's default Bible version,
   switches versions where his exposition leans on specific wording.
5. **Marks spoken emphasis** — detects acoustic prominence from the word timestamps and
   italicizes the prose peaks.
6. **Finalizes** to one **Markdown** deliverable (`…-BOOK-final.md`) with a Scripture-permissions
   footer for the versions used. (An HTML preview is available but optional.)

The engine and the skill are **generic**. Everything speaker- or series-specific lives in the
*data* project beside the audio — never in this plugin.

## How it's layered

Config resolves by walking up from a chapter file: `DEFAULTS < speaker.config < series.config`.

| Layer | Lives in | Holds |
|-------|----------|-------|
| **Speaker** | project root | `speaker.config` (name, Bible version + lookup URL, whisper-prompt base) and `SPEAKER-PROFILE.md` — the voice / version / sensitivity ledger |
| **Series** | each series folder | `series.config` (title, numbering, proper-noun seed) and `SERIES-*.md` precedent files |
| **Sermon** | each chapter folder | the audio, the Markdown drafts, the per-sermon audit logs |

`SPEAKER-PROFILE.md` is a **ledger**: every misheard-name fix, version quirk, and sensitivity
call gets appended, so later chapters — and parallel drafting agents — resolve them the same
way. By a speaker's third sermon the profile is dense enough that new chapters draft as cheaply
as an established one.

## Install

```sh
claude plugin marketplace add ~/Projects/scribe     # or: github:zoopmaster/scribe
claude plugin install scribe@scribe
```

Restart Claude Code. The `scribe` skill loads automatically and triggers on a sermonaudio.com
link or phrases like "sermon to book", "book edition", "next sermon".

## Usage

Hand the skill the audio plus the speaker and series name — it does the setup itself:

- **New speaker** → scaffolds the project root (`speaker.config` + `SPEAKER-PROFILE.md`) from
  `templates/`.
- **New series** → creates the series folder with its `series.config` and seeds `SERIES-DECISIONS.md`.
- **Existing speaker/series** → reads the config + ledgers and continues.

## Output & retention

The deliverable is **one Markdown file**, `…-BOOK-final.md` — emphasis as `*italics*`, scripture
as blockquotes, `[^footnotes]`, `![figures]()`, all portable to any Markdown reader or
typesetter. `finalize.py` produces it from the curated source at sign-off and appends the
Scripture-permissions footer.

Two outputs are **opt-in and never assumed** — the skill asks, and the answer can be saved to
`speaker.config` so a batch isn't re-asked:

- **HTML preview** (`preview: ask | yes | no`) — a styled, book-like HTML rendering. When on, the
  edit hook keeps it fresh; when never generated, the hook leaves it alone.
- **Retention** (`keep: ask | final | final+html | all`) — a finished sermon dir accumulates
  audio, transcripts, intermediate Markdown, and logs. `prune_sermon.sh` keeps only what you
  choose (the final md + figures by default) and removes the rest, including the original audio.
  It always supports `--dry-run`, and the skill previews the deletion list before acting.

## Flags & permissions

Sensitive or uncertain material runs through an agnostic **flag process**. The categories are
fixed (`SENSITIVE`, `ATTRIBUTION`, `VERSION`, `BYLINE`, `TRUNCATION`, `GRAPHIC`, `WORDING`); the
triggers and the reword/keep decision for a given speaker come from that speaker's profile. A
non-destructive watchlist (`flag-terms.tsv` + `scan_flags.py`) surfaces candidates for the
editorial pass to judge; raised flags go into the screen-only proof-checklist and a durable
per-sermon `FLAGS.md`, and `lint_series.py` fails any flag marker that leaks into the body.

Bible-copyright notices are appended automatically at finalize, keyed by version
(`bible_permissions.py`, override per speaker via `bible-permissions.tsv`). Verify the notice
against the publisher's current wording before sending a book to print.

## Layout

```
scribe/
  .claude-plugin/   plugin.json + marketplace.json
  skills/scribe/    SKILL.md — the method (the editorial judgment you perform)
  scripts/          the engine — speaker-agnostic, config-driven
  hooks/            on_book_edit.sh + hooks.json (refresh an existing HTML preview on edit)
  templates/        speaker.config, SPEAKER-PROFILE.md, series.config, sections.tsv,
                    FLAGS.md, flag-terms.tsv
```

### The engine

| Script | Does |
|--------|------|
| `series_config.py` | layered config resolver (`speaker.config` over `series.config`) |
| `transcribe.sh` / `transcribe_local.sh` | mlx-whisper transcription (URL or local file) with repetition-collapse guard |
| `apply_emphasis.py` | acoustic-prominence emphasis detector → curated `…-BOOK-emph.md` |
| `scan_flags.py` | grep the speaker's `flag-terms.tsv` watchlist → flag candidates (non-destructive) |
| `finalize.py` | strip screen-only blocks + append permissions → `…-BOOK-final.md` (the deliverable) |
| `bible_permissions.py` | canonical Bible-version copyright notices |
| `build_html.py` | optional styled HTML preview of a chapter (opt-in) |
| `prune_sermon.sh` | keep only chosen artifacts (audio/intermediates removed); `--dry-run` first |
| `build_index.py` | series contents page (optional grouping via `sections.tsv`) |
| `build_book.py` / `build_book_pdf.sh` | combined review HTML → PDF |
| `smartquotes.py` | straight → curly typographic quotes, in place |
| `lint_series.py` | front-matter + cross-chapter consistency lint (+ flag-leak check) |

## A speaker project (the consumer)

```
<speaker-project>/            # e.g. a private "axehead-press" repo
  speaker.config              # speaker, bible_version, bible_url_base, alt_version, whisper base
  SPEAKER-PROFILE.md          # voice tics, version policy, sensitivity taxonomy, name ledger
  <series>/
    series.config             # series_title, numbered, whisper_prompt (+ series nouns)
    SERIES-DECISIONS.md …     # standing rulings / registry / house style (as they accrue)
    sections.tsv              # optional contents grouping for build_index.py
    NN-slug/                  # one sermon: …-BOOK-final.md (deliverable) + (pre-prune) audio.*,
                              # …-BOOK.md, …-BOOK-emph.md, FLAGS.md, logs
```

Per-series batch runners (e.g. `batch_transcribe_*.sh`) stay in the data project and call this
plugin's `scripts/` via `${CLAUDE_PLUGIN_ROOT:-$HOME/Projects/scribe}/scripts`.

## Editing the engine

This repo is the source of truth; the installed plugin is a cached copy. After editing, refresh
the cache. Bump the `version` in `.claude-plugin/plugin.json` + `marketplace.json`, commit, then:

```sh
claude plugin marketplace update scribe     # re-read this local marketplace
claude plugin update scribe                 # pull the new version
```

If a refresh ever reports "not found" (e.g. the version was unchanged), reinstall:

```sh
claude plugin uninstall scribe@scribe
claude plugin marketplace update scribe
claude plugin install scribe@scribe
```

Restart Claude Code (or reload) so the updated skill and hooks load.

## Requirements

macOS with an Apple-silicon GPU is assumed for the transcription engine (`mlx-whisper`,
`whisper-large-v3-mlx`), plus `ffmpeg` and `yt-dlp`. CPU `whisper medium.en` is the fallback
floor. Rendering and linting are pure Python 3 with no third-party dependencies.
