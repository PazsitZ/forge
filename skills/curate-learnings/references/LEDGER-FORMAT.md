# Ledger format and what the counts mean

The ledger lives at `<lessons-dir>/.usage-ledger.json` and is the only durable record of usage. It exists because session transcripts — the sole source of usage evidence — are pruned after `cleanupPeriodDays` (default 30). A live scan can never prove "unused for 60 days"; the ledger accumulates across runs until it can.

It is written in the repo so it travels with the corpus it describes and shows up in review ("this lesson went cold" is visible in a diff). The skill never commits it.

## Schema

```json
{
  "scanned_through": "2026-08-02T15:09:05.958000+00:00",
  "curate_sessions": ["72e32244-95fb-417c-884a-b0e986f9ac54"],
  "items": {
    "2026-07-29-prohibition-load-bearing-for-downstream-audit": {
      "kind": "lesson",
      "path": "docs/lessons/2026-07-29-prohibition-load-bearing-for-downstream-audit.md",
      "created": "2026-07-29",
      "created_estimated": false,
      "body_sha": "e3b0c44298fc1c14",
      "aliases": [],
      "reads": 1,
      "last_read": "2026-07-29T10:37:23.000Z",
      "status": "live"
    }
  }
}
```

| Field | Meaning |
|---|---|
| `scanned_through` | Stage-A scan time of the last run. Passed as `--since` next run so events are counted exactly once. |
| `curate_sessions` | Session ids of past curate runs, passed as `--exclude-session`. Without this, the skill's own review reads inflate every subsequent run. |
| `kind` | `lesson`, `memory`, or `index`. Index files (`lessons.md`, `MEMORY.md`) are tracked but never given a verdict — they are auto-injected every session, so their counts measure the harness, not the content. |
| `created` | Lessons: the filename date prefix. Memories: earlier of mtime and first-seen, with `created_estimated: true`. |
| `body_sha` | sha256 prefix of the file body. The rename key — see below. |
| `aliases` | Previous slugs whose counts were carried forward. |
| `reads`, `last_read` | Cumulative across all runs, not just the current window. |
| `status` | `live`, `archived`, or `gone` (vanished from disk with no content match). |

## Identity survives renames

Slug is the key, `body_sha` is the fallback. A ledger slug with no file on disk is matched against the `body_sha` of any unrecognized on-disk file; on a hit, the old slug moves into `aliases` and the counts carry over.

This is not hypothetical: `grill-me` → `interview-me` reset that skill's visible history from 31 invocations to 1. Name-keyed history breaks on rename, and no git history is consulted here, so content is the only stable identity available.

Renaming *and* editing a file in the same step defeats the match. Accepted: the entry lands as `gone` and the renamed file starts fresh, which under-reports rather than misattributes.

## What the read count deliberately excludes

`reads` counts `Read`/`NotebookRead` tool calls on the file, from the project's transcripts, including subagent activity (sidechain records live in the same files). Three classes are dropped:

1. **Any session that wrote or edited the file.** The harness requires a Read before an Edit, so maintenance reads look identical to usage reads. This also covers the authoring session reading back what it just wrote. Verified on the Raz-pAI corpus: `project_design_patterns_skill.md` showed 2 reads that were both immediately followed by edits in the same session.
2. **Past curate runs**, via `curate_sessions`.
3. **Events at or before `scanned_through`**, so a re-run adds nothing.

The consequence is directional and must be stated in every report: **counts under-report use.** `reads: 0` means "no evidence of use in the ledger's span", never "proven useless". A verdict of `archive` rests on that absence plus the age floor, which is why archiving is reversible and deletion is not offered.

## First run

There is no ledger and no `--since`, so the first run sees only the last ~30 days and its counts start there. Older activity is unrecoverable — it was pruned before the ledger existed. Report the scanned window next to the verdicts so the evidence is never read as broader than it is.
