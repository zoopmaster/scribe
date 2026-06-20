---
name: scribe
description: Turn a sermon or theological lecture (SermonAudio URL or local audio, optionally with companion notes) into a finished, typeset book-edition chapter — transcribe, revise in the speaker's voice, bookify, cite Scripture, mark spoken emphasis, and render styled HTML. Speaker- and series-agnostic; all speaker specifics live in a per-speaker SPEAKER-PROFILE.md + speaker.config. Use when the user gives a SermonAudio URL or asks to "transcribe", "make a book edition / chapter", or "do the next sermon". Triggers: a sermonaudio.com link, "sermon to book", "book edition", "next sermon", "sermon NN".
---

# scribe

Converts one sermon (or theological lecture) into a book chapter. Most steps are editorial
judgment you perform; four mechanical steps use the bundled engine scripts. The engine is
**speaker- and series-agnostic** — every speaker-specific decision lives in that speaker's
`SPEAKER-PROFILE.md` (the voice/version/sensitivity ledger) and `speaker.config` (machine
knobs); every series-specific decision lives in the series' `series.config` + `SERIES-*.md`.

**Resolve the engine first.** The scripts live in this plugin:
```
SCRIBE="${CLAUDE_PLUGIN_ROOT:-$HOME/Projects/scribe}"   # scripts in $SCRIBE/scripts
```

**Project layout.** A *speaker project* is one repo/folder holding `speaker.config` +
`SPEAKER-PROFILE.md` at its root and one folder per series under it; each series folder holds
`series.config`, its `SERIES-*.md`, and `NN-slug/` chapter dirs. Config resolves by walking
up from the chapter: `DEFAULTS < speaker.config < series.config`.
```
<speaker-project>/
  speaker.config   SPEAKER-PROFILE.md
  <series>/
    series.config  SERIES-*.md  sections.tsv(optional)
    NN-slug/   (one sermon: audio.*, …-BOOK.md, …-BOOK-emph.md, logs)
```

Standing decisions are FIXED unless the user overrides them. Keep two audit logs per sermon:
`CORRECTIONS-LOG.md` and `SCRIPTURE-VERIFICATION.md`.

**Report the substantive Steps 2–4 issues back to the user — never fix silently.** Surface in
your reply: name/publication corrections, version calls, paraphrase-kept-as-his decisions,
dropped/unverifiable attributions, cut digressions, **referenced handouts / charts /
graphics**, and heading/byline/epigraph judgment calls. **Do NOT report basic Scripture
normalizations** (restoring the default version's wording, a dropped word, a transcription
stumble inside a quote) or purely mechanical smoothing — those stay log-only. The logs are
the durable record; the report is the short list of calls the user actually needs to review.

## Inputs
- **Audio (required)** — either a SermonAudio URL *or* a local audio file (mp3/wav).
  - **URL:** get title/speaker/date from the page's og: tags
    (`curl -s <url> -H 'User-Agent: Mozilla/5.0' | grep og:`); WebFetch is 403'd.
  - **Local file (the batch case):** `$SCRIBE/scripts/transcribe_local.sh <audio-file> <out-dir>`
    does the whole local-file path (copy → `audio.mp3`, `ffmpeg` → wav, mlx-whisper,
    `cp audio.json emphasis_full/`).
- The user hands you the audio (a file, a directory, or a URL) and **names the speaker + the
  series** — you do all the setup (Step 0). Derive number/title/date/reading from the
  filename or page.
- Optional: a companion epub of notes. Some notes were skipped in delivery — MERGE both
  sources, using the transcript as the spine and inserting epub-only material in his wording;
  flag conflicts rather than silently picking one.

## Step 0 — Locate or set up speaker + series (automatic; the user only names them)
Never make the user configure anything — given the audio + who said it + the series it
belongs to, set it all up yourself.
- **New speaker →** scaffold the speaker project root: copy `$SCRIBE/templates/speaker.config`
  and `$SCRIBE/templates/SPEAKER-PROFILE.md`, fill in name, default Bible version + lookup
  base + alternate, the whisper-prompt base, and whatever voice/sensitivity you can infer.
  The profile is a ledger — it fills in as you process more of this speaker.
- **New series →** create `<series>/` and write `<series>/series.config` from the template:
  `series_title` (the book/series title the user named) and `whisper_prompt` (the speaker base
  **plus this series' key proper nouns / book names** you can infer from its subject). Standalone
  (non-series) sermon → leave `series_title` empty (H1 = the sermon's own title) and set
  `numbered: false`. Seed `<series>/SERIES-DECISIONS.md` with the standing rulings + that
  proper-noun list; add `SERIES-REGISTRY.md` / `SERIES-STYLE.md` only once recurring elements
  or series-specific style choices actually appear.
- **Existing speaker/series →** read `speaker.config` + `SPEAKER-PROFILE.md` and the series'
  `series.config` + `SERIES-*.md` and continue.
- Each sermon lives in `<series>/NN-slug/`. **Trust a `CP##`-style filename over SermonAudio
  titles/numbers** when they're known to be misaligned; confirm with a ~90s probe if a URL is
  ambiguous.
The shared `scripts/` never change between speakers; only the config + `*-PROFILE.md` /
`SERIES-*.md` do.

## Step 1 — Transcribe (script)
```
$SCRIBE/scripts/transcribe_local.sh <audio-file> <series>/NN-slug   # local mp3 (batch) — mlx large-v3
$SCRIBE/scripts/transcribe.sh       <url>        <series>/NN-slug   # SermonAudio URL — same engine
```
Engine is **mlx-whisper (Apple GPU) at `mlx-community/whisper-large-v3-mlx`** — ~10x realtime
on an M3 Max (a 1-hr sermon in ~6 min, word timestamps included). Produces
`audio.{txt,srt,json,tsv,vtt}` + `emphasis_full/audio.{wav,json}`. Proper nouns are seeded via
`whisper_prompt` in the series' `series.config` (override per run with `WHISPER_PROMPT=…`).
(Override the model with `MLX_WHISPER_MODEL=…`; CPU `whisper medium.en` is the fallback floor.)
For a batch, transcription can run ahead in the background while the editorial passes
(Steps 2–7) pipeline behind it.
**Transcript trust (batch safety) — confirm BEFORE editing.** Two independent failures, one
gate each: (a) **engine collapse** — mlx large-v3 can repetition-collapse on a long tape (one
phrase looped for the rest of it); `transcribe_local.sh` gates this (retry hotter, then flag) —
trust the transcript only if it passed (no single line ≥25%). (b) **wrong source** — verify the
audio actually IS the sermon you think it is; a `~90s` probe + filename/title check. Never run
Steps 2–7 on a transcript that failed either check.

## Step 2 — Faithful revision (MEDIUM dial)
Tighten run-ons and smooth transitions for a reader; remove spoken artifacts (false starts,
filler, doubled words). **KEEP the speaker's voice — the tics listed in `SPEAKER-PROFILE.md`**
(direct address, rhetorical repetition, rhetorical questions, em-dash asides). Fix only clear
transcription errors; verify any name/quote — Whisper phonetics lie. Log every non-obvious fix
in `CORRECTIONS-LOG.md` **and report it back** (see the reporting rule above) — don't silently
fix. Append confirmed misheard-name fixes to the profile's name-fix ledger.

## Step 3 — Bookify
Strip oral deixis: "turn in your hymnals", page numbers, "tonight"/"this evening",
week/Sunday scheduling, and personal congregation asides. **Cut dated topical digressions** —
do NOT preserve them as footnotes; log the cut.
**Handouts / charts / graphics — BUBBLE UP; KEEP his description + pointer.** The graphics ARE
included in the book (the user creates and inserts them), so his words about a visual aid are
not throwaway deixis. When he describes and points to one: **keep his description and his
pointers** — only adapt the oral handout reference ("in your outline you'll find…") into a
reader-facing pointer ("you can see in this chart…"). Then **report the graphic** and **insert
a visible placeholder image** where it goes: a standalone
`![<his description, as caption>](figure-<slug>-PLACEHOLDER.svg)` line, with a matching
`figure-<slug>-PLACEHOLDER.svg` in the sermon dir. `build_html.py` renders `![alt](src)` as a
`<figure>`; a src containing `PLACEHOLDER` gets a "Placeholder —" caption tag and dashed
styling. Put the detailed build spec in `CORRECTIONS-LOG.md`. Never prose-ify away his
description or silently drop a referenced graphic. **If a later chapter re-references a graphic
introduced earlier**, REUSE the same placeholder file + caption rather than minting a new one,
and report the reuse. Convert series talk to chapter talk.
**Sensitive material — the keep/flag taxonomy is speaker-tuned; read the speaker's
`SPEAKER-PROFILE.md`** (and any series-local override in `SERIES-DECISIONS.md`). Apply its
rules: reword + reintegrate flagged categories in his voice (keep his point) and add a
`⚑ REWORDED — review wording` item — `⚑` lives in the `<!-- proof-checklist -->` block ONLY,
NEVER inline in the body. Keep-as-exposition categories stay, no flag, do NOT soften. Named
figures: a **famous** one → KEEP; a **non-famous** one → reword + flag.
Derive H2/H3 **headings from his own numbered points** ("first major point… secondly… now
finally") — never a generic template. **Byline = his actual recorded Scripture reading**
("on <Book c:v>") whenever one is captured — the text he reads out to open the sermon; only
fall back to an editorial pick when NO reading is recorded. Do NOT prefer a "thematic/dramatic
center" over a recorded reading. Opening and closing prayers become **mirrored epigraphs** (use
the `<!-- epigraph -->` trigger before the closing one; drop "Let us pray:"). **If the recording
starts mid-stream** and no opening prayer was captured, use only the closing epigraph — never
fabricate an opening one. **If the recording cuts off mid-closing-prayer,** complete only an
unmistakable liturgical/covenant closure (e.g. "…for us, and for our children. Amen.") and flag
it — never invent beyond the obvious.

## Step 4 — Scripture & citations
- **Verify every quotation** against the speaker's default version: `<bible_url_base>/<book>/<ch>.htm`
  (`bible_url_base` from `speaker.config`, e.g. `https://biblehub.com/nasb77`), cross-checked
  against the alternate version. Don't trust memory for verse text.
- **Version rule:** default to `bible_version`; switch a quote to the **alternate (`alt_version`)**
  when his surrounding exposition leans on words specific to it (the profile lists the tells). If
  he cites the alternate, keep it and tag it — never silently convert.
- **Direct quote** → quotation/blockquote + plain `(Book c:v)`; tag the non-default version as
  `(…, <alt_version>)`. Front matter states the default "unless marked" (the `scripture_note`).
- **Simulated / dramatized speech — quotation marks, NO citation, NEVER italics.** When he
  voices God speaking, a hypothetical person, the congregation's imagined reply, or a composite
  "God said…" not tied to one verse → wrap it in **quotation marks (roman)**. It is invented
  dramatization, so **do not cite it**. Reserve *italics* for emphasis, word-as-word, and titles.
- **Paraphrase of an actual verse** → quotation marks (roman), cited by *closeness*: if **close
  to the verse, just colloquialized**, use `(see Book c:v)`; if **very loose**, don't cite at
  all. Never italicize the paraphrase unless he stressed a word in it.
- **Name/publication corrections:** you MAY fix a misheard proper noun or title, but only with a
  **citable source** — cite it in `CORRECTIONS-LOG.md` and append to the profile's name ledger.
- **Unverifiable attributions:** don't make them. Drop the name + footnote, keep his wording. If
  a named source's exact quote can't be found, keep his words; don't pad with biography.
- Non-biblical sources that ARE solid → numbered footnotes. **Footnotes are source citations
  ONLY** — neutral bibliographic form **with specific page numbers, verified, never invented**;
  a whole-book recommendation with no quoted passage stays a full-book ref. The book is wholly
  the speaker's first-person voice: never write third-person editorial notes, and never footnote
  an aside.
- Record verified quotes, divergences, and small-caps (OT-in-NT) spots in `SCRIPTURE-VERIFICATION.md`.

## Step 5 — Emphasis (script)
```
$SCRIBE/scripts/apply_emphasis.py            # default top 3% (Sparse); arg = top-% knob
```
Detects acoustic prominence (loudness, drawn-out duration, autocorrelation pitch, pause) from
the word timestamps, keeps **Sparse** peaks (one per sentence, phrases collapsed, litany
repetition suppressed, ubiquitous theme words demoted), aligns to the book text, and italicizes
prose only (never scripture). Writes `…-BOOK-emph.md`. It's a **proposal layer** (~half land,
half you prune) and is BLIND to reverent-hush emphasis — add those by ear (the profile lists the
speaker's hush patterns). The curated `…-BOOK-emph.md` is the **source of truth** for the render;
re-running this script OVERWRITES your curation, so run it once up front, then prune by hand.

## Step 6 — Render (script)
```
$SCRIBE/scripts/build_html.py <…-BOOK-emph.md> <…-BOOK-emph.html>   # the ONE deliverable (book view)
```
**One HTML only** — the emphasized book view. (`--review` makes a tinted copy if you want one
while editing; it is NOT a deliverable, and neither is a non-emph `…-BOOK.html`.) Smart quotes:
`$SCRIBE/scripts/smartquotes.py <file.md>`. The PostToolUse hook rebuilds `…-BOOK-emph.html`
when you edit `…-BOOK-emph.md`; it does NOT re-run apply_emphasis (that would clobber curation)
and builds no review/base HTML.

## Step 7 — Proofing checklist (in the render, screen-only)
Put the **same substantive Steps 2–4 calls you report back** into a `<!-- proof-checklist … -->`
block at the **very top of `…-BOOK-emph.md`**, above the `# ` title. `build_html.py` renders it
as a subtle **static to-check list** at the top of the article — a *bullet* list, NOT interactive
checkboxes. It is `@media print`-hidden, so it can never reach the final book, and it is
**deleted from the `.md` at sign-off**. Each `- ` line is one item; lead each with a **bold tag**
for the call (e.g. name/version/byline/graphic/truncation/wording decision).
```
<!-- proof-checklist
- **Byline:** used X; his recorded reading was Y. Decide.
- **Truncated closing prayer:** completed "…Amen." — confirm.
-->
# The Series Title
```

## Step 8 — Series + speaker consistency (makes parallel drafting safe)
`series.config` holds the per-series knobs; `speaker.config` holds the speaker-wide ones;
neutral defaults live in `$SCRIBE/scripts/series_config.py`. `build_html.py`, `lint_series.py`,
and the transcribe scripts resolve them by **walking up** from the chapter. **Using this for a
new speaker = a new project folder with its own `speaker.config` + `SPEAKER-PROFILE.md`; a new
series = a new folder with its own `series.config` (+ `SERIES-*.md`); nothing in this skill or
the scripts changes.**

Speaker- and series-*specific* conventions do NOT belong in this skill — they live with the
data so every chapter and every parallel wave shares the same precedent:
- `SPEAKER-PROFILE.md` — voice, version policy, sensitivity taxonomy, proper-noun seed, name-fix
  ledger (speaker-wide).
- `SERIES-STYLE.md` = house style; `SERIES-REGISTRY.md` = canonical wording of recurring quotes /
  figures / footnote forms; `SERIES-DECISIONS.md` = standing rulings, borderline keep/cut
  precedents, proper-noun seed list (series-local).
- **Read the profile + all present `SERIES-*.md` before drafting**, and **reuse** the registry's
  canonical renderings verbatim.
- **Seed the transcription prompt** from the ledgers' proper-noun lists.
- **Append** any new borderline call, name fix, or recurring element to the right ledger so later
  chapters resolve it the same way.
- After each chapter — and especially after a parallel wave — run `$SCRIBE/scripts/lint_series.py`
  and reconcile any drift (front-matter, byline, footnote/figure forms, smart quotes) **before
  committing**.
Without this shared precedent, parallel agents re-derive judgment independently and drift; with
it, parallel ≈ serial. (If no such files exist yet, distill them from the finished chapters first.)

## Deliverables per sermon
`…-BOOK.md` (source), `…-BOOK-emph.md` (curated) + `…-BOOK-emph.html` (the one render),
`audio.*`, `emphasis_full/audio.json`, `CORRECTIONS-LOG.md`, `SCRIPTURE-VERIFICATION.md`.
Commit them. Run `$SCRIBE/scripts/lint_series.py` clean first.
