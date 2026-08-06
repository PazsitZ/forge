# Ledger format and what the counts mean

The ledger lives at `<lessons-dir>/.usage-ledger.json` and is the only durable record of usage. It exists because session transcripts — the sole source of usage evidence — are pruned after `cleanupPeriodDays` (default 30). A live scan can never prove "unused for 60 days"; the ledger accumulates across runs until it can.

It is written in the repo so it travels with the corpus it describes and shows up in review ("this lesson went cold" is visible in a diff). The skill never commits it.

## Schema

```json
{
  "scanned_through": "2026-08-02T15:09:05.958000+00:00",
  "curate_sessions": ["00000000-0000-0000-0000-000000000000"],
  "scans": [
    {"start": "2026-07-02T13:41:00+00:00", "end": "2026-08-02T17:37:32+00:00"}
  ],
  "items": {
    "lesson:2026-07-29-verify-claims-against-the-artifact": {
      "kind": "lesson",
      "path": "docs/lessons/2026-07-29-verify-claims-against-the-artifact.md",
      "created": "2026-07-29",
      "created_estimated": false,
      "body_sha": "e3b0c44298fc1c14",
      "aliases": [],
      "reads": 1,
      "last_read": "2026-07-29T10:37:23.000Z",
      "read_sessions": ["9f1c…"],
      "read_days": ["2026-07-29"],
      "status": "live"
    }
  }
}
```

| Field | Meaning |
|---|---|
| item key | `<kind>:<slug>`. The prefix is load-bearing: without it a lesson and a memory with the same filename merge into one entry and silently pool their counts. Index keys keep the extension (`index:lessons.md`). |
| `scanned_through` | Stage-A `scanned_at` of the last run, identical to that run's `window.end`. Passed as `--since` next run, so windows abut instead of overlapping and events are counted exactly once. |
| `curate_sessions` | Session ids of past curate runs, passed as `--exclude-session`. Without this, the skill's own review reads inflate every subsequent run. |
| `scans` | Every window ever observed, appended one per run — the scanner's `window`, already clipped to `--since`. The record of when the corpus *was* being watched, and by omission when it was not. `coverage` is computed from this; see below. |
| `kind` | The *store*: `lesson`, `memory`, or `index`. It does not change when a file is archived, so counts survive the move. Index files (`lessons.md`, `MEMORY.md`) are tracked but never given a verdict — they are auto-injected every session, so their counts measure the harness, not the content. |
| `created` | Lessons: the filename date prefix. Memories: earlier of mtime and first-seen, with `created_estimated: true`. |
| `body_sha` | sha256 prefix of the file body, **frontmatter excluded**. The rename key — see below. |
| `aliases` | Previous keys whose counts were carried forward. |
| `reads`, `last_read` | Cumulative across all runs, not just the current window. Archived items keep accruing them. |
| `read_sessions`, `read_days` | Distinct session ids, and distinct UTC dates, behind those reads. **Unioned across runs, never summed** — a session straddling a window boundary is seen twice, and adding counts would turn one sitting into fake recurrence. The `promote` gate reads these, not `reads` alone. |
| `status` | `live`, `archived` (found under `archive/`), or `gone` (vanished from the tree with no content match). |

## Identity survives renames

The key is the identity, `body_sha` is the fallback. A ledger key with no on-disk entry is matched against the `body_sha` of any unrecognized on-disk file; on a hit, the old key moves into `aliases` and the counts carry over.

The hash covers the body only. Frontmatter carries the `name`/title that a rename rewrites, so hashing it would break the match in exactly the case the match exists for.

This is not hypothetical: renaming a skill (`grill-me` → `interview-me`) resets its name-keyed history to zero, however long it had been in use. No git history is consulted here, so content is the only stable identity available.

Renaming *and* editing a file in the same step defeats the match. Accepted: the entry lands as `gone` and the renamed file starts fresh, which under-reports rather than misattributes.

## What the read count deliberately excludes

`reads` counts `Read`/`NotebookRead` tool calls on the file, from the project's transcripts, including subagent activity (sidechain records live in the same files). Files under `curate-notes/` are not corpus items at all — the scanner drops them before counting, so past reports never appear as lessons that can never earn a verdict. Three further classes are dropped:

1. **Any session that wrote or edited the file.** The harness requires a Read before an Edit, so maintenance reads look identical to usage reads. This also covers the authoring session reading back what it just wrote. Observed in practice: a file credited with 2 reads had both of them immediately followed by an edit in the same session — maintenance, not use.
2. **Past curate runs**, via `curate_sessions`.
3. **Events at or before `scanned_through`**, so a re-run adds nothing.

The consequence is directional and must be stated in every report: **counts under-report use.** `reads: 0` means "no evidence of use in the ledger's span", never "proven useless". A verdict of `archive` rests on that absence plus the age floor, which is why archiving is reversible and deletion is not offered.

A fourth exclusion has no entry in the ledger at all, because it leaves no trace to record: **reads from any other tool.** Transcripts are Claude Code's. A file opened by Copilot, another agent, or the user's editor is read without the scanner ever learning it happened. `reads` is a Claude-Code-share metric, not a use metric — which is tolerable for `promote` (it under-promotes) and is the standing hazard for `archive`.

## Coverage is what the floors measure

```
coverage(item) = Σ over merge_overlaps(scans[]) of (window ∩ [created, now])
```

Not `now − created`. Raw age accrues whether or not anyone was watching: skip the skill for 40 days, and since transcripts prune at 30, a 10-day hole opens in which reads happened and were never counted. Age would carry an item past a floor on the strength of that hole. Coverage will not.

**Merge overlapping windows before summing.** Two windows covering the same day are one observed day, not two. The scanner already prevents the routine case by clipping `window.start` to `--since`, but a hand-edited ledger or a restored backup can still produce overlap, and double-counted coverage walks items past the eviction floors in a fraction of the real elapsed time — the one failure here that quietly deletes things.

The two are equal exactly when `scans[]` has run continuously since before the item was created — which is the normal case, and why the distinction stays invisible until the run it matters for. Report coverage always, and when it diverges from age, report both: the gap is the finding.

## First run

There is no ledger and no `--since`, so the first run sees only the last ~30 days and its counts start there. Older activity is unrecoverable — it was pruned before the ledger existed. Record that window as the first `scans[]` entry, and report it next to the verdicts so the evidence is never read as broader than it is.

An item created **before** the first window opens can never reach full coverage — its early life is simply unobserved. Such an item is a `hold` until the observed portion alone clears the floor.
