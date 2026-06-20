# Speaker profile — <Speaker name>

The durable record of this speaker's voice and editorial standing rulings. The scribe SKILL
reads this before Steps 2–4. It is a **ledger**: append every name fix, version quirk, voice
tell, and sensitivity call as you process more of this speaker's sermons, so later chapters
(and parallel agents) resolve them the same way. Pairs with `speaker.config` (the machine
knobs) and each series' `SERIES-*.md` (series-local precedent).

## Voice signature — KEEP these (Step 2/5)
Tics that ARE the speaker and must survive faithful revision:
- Direct address: <e.g. "you and I", "beloved", "now listen">
- Rhetorical repetition / litany: <describe the pattern>
- Rhetorical questions, em-dash asides: <keep / how>
- Reverent-hush emphasis (the emphasis script is blind to this — add by ear): <e.g. a slowed,
  lowered "Jesus Christ Himself">

## Scripture policy (Step 4)
- Default version: <e.g. NASB 1977> — verify against `<bible_url_base>`.
- Switch to the alternate (<e.g. KJV>) when the surrounding exposition leans on its wording.
  Signature tells: <e.g. "the whole *counsel* of God" = KJV>.
- If the speaker cites the alternate, keep and tag it; never silently convert.

## Filters (flag taxonomy) — Step 3
The agnostic flag categories are fixed by the SKILL: **SENSITIVE, ATTRIBUTION, VERSION, BYLINE,
TRUNCATION, GRAPHIC, WORDING**. This table tells the editorial pass how THIS speaker's content
maps onto them — the action per trigger. `scan_flags.py` greps `flag-terms.tsv` to surface
SENSITIVE/ATTRIBUTION candidates; you judge each here and raise the flag in the proof-checklist.

| Category  | Trigger (what fires it)                         | Action |
|-----------|--------------------------------------------------|--------|
| SENSITIVE | <e.g. charged racial/ethnic/national-group aside> | reword in his voice (keep the point), `⚑ REWORDED — review wording` |
| SENSITIVE | <doctrinal / theological position>               | KEEP as ordinary exposition — no flag, do NOT soften |
| SENSITIVE | named figure                                     | famous → KEEP; non-famous → reword + flag |
| ATTRIBUTION | source/quote that can't be verified            | drop name + footnote, keep his wording, flag |
| VERSION   | quote leans on alternate-version wording          | switch + tag `(…, <alt>)`, flag the call |

Anything NOT covered here defaults to KEEP — do not invent new sensitivities.

## Proper-noun seed
The base list for the whisper prompt (each series adds its own); the names Whisper mishears:
- <Name>, <Name>, <Name> …

## Name / attribution fixes (append-only ledger)
Misheard proper nouns confirmed and corrected, with a citable source:
- "<as transcribed>" → **<correct>** (<source>).
