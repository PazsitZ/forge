---
name: curate-learnings
description: Clean up, prune, and consolidate the lessons and memories stores — archive lessons that were never used, merge duplicates that say the same thing, and promote proven rules into AGENTS.md or CLAUDE.md. Use when asked to "clean up lessons", "prune lessons.md", "curate learnings", "distill memories", "the lessons index is getting long", or "are my lessons actually being used".
argument-hint: "[lessons-only | memories-only]  (default: both) — narrows which store gets verdicts, never what is scanned"
---

`docs/lessons/` and the memory store only ever grow, and their index files load into context at the start of every session. This skill closes the loop: measure what was actually read, then archive the dead, merge the redundant, and promote the proven into files that load automatically.

**Never run git.** Filesystem actions only — `mv`, read, write. No `git mv`, no `git add`, no `git commit`. Staging and committing is the user's step; list the touched paths at the end so they can do it.

**Stop at the report.** Stages A–D only ever write the ledger and the report. Nothing is moved, merged, or promoted until the user approves that group.

## Stage 0 — resolve paths and scope

1. Lessons: `<cwd>/docs/lessons/`. If it does not exist, say so in one line and stop.
2. Memories: `autoMemoryDirectory` from `<cwd>/.claude/settings.local.json`, else `<cwd>/docs/memories/`, else `~/.claude/projects/<slug>/memory/`. If none exists, run lessons-only rather than failing.
3. Ledger: `<lessons-dir>/.usage-ledger.json`. Absent on first run — that is expected, not an error.
4. Scope, from the argument — `lessons-only`, `memories-only`, or both when absent.

   Scope narrows **which items get a verdict and appear in the report**. It never narrows the scan: both stores are always scanned and always merged into the ledger, because `scans[]` is a property of the run, not of a store. Recording a window as observed while quietly not looking at half the corpus would credit those items with coverage nobody measured.

   `memories-only` still needs the lessons directory — the ledger lives there.

## Stage A — scan

Run the scanner **before reading any lesson or memory file**, so this session's own review reads land after the cutoff and cannot inflate the next run:

```bash
python3 <skill-dir>/scripts/scan_usage.py \
  --project-dir "$PWD" \
  --memories-dir "<memories dir from Stage 0, omit if it is <cwd>/docs/memories>" \
  --since "<ledger.scanned_through, omit on first run>" \
  --exclude-session "<each id in ledger.curate_sessions>"
```

`<skill-dir>` is wherever this SKILL.md was loaded from — `.claude/skills/curate-learnings/`, `.github/skills/curate-learnings/`, or `~/.claude/skills/curate-learnings/` depending on the install. Resolve it rather than assuming one; do not copy the script elsewhere.

The scanner reads Claude Code session transcripts (`~/.claude/projects/<slug>/*.jsonl`). Under a harness that does not write them, it finds no transcripts and every count is 0 — report that as *no evidence available*, and do not let it produce `archive` verdicts.

It returns per-item `reads`, `last_read`, `authoring_session`, plus `on_disk` (path, `archived`, `body_sha`, `mtime`) and the window it observed. Read [references/LEDGER-FORMAT.md](references/LEDGER-FORMAT.md) for what the numbers mean and what they deliberately exclude.

Check three fields before going on:

- `memories_scanned: false` means no memory store was found. Say so in the report — an empty memory section otherwise reads as a curated store rather than a missing one.
- `unobserved_gap` non-null means transcripts were pruned between this run and the last: nobody was watching from `from` to `to`. Report it, and remember coverage deliberately excludes it.
- `transcripts: 0` means this harness writes no transcripts to read. Every count is then 0 by construction — report *no evidence available* and propose no `archive` verdicts at all.

Two properties of the count matter when you report it:

- **The window is ~30 days.** Transcripts prune at `cleanupPeriodDays` (default 30). A first run cannot see further back than that, no matter how old the corpus is.
- **Reads are under-counted, never inflated.** A session that wrote or edited a file gets no read credit for it, because the harness forces a Read before an Edit. So `reads: 0` means "no evidence of use", not "proven unused".

## Stage B — merge into the ledger

Items are keyed `<kind>:<slug>` — `lesson:2026-07-29-…`, `memory:…`, `index:lessons.md`. The prefix is what keeps a lesson and a memory that happen to share a filename from collapsing into one entry.

Load the ledger, add unseen items from `on_disk`, add the new read counts, then reconcile disappearances:

- An on-disk entry with `"archived": true` → set `"status": "archived"` and update `path`. It is not gone; it is where a past run put it.
- A ledger key with **no on-disk entry at all** → look for an unrecognized on-disk file with the same `body_sha`. On a hit it was renamed: move the old key into `aliases`, update `path`, keep the counts. On no hit, mark `"status": "gone"` and leave it (the user may have moved it out of the tree by hand).
- `kind: index` entries are never `gone`, never archived and never given a verdict — they are auto-injected every session, so their counts measure the harness, not the content.
- `created`: for lessons, the date prefix in the filename. For memories there is no prefix — use the earlier of `mtime` and this run's date, and record `"created_estimated": true`. Those entries must be reported as `coverage≥N`, never as an exact figure.
- Append the scanner's `window` verbatim to the top-level `scans` array. Do **not** substitute the raw transcript span (`window_oldest`): the scanner has already clipped `window.start` to `since`, and re-crediting time an earlier run counted would inflate every item's coverage and walk the whole corpus past the eviction floors early. If `window` is null, there was nothing to observe — append nothing.

The scanner drops this skill's own `curate-notes/curate-*.md` reports before you see them; they carry no rule and no index line, so they can never earn a verdict.

Write the ledger now, before the report. It is the run's durable output even if the user approves nothing.

## Stage C — classify

Apply the verdict table in [references/POLICY.md](references/POLICY.md) — it holds the thresholds, the merge-clustering rule, and the promotion routing table. Rows are evaluated top-down, first match wins.

Classify only items in the Stage-0 scope, and only those with `status: live`. Already-archived items keep accruing reads in the ledger — a read of an archived lesson is real evidence — but they have no index line left to pay for, so they get no verdict.

Two floors, not one, and both are measured in **coverage** (observed time) rather than raw age:

| Verdict | Floor |
|---|---|
| `merge`, `promote` | none — neither is an eviction |
| `compact` | coverage ≥ 30d |
| `archive` | coverage ≥ 60d, and at most 5 proposals per run |

## Stage D — report, then stop

Write `<lessons-dir>/curate-notes/curate-YYYY-MM-DD.md`:

- The window actually observed this run, the ledger's cumulative span, and any `unobserved_gap`, stated plainly. Name the scope if it was narrowed, so an absent store is never mistaken for a clean one.
- One verdict table: item, kind, **coverage**, reads, last read, verdict. Group by verdict. Report coverage, not age — and if the two differ for any row, say so and give both, because the gap is the part worth seeing.
- One evidence line per row, naming **which floor it was measured against**. A row is unreadable without knowing whether 30d or 60d applied to it. For merge rows, name the shared rule instead.
- If the floors make the archive/compact/promote groups empty, **say that** — an early run legitimately has nothing to evict, and its value is starting the ledger. Do not manufacture verdicts to fill the table.
- If the archive group was capped at 5, state how many rows were held back and to when.

Then ask for approval **per verdict group** (archive / merge / promote / compact) with AskUserQuestion — not per item, which is unusable at 20+ rows. Stop until answered.

## Stage E — apply what was approved

- **Archive** — `mv` the file into `<store>/archive/` (create it if needed), then delete its line from the index (`lessons.md` / `MEMORY.md`). Move, never copy: a copy leaves two live sources and the self-contained file hides it. Verify the source path is gone.
- **Compact** — rewrite the item's **index line** to ≤200 characters — date, linked title, one clause. Nothing else changes — the file does not move, the body is not edited, the ledger entry keeps its counts. The body is where the detail belongs; it costs nothing until someone opens it.

  Before shortening a line, confirm the fact you are cutting is actually in the body. An index line for an item with **no backing file** is the content, not a summary of it — truncating it deletes the fact outright. Give that item a real file first, then point at it.
- **Merge** — write one new themed lesson stating the rule once, with each original as a two-line case and a link to its archived path. `mv` the originals to `archive/`. Replace their index lines with a single line for the new file.
- **Promote** — classify the rule first:
  - project-specific (this repo's conventions, paths, pipelines) → append a one-line directive to `<cwd>/AGENTS.md`, linking the lesson for rationale;
  - harness/tooling-general (true in every repo) → append to the user-level global instructions file (`~/.claude/CLAUDE.md` for Claude Code, its equivalent elsewhere), kept terse — it competes for attention on every request in every project;
  - neither → leave it as a lesson, and mark it `compact` only if its index line is over 200 chars.

  Then `mv` the lesson to `archive/` and drop its index line, since the rule now loads automatically.
- **Memories** — same verdicts, but never delete: the harness owns `MEMORY.md` and may recreate a memory it still considers live. Archive and unlink from the index only.
- **Ledger** — update `path`/`status` for everything moved, append this session's id to `curate_sessions`, set `scanned_through` to the scanner's `scanned_at` (which is also `window.end`, so the next run's window starts exactly where this one ended), and confirm this run's window landed in `scans`.

Close by reporting what was applied, what was skipped, and the list of touched paths for the user to commit.
