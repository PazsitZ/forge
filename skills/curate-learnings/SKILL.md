---
name: curate-learnings
description: Clean up, prune, and consolidate the lessons and memories stores — archive lessons that were never used, merge duplicates that say the same thing, and promote proven rules into AGENTS.md or CLAUDE.md. Use when asked to "clean up lessons", "prune lessons.md", "curate learnings", "distill memories", "the lessons index is getting long", or "are my lessons actually being used".
argument-hint: "[lessons-only | memories-only]  (default: both)"
---

`docs/lessons/` and the memory store only ever grow, and their index files load into context at the start of every session. This skill closes the loop: measure what was actually read, then archive the dead, merge the redundant, and promote the proven into files that load automatically.

**Never run git.** Filesystem actions only — `mv`, read, write. No `git mv`, no `git add`, no `git commit`. Staging and committing is the user's step; list the touched paths at the end so they can do it.

**Stop at the report.** Stages A–D only ever write the ledger and the report. Nothing is moved, merged, or promoted until the user approves that group.

## Stage 0 — resolve paths

1. Lessons: `<cwd>/docs/lessons/`. If it does not exist, say so in one line and stop.
2. Memories: `autoMemoryDirectory` from `<cwd>/.claude/settings.local.json`, else `<cwd>/docs/memories/`, else `~/.claude/projects/<slug>/memory/`. If none exists, run lessons-only rather than failing.
3. Ledger: `<lessons-dir>/.usage-ledger.json`. Absent on first run — that is expected, not an error.

## Stage A — scan

Run the scanner **before reading any lesson or memory file**, so this session's own review reads land after the cutoff and cannot inflate the next run:

```bash
python3 ~/.claude/skills/curate-learnings/scripts/scan_usage.py \
  --project-dir "$PWD" \
  --since "<ledger.scanned_through, omit on first run>" \
  --exclude-session "<each id in ledger.curate_sessions>"
```

It returns per-item `reads`, `last_read`, `authoring_session`, plus `on_disk` (path, `body_sha`, `mtime`) and the transcript window it saw. Read [references/LEDGER-FORMAT.md](references/LEDGER-FORMAT.md) for what the numbers mean and what they deliberately exclude.

Two properties of the count matter when you report it:

- **The window is ~30 days.** Transcripts prune at `cleanupPeriodDays` (default 30). A first run cannot see further back than that, no matter how old the corpus is.
- **Reads are under-counted, never inflated.** A session that wrote or edited a file gets no read credit for it, because the harness forces a Read before an Edit. So `reads: 0` means "no evidence of use", not "proven unused".

## Stage B — merge into the ledger

Load the ledger, add unseen items from `on_disk`, add the new read counts, then reconcile disappearances:

- A ledger slug with **no file on disk** → look for an unrecognized on-disk file with the same `body_sha`. On a hit it was renamed: move the old slug into `aliases`, update `path`, keep the counts. On no hit, mark `"status": "gone"` and leave it (the user may have moved it by hand).
- `created`: for lessons, the date prefix in the filename. For memories there is no prefix — use the earlier of `mtime` and this run's date, and record `"created_estimated": true`. Those entries must be reported as `age≥N`, never as an exact age.

Write the ledger now, before the report. It is the run's durable output even if the user approves nothing.

## Stage C — classify

Apply the verdict table in [references/POLICY.md](references/POLICY.md) — it holds the thresholds, the merge-clustering rule, and the promotion routing table. Only `merge` is exempt from the 60-day age floor.

## Stage D — report, then stop

Write `<lessons-dir>/curate-YYYY-MM-DD.md`:

- The transcript window actually scanned, and the ledger's cumulative span, stated plainly.
- One verdict table: item, kind, age, reads, last read, verdict. Group by verdict.
- One evidence line per row. For merge rows, name the shared rule.
- If the age floor makes the archive/compact/promote groups empty, **say that** — an early run legitimately has nothing to evict, and its value is starting the ledger. Do not manufacture verdicts to fill the table.

Then ask for approval **per verdict group** (archive / merge / promote) with AskUserQuestion — not per item, which is unusable at 20+ rows. Stop until answered.

## Stage E — apply what was approved

- **Archive** — `mv` the file into `<store>/archive/` (create it if needed), then delete its line from the index (`lessons.md` / `MEMORY.md`). Move, never copy: a copy leaves two live sources and the self-contained file hides it. Verify the source path is gone.
- **Merge** — write one new themed lesson stating the rule once, with each original as a two-line case and a link to its archived path. `mv` the originals to `archive/`. Replace their index lines with a single line for the new file.
- **Promote** — classify the rule first:
  - project-specific (this repo's conventions, paths, pipelines) → append a one-line directive to `<cwd>/AGENTS.md`, linking the lesson for rationale;
  - harness/tooling-general (true in every repo) → append to `~/.claude/CLAUDE.md`, kept terse — it competes for attention on every request in every project;
  - neither → leave it as a lesson and mark it `compact`.

  Then `mv` the lesson to `archive/` and drop its index line, since the rule now loads automatically.
- **Memories** — same verdicts, but never delete: the harness owns `MEMORY.md` and may recreate a memory it still considers live. Archive and unlink from the index only.
- **Ledger** — update `path`/`status` for everything moved, append this session's id to `curate_sessions`, set `scanned_through` to the Stage-A scan time.

Close by reporting what was applied, what was skipped, and the list of touched paths for the user to commit.
