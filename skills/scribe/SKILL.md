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
- **Audio (required)** — a SermonAudio **series** URL, a single SermonAudio **sermon** URL,
  *or* a local audio file (mp3/wav).
  - **Series URL** (`/series/<id>`): the public API is auth-gated, so enumerate from the
    server-rendered pages — `$SCRIBE/scripts/series_manifest.py <series-url> <series-dir>` does
    it: it scrapes the embedded `/sermons/<id>` links + each sermon's ld+json (title, preach
    date, duration), sorts by date, auto-slugifies, and writes `<series-dir>/SERMON-MAP.tsv`
    (chapter, sermon_id, url, slug, date, title). It won't clobber an existing map (writes
    `.tsv.new`; `--force` to overwrite). **Hand-tweak the auto-slugs**, then process chapters
    from the map (pilot one first, then batch — confirm scope).
  - **Sermon URL:** get title/speaker/date from the page's og: tags
    (`curl -s <url> -H 'User-Agent: Mozilla/5.0' | grep og:`); WebFetch is 403'd. The page's
    `application/ld+json` also carries SermonAudio's **own transcript** — save it and use it as
    an *independent* cross-check for proper nouns / quotes against your mlx run (in practice it
    caught a spelled-out name and confirmed two place names). It is NOT a substitute for the mlx
    transcript — no word timestamps, so no emphasis pass — and it can mis-hear what the speaker
    spells out, so the audio still wins ties.
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
$SCRIBE/scripts/transcribe.sh       <url>        <series>/NN-slug   # URL — downloads, then delegates to transcribe_local.sh (same hardened engine + gate)
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
phrase looped for the rest of it); **both scripts gate this** (`transcribe.sh` downloads then
delegates to `transcribe_local.sh`, which sets `--condition-on-previous-text False`, a
hallucination threshold, and the ≥25%-single-line gate; retry hotter via
`MLX_WHISPER_TEMPERATURE=0.4`, then flag) — trust the transcript only if it passed (no single
line ≥25%). (b) **wrong source** — verify the
audio actually IS the sermon you think it is; a `~90s` probe + filename/title check. Never run
Steps 2–7 on a transcript that failed either check.

## Step 2 — Faithful revision (MEDIUM dial)
Tighten run-ons and smooth transitions for a reader; remove spoken artifacts (false starts,
filler, doubled words). **KEEP the speaker's voice — the tics listed in `SPEAKER-PROFILE.md`**
(direct address, rhetorical repetition, rhetorical questions, em-dash asides). Fix only clear
transcription errors; verify any name/quote — Whisper phonetics lie. Log every non-obvious fix
in `CORRECTIONS-LOG.md` **and report it back** (see the reporting rule above) — don't silently
fix. Append confirmed misheard-name fixes to the profile's name-fix ledger.
**Writing the `…-BOOK.md` — go section by section, NOT one giant Write.** A full chapter emitted
in a single Write call gets API-content-filter-blocked (especially in a subagent). Write the
front matter + first section, then **Edit-append** each following section. This is the reliable
path for both the main agent and any fan-out subagent.

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
**Sensitive material — run the flag process below.** The keep/reword decision is speaker-tuned;
read the speaker's `SPEAKER-PROFILE.md` Filters table (and any series-local override in
`SERIES-DECISIONS.md`).
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

## Flag process (agnostic filters; speaker rules)
Flags are the audit trail of every editorial call a human should review. The **categories are
fixed and speaker-agnostic**; the **triggers/actions for SENSITIVE come from the speaker's
profile** — so the same process serves every speaker.
- **Categories:** `SENSITIVE` (reworded charged material) · `ATTRIBUTION` (unverifiable source) ·
  `VERSION` (non-default Bible version call) · `BYLINE` (byline ≠ recorded reading) ·
  `TRUNCATION` (completed a cut-off prayer/sentence) · `GRAPHIC` (referenced handout/figure) ·
  `WORDING` (reworded passage needing a look). Anything not covered defaults to KEEP — don't
  invent new sensitivities.
- **Surface candidates (non-destructive):** run `$SCRIBE/scripts/scan_flags.py <NN-slug>` — it
  greps the speaker's `flag-terms.tsv` watchlist against the draft and lists hits with line
  numbers. A hit is a *prompt to judge*, never an auto-edit. Judge each against the profile's
  Filters table: reword + flag, keep, or cut + flag.
- **Raise a flag** by adding one line to the `<!-- proof-checklist -->` block (Step 7) —
  `- **<CATEGORY>:** <what> — <decision>`. The `⚑` marker, when used, lives in that block ONLY,
  **NEVER inline in the body** (lint FAILs on an inline `⚑`).
- **Record durably** in the sermon's `FLAGS.md` (from `$SCRIBE/templates/FLAGS.md`): the
  proof-checklist is screen-only and is deleted at sign-off, so `FLAGS.md` is the surviving
  record. The same items go in your report back to the user.
- **Resolve:** the user reviews; at sign-off the proof-checklist block is deleted from the
  deliverable and the `FLAGS.md` rows are marked resolved.

## Step 4 — Scripture & citations
- **Verify every quotation** — don't trust the transcript's or your memory's wording. Use the
  bundled fetcher: `python3 $SCRIBE/scripts/bible_fetch.py <version> <book> <ch> [verses]`
  (e.g. `bible_fetch.py nasb77 isaiah 40 1-11`, `bible_fetch.py kjv haggai 2 1-9`). It pulls
  copyrighted versions (nasb77, esv, …) from BibleHub and public-domain ones (kjv, web) from a
  clean API, handling the poetry layout. Book names lowercase with underscores (`1_corinthians`,
  `psalms`). Cross-check the default against the alternate.
- **Version rule:** default to `bible_version`; switch a quote to the **alternate (`alt_version`)**
  when his surrounding exposition leans on words specific to it (the profile lists the tells). If
  he cites the alternate, keep it and tag it — never silently convert.
  - **Two-layer default (context, not just word-tells):** a sermon may deliberately use *two*
    versions by role — e.g. a formal **reading** in one version and **exposition** in another
    ("I'll read the KJV so you recognize it in the music… now we'll preach from the NASB"). When
    he announces this, treat it as a **series-wide layer rule** (record in `SERIES-DECISIONS.md`),
    render each layer in its stated version, and write a `scripture_note` that states both —
    don't force one global default and tag the rest.
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
- **Permissions footer** — you do NOT hand-write Bible copyright text. `finalize.py` (Step 6)
  appends the canonical notice for the default version plus any cited alternate, from
  `bible_permissions.py` (override per speaker with a `bible-permissions.tsv`). Verify the notice
  against the publisher's current wording before sending to print.

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

## Step 6 — Finalize (script) — the deliverable is Markdown
The deliverable is **`…-BOOK-final.md`** (Markdown — emphasis as `*italics*`, scripture as
blockquotes, `[^footnotes]`, `![figures]()`, all portable to any md reader/typesetter).
```
$SCRIBE/scripts/finalize.py  <…-BOOK-emph.md>                  # -> …-BOOK-final.md (THE deliverable)
$SCRIBE/scripts/build_html.py <…-BOOK-emph.md> <…-emph.html>   # optional HTML preview only
$SCRIBE/scripts/smartquotes.py <file.md>                       # straight -> curly, in place
```
`finalize.py` is the **sign-off** action: it strips the screen-only proof-checklist + comment
triggers and appends the Scripture-permissions footer, then writes `…-BOOK-final.md`. The
curated `…-BOOK-emph.md` stays the editable source of truth.
**The HTML preview is opt-in — never assume it.** Check the `preview` config: `yes` → build it;
`no` → skip; `ask`/unset → **ask the user** whether they want a styled HTML preview, and offer to
save the answer to `speaker.config` (so a batch isn't re-asked). The PostToolUse hook only
*refreshes a preview that already exists* — it never conjures one — and it never re-runs
apply_emphasis or finalize.

## Step 7 — Proofing checklist (in the render, screen-only)
Put the **same substantive Steps 2–4 calls you report back** into a `<!-- proof-checklist … -->`
block at the **very top of `…-BOOK-emph.md`**, above the `# ` title. The HTML preview renders it
as a subtle **static to-check list** — a *bullet* list, NOT interactive checkboxes. `finalize.py`
**strips it from the deliverable** at sign-off (and it never reaches the final book). Each `- `
line is one flag item carrying a **bold CATEGORY tag** (see the Flag process); these are the same
items that go in `FLAGS.md` and your report back.
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

## Step 9 — Retain or prune (ask; never assume)
A finished sermon dir accumulates a lot — audio, transcripts (`audio.{srt,vtt,tsv,json,txt}`),
the `emphasis_full/` wav + json, `whisper.log`, the intermediate `…-BOOK.md` / `…-BOOK-emph.md`,
the logs. Most users want only the deliverable. **Do not assume — ask what to keep**, honoring
the `keep` config: `final` → just `…-BOOK-final.md` (+ figures); `final+html` → also the preview;
`all` → keep everything; `ask`/unset → **ask the user** (and offer to save the answer to
`speaker.config`). Then prune:
```
$SCRIBE/scripts/prune_sermon.sh <NN-slug> --keep final,figures --dry-run   # preview the deletion
$SCRIBE/scripts/prune_sermon.sh <NN-slug> --keep final,figures             # apply
```
`--dry-run` first and show the list before deleting. Figures and the `…-BOOK-final.md` are kept
unless explicitly dropped. **Audio and intermediates are gone after this** — only prune once the
deliverable is verified (and committed, if the project is under git).

## Deliverables per sermon
After retention, what remains is your chosen keep set. In full: `…-BOOK-final.md` (**the
deliverable** — finalized Markdown with permissions footer), optional `…-emph.html` preview,
`…-BOOK.md` (source), `…-BOOK-emph.md` (curated source of truth), `FLAGS.md` (durable flag
record), `audio.*`, `emphasis_full/audio.json`, `CORRECTIONS-LOG.md`, `SCRIPTURE-VERIFICATION.md`.
Commit before pruning. Run `$SCRIBE/scripts/lint_series.py` clean first.
