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

## Sensitivity taxonomy (Step 3)
What this speaker says that needs handling, and how:
- <Category to reword + flag>: <rule>. → reword in his voice, add `⚑ REWORDED — review wording`.
- <Category to KEEP as ordinary exposition, do NOT soften>: <rule>.
- Named figures: famous → KEEP; non-famous → reword + flag.

## Proper-noun seed
The base list for the whisper prompt (each series adds its own); the names Whisper mishears:
- <Name>, <Name>, <Name> …

## Name / attribution fixes (append-only ledger)
Misheard proper nouns confirmed and corrected, with a citable source:
- "<as transcribed>" → **<correct>** (<source>).
