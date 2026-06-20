# Concepts

Shared domain vocabulary for this project — entities, named processes, and status concepts with
project-specific meaning. Seeded with core domain vocabulary, then accretes as ce-compound and
ce-compound-refresh process learnings; direct edits are fine. Glossary only, not a spec or
catch-all.

## Project structure

### Engine
The speaker-agnostic scripts that do the mechanical work (transcribe, detect emphasis, render,
finalize, lint, prune). Knows nothing about any particular speaker; reads everything it needs
from config. Shipped in the plugin; one copy serves every consumer.

### Consumer
A data project that uses the engine — one speaker's body of work, holding the audio, the drafts,
and the config/ledgers that make the generic engine produce *that speaker's* book. The plugin is
generic; the consumer carries all the specifics.

### Speaker layer
The speaker-wide config and precedent at a consumer's root: machine knobs and the speaker's
voice/version/flag rulings. Applies to every series under that speaker.

### Series layer
The per-series config and precedent inside a series folder: title, numbering, and the
proper-noun seed for that series. Overrides the speaker layer for that series only.

### Config resolution
The rule that a value is found by walking up the directory tree and merging layers in precedence
order, least-specific to most-specific, so the nearest definition wins.

## Precedent ledgers

### Speaker profile
The durable, append-only record of a speaker's voice tics, Bible-version habits, flag rules, and
confirmed name fixes. Read before editing; grows denser with each sermon so later chapters draft
as cheaply as established ones. The mechanism by which work compounds per speaker.

### Series precedent
The series-local standing rulings, canonical wording of recurring quotes/figures, and house
style. Keeps parallel drafting consistent so parallel work approximates serial work.

## The pipeline

### Bookify
The editorial pass that turns a faithful transcript into book prose — stripping oral deixis,
converting spoken handout references into reader-facing figure pointers, and deriving headings
from the speaker's own numbered points.

### Emphasis
Italicized prose marking spoken stress, proposed by detecting acoustic prominence in the word
timestamps and then hand-pruned. A proposal layer, not a final answer; re-running it overwrites
hand curation.

### Flag taxonomy
The fixed, speaker-agnostic set of categories for material a human should review (sensitive,
unverifiable attribution, version call, and so on). The categories are universal; what triggers
a given category, and whether to reword or keep, comes from the speaker profile.

### Watchlist
A speaker's list of terms or patterns that, when found in a draft, prompt a human to judge them
against the profile — a non-destructive review prompt, never an automatic edit or a blocklist.

### Finalize
The sign-off action that produces the deliverable: it strips the screen-only review material and
appends the Scripture-permissions footer, leaving clean Markdown.

### Deliverable
The single finished output of a sermon — one Markdown file, portable to any reader or
typesetter. The styled HTML rendering is an optional preview, not the deliverable.

## Retention concepts

### Keep set
The artifacts a user chooses to retain after finalize; everything else (audio, transcripts,
intermediate drafts, logs) is pruned. The choice is asked, never assumed, and can be saved to
config.
