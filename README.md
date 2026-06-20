# scribe

A speaker-agnostic pipeline that turns a sermon or theological lecture into a finished,
typeset book-edition chapter: transcribe → revise in the speaker's voice → bookify → cite
Scripture → mark spoken emphasis → render styled HTML.

The engine and the `scribe` skill are generic. Everything speaker-specific lives in the
*data* project beside the audio, not in this plugin:

- `speaker.config` + `SPEAKER-PROFILE.md` — speaker-wide knobs and the voice/version/
  sensitivity ledger (project root).
- `series.config` + `SERIES-*.md` — per-series knobs and precedent (each series folder).

Config resolves by walking up from a chapter: `DEFAULTS < speaker.config < series.config`.

## Install

```sh
claude plugin marketplace add ~/Projects/scribe
claude plugin install scribe@scribe
```

Restart Claude Code; the `scribe` skill loads automatically. Give it a SermonAudio URL or a
local audio file plus the speaker and series name, and it does the rest (Step 0 scaffolds a
new speaker/series from `templates/`).

## Layout

```
scribe/
  .claude-plugin/   plugin.json + marketplace.json
  skills/scribe/    SKILL.md (the method)
  scripts/          the engine (transcribe, emphasis, render, lint, config)
  hooks/            on_book_edit.sh + hooks.json (rebuild HTML on edit)
  templates/        speaker.config, SPEAKER-PROFILE.md, series.config, sections.tsv
```

## A speaker project (the consumer)

```
<speaker-project>/            # e.g. axehead-press
  speaker.config              # speaker, bible_version, bible_url_base, alt_version, whisper base
  SPEAKER-PROFILE.md          # voice tics, version policy, sensitivity taxonomy, name ledger
  <series>/
    series.config             # series_title, numbered, whisper_prompt (+ series nouns)
    SERIES-DECISIONS.md …     # standing rulings / registry / style (as they accrue)
    sections.tsv              # optional contents grouping for build_index.py
    NN-slug/                  # one sermon: audio.*, …-BOOK.md, …-BOOK-emph.md, logs
```

Per-series batch runners (e.g. `batch_transcribe_*.sh`) stay in the data project; they call
this plugin's `scripts/`.

## Editing the engine

Edit here, then refresh the installed copy:

```sh
claude plugin update scribe
```
