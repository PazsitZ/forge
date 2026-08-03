# Verdict policy

## Table

| Condition | Verdict | Action |
|---|---|---|
| age < 60d | `hold` | Untouched. Not listed as a candidate. |
| age ≥ 60d, reads 0 | `archive` | Move to `archive/`, unlink from index. |
| age ≥ 60d, reads 1–2 | `compact` | Rewrite tighter in place, or fold into a merge cluster. |
| reads ≥ 3, any age | `promote` | Route to `AGENTS.md` or `~/.claude/CLAUDE.md`, then archive the file. |
| ≥3 items share one rule, any age | `merge` | Collapse into one themed file. |

Age uses `created`, not mtime — editing a lesson does not restart its clock.

## Why 60 days

The transcript window is 30 days. Inside it, "never read" and "the situation it warns about has not come up yet" are indistinguishable. The floor forces at least one full ledger cycle of evidence before anything is evicted, so the archive verdict rests on ledger history rather than on a single 30-day snapshot.

An early corpus therefore produces an empty archive group. That is the correct output, not a failed run.

## Why merge ignores the floor

The floor protects *eviction* decisions from thin evidence. Merging is bloat-driven and lossless — the rule survives, the cases survive, the originals sit in `archive/` with pointers — so nothing is at risk from doing it early. The cost it addresses (index lines loaded every session) is incurred immediately, not after 60 days.

Cluster on the **rule**, not the topic. Two lessons about pytest are not a cluster; five lessons that all say *verify the claim against the artifact instead of accepting it* are, whatever subsystem each was learned in. If a merged file cannot state one rule in one sentence, the cluster was topical and should be split back.

Keep merges to one theme per run. A merge that rewrites half the corpus is unreviewable.

## Promotion routing

| The rule is… | Goes to | Form |
|---|---|---|
| specific to this repo — its paths, pipelines, conventions, deployment | `<cwd>/AGENTS.md` | One-line directive + link to the archived lesson for rationale. Cross-agent, not Claude-only. |
| true of the harness or tooling in any repo | `~/.claude/CLAUDE.md` | One terse line. This file is read on every request in every project — anything vague costs attention everywhere. |
| durable project *fact* rather than a rule | the memory store | A memory file. Facts are Memory's job; rules are Lessons'. |
| neither general nor repo-specific | stays a lesson | Mark `compact` instead. |

A promoted lesson moves to `archive/` and loses its index line: the rule now loads automatically, so leaving it in the index pays the context cost twice.

Promotion is append-only on the target file. Never rewrite or reorder existing instructions in `AGENTS.md` or `CLAUDE.md` during a curate run — that is a separate, deliberate edit.

## Verdicts are proposals

Every threshold here is a heuristic over a signal that under-counts by construction (see [LEDGER-FORMAT.md](LEDGER-FORMAT.md)). A lesson can be load-bearing without ever being read — it may have been absorbed into the way a task was approached. So:

- read the item before proposing `archive` for it, and drop the verdict if the content is still obviously live;
- state the evidence for each row, never just the verdict;
- prefer `compact` over `archive` when the rule is sound but the prose is long;
- archive, never delete — a wrong archive verdict costs one `mv` to undo.
