# CLAUDE.md — working in the scribe repo

scribe is a **speaker-agnostic** sermon-to-book pipeline, packaged as a Claude Code plugin. The
engine and the skill are generic; every speaker- and series-specific decision lives in a
*consumer* project (its `speaker.config` + `SPEAKER-PROFILE.md` and each series' `series.config`
+ `SERIES-*.md`), never in this repo. See `README.md` for the overview and `CONCEPTS.md` for the
domain vocabulary.

## Conventions

- **Keep the engine generic.** No speaker, series, Bible version, or church name belongs in
  `scripts/` or `skills/scribe/SKILL.md`. If you reach for a specific value, it belongs in a
  config key or a profile, resolved via `series_config.py` (`DEFAULTS < speaker.config <
  series.config`, walked up from the file).
- **The deliverable is Markdown** (`…-BOOK-final.md`). HTML is an optional, opt-in preview.
- **Don't break rendering output silently.** When changing a render/transform script, render a
  sample before and after and diff (`md5`/`cmp`) — the deliverable's bytes should change only
  when you intend them to. Copy unchanged scripts verbatim rather than retyping.
- **Optional outputs and destructive cleanup are opt-in** — ask, don't assume; the answer can be
  saved to config. The edit hook only refreshes an HTML preview that already exists.
- **Plugin packaging:** don't add a `"hooks"` key to `plugin.json` (the `hooks/hooks.json`
  auto-loads — declaring both errors). Reference engine paths via
  `${CLAUDE_PLUGIN_ROOT:-$HOME/Projects/scribe}`. After editing, bump the version and reinstall
  to refresh the installed cache.
- **Python 3 stdlib only** for the engine (no third-party deps); transcription assumes Apple-
  silicon `mlx-whisper` with a CPU fallback.

## Knowledge stores

- `docs/solutions/` — documented solutions to past problems and reusable patterns, organized by
  category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing
  or debugging in a documented area. **Local-only (gitignored)** — these are internal engineering
  notes, not shipped to plugin consumers, so the public repo won't contain them.
- `CONCEPTS.md` — shared domain vocabulary (engine/consumer, speaker/series layers,
  profile-as-ledger, flag taxonomy, deliverable). Relevant when orienting to the project or
  discussing domain concepts.
