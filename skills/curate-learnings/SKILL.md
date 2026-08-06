---
name: curate-learnings
description: Clean up, prune, and consolidate the lessons and memories stores — archive lessons that were never used, merge duplicates that say the same thing, and promote proven rules into AGENTS.md or CLAUDE.md on your per-item confirmation. Use when asked to "clean up lessons", "prune lessons.md", "curate learnings", "distill memories", "the lessons index is getting long", or "are my lessons actually being used".
argument-hint: "[lessons-only | memories-only]  (default: both) — narrows which store gets verdicts, never what is scanned"
---

`docs/lessons/` and the memory store only ever grow, and their index files load into context at the start of every session. This skill closes the loop: measure what was actually read, then archive the dead, merge the redundant, and promote the proven into files that load automatically.

**Never run git.** Filesystem actions only — `mv`, read, write. No `git mv`, no `git add`, no `git commit`. Staging and committing is the user's step; list the touched paths at the end so they can do it.

**Stop at the report.** Stages A–D only ever write the ledger and the report. Nothing is moved or merged until the user approves that group — and nothing is **promoted** until the user confirms that item, with the exact line and target file in front of them. Group approval never authorises a promotion.

## Stage 0 — resolve paths and scope

1. Lessons: `<cwd>/docs/lessons/`.

   If the directory is missing there is nothing to curate. Say so in one line, offer to create it with an empty `lessons.md` so the learnings instruction has somewhere to write, and stop either way. Never create it silently: an empty store makes the run report a clean corpus that never existed, and a first `scans[]` entry would start the clock on a store with nothing in it.

   If the directory exists and holds lesson files but `lessons.md` does not, ask before rebuilding it. Reconstructing an index means writing one line per lesson, which is authoring rather than curation, and those lines are what every later `compact` verdict is measured against.

   Everything the skill writes for its own use — `archive/`, `curate-notes/` — it creates when missing without asking. Those hold no content decisions.
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
- `read_sessions` and `read_days` **union** with what the entry already holds; they are never added. Runs abut, but a single session can straddle the boundary and be seen by both — summing would invent recurrence out of one sitting, which is exactly what the `promote` gate exists to reject.
- Append the scanner's `window` verbatim to the top-level `scans` array. Do **not** substitute the raw transcript span (`window_oldest`): the scanner has already clipped `window.start` to `since`, and re-crediting time an earlier run counted would inflate every item's coverage and walk the whole corpus past the eviction floors early. If `window` is null, there was nothing to observe — append nothing.

The scanner drops this skill's own `curate-notes/curate-*.md` reports before you see them; they carry no rule and no index line, so they can never earn a verdict.

Write the ledger now, before the report. It is the run's durable output even if the user approves nothing.

## Stage C — classify

Apply the verdict table in [references/POLICY.md](references/POLICY.md) — it holds the thresholds, the merge-clustering rule, and the promotion routing table. Rows are evaluated top-down, first match wins.

Classify only items in the Stage-0 scope, and only those with `status: live`. Already-archived items keep accruing reads in the ledger — a read of an archived lesson is real evidence — but they have no index line left to pay for, so they get no verdict.

Two floors, not one, and both are measured in **coverage** (observed time) rather than raw age:

| Verdict | Floor |
|---|---|
| `merge`, `promote?` | none — neither is an eviction |
| `compact` | coverage ≥ 30d |
| `archive` | coverage ≥ 60d, and at most 5 proposals per run |

`promote?` is a **nomination, not a verdict**. It ranks a shortlist; it decides nothing. Nothing is ever promoted without per-item confirmation, and the thresholds exist only to order the list — see [Promotion is nominated, never decided](references/POLICY.md#promotion-is-nominated-never-decided).

## Stage D — report, then stop

Write `<lessons-dir>/curate-notes/curate-YYYY-MM-DD.md`, creating `curate-notes/` if it is not there:

- The window actually observed this run, the ledger's cumulative span, and any `unobserved_gap`, stated plainly. Name the scope if it was narrowed, so an absent store is never mistaken for a clean one.
- One verdict table: item, kind, **coverage**, reads, last read, verdict. Group by verdict. Report coverage, not age — and if the two differ for any row, say so and give both, because the gap is the part worth seeing.
- `promote?` rows carry two extra columns, **sessions** and **span** (first to last `read_days`). Without them the row shows a bare `reads: 2` and hides the one distinction the gate is built on — one sitting versus recurrence.
- One evidence line per row, naming **which floor it was measured against**. A row is unreadable without knowing whether 30d or 60d applied to it. For merge rows, name the shared rule instead. For `promote?` rows, name the routing target as well.
- If the floors make the archive/compact/promote groups empty, **say that** — an early run legitimately has nothing to evict, and its value is starting the ledger. Do not manufacture verdicts to fill the table.
- If the archive group was capped at 5, state how many rows were held back and to when.
- Close the promote section by inviting nominations: any live item can be promoted on request whatever the counts say. State the reason plainly — reads made outside Claude Code leave no trace, so an item that is load-bearing under another tool sits at `reads: 0` here forever. Without this line the user has no way to know the shortlist is not the whole set.

Then ask for approval with AskUserQuestion:

- **archive / merge / compact** — **per verdict group.** Per item is unusable at 20+ rows.
- **`promote?`** — do **not** ask for it here. Nominations are confirmed one at a time in Stage E, each with its line and target file already written out; a yes given at this point would be a yes to text nobody has seen. Ask only whether the user wants to add nominations of their own — including when the shortlist is empty.

Stop until answered.

## Stage E — apply what was approved

- **Archive** — `mv` the file into `<store>/archive/` (create it if needed), then delete its line from the index (`lessons.md` / `MEMORY.md`). Move, never copy: a copy leaves two live sources and the self-contained file hides it. Verify the source path is gone.
- **Compact** — rewrite the item's **index line** to ≤200 characters — date, linked title, one clause. Nothing else changes — the file does not move, the body is not edited, the ledger entry keeps its counts. The body is where the detail belongs; it costs nothing until someone opens it.

  Before shortening a line, confirm the fact you are cutting is actually in the body. An index line for an item with **no backing file** is the content, not a summary of it — truncating it deletes the fact outright. Give that item a real file first, then point at it.
- **Merge** — write one new themed lesson stating the rule once, with each original as a two-line case and a link to its archived path. `mv` the originals to `archive/`. Replace their index lines with a single line for the new file.
- **Promote** — a nomination, applied one item at a time and never in a batch. For each:

  1. **Route it.** Project-specific (this repo's conventions, paths, pipelines) → `<cwd>/AGENTS.md`, as a one-line directive linking the lesson for rationale. Harness/tooling-general (true in every repo) → the user-level global instructions file (`~/.claude/CLAUDE.md` for Claude Code, its equivalent elsewhere), kept terse, since it competes for attention on every request in every project. Neither → it stays a lesson; mark it `compact` only if its index line is over 200 chars, and drop the nomination.
  2. **Write the line, then show it.** Present the target file and the exact text to be appended, with the item's evidence beside it, and ask. The user may accept, reword, retarget or skip — rewording is the expected outcome, not an exception, because a promoted rule has to survive with none of the lesson's context around it.
  3. **Only on an explicit yes**, append to the target (append-only — never rewrite or reorder what is already there), `mv` the lesson to `archive/`, and drop its index line, since the rule now loads automatically.

     Check that the target file ends in a newline before appending. `AGENTS.md` and `CLAUDE.md` are line-oriented: appending to a file whose last byte is not `\n` fuses your directive onto the existing last line, producing one instruction that says neither thing. It fails silently and reads correctly at a glance.

  A skipped nomination stays exactly where it was: live, indexed, and eligible again next run. Do not downgrade it to `archive` because the user declined to promote it — those are opposite judgements, not a fallback chain.

  User-named items follow the same three steps. They skip the thresholds, not the preview.

  **Promotion is the one action here with no undo path in the ledger.** Once a rule leaves the corpus its reads stop being tracked, so a promoted line is never revisited by a later run. That is why it is confirmed one at a time — and why, if the user approves the group of nominations wholesale without seeing the lines, you ask again per item rather than taking it.
- **Memories** — same verdicts, but never delete: the harness owns `MEMORY.md` and may recreate a memory it still considers live. Archive and unlink from the index only.
- **Ledger** — update `path`/`status` for everything moved, append this session's id to `curate_sessions`, set `scanned_through` to the scanner's `scanned_at` (which is also `window.end`, so the next run's window starts exactly where this one ended), and confirm this run's window landed in `scans`.

Close by reporting what was applied, what was skipped, and the list of touched paths for the user to commit.
