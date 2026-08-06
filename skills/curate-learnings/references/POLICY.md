# Verdict policy

## Table

Evaluate **top-down; first match wins.**

| Condition | Verdict | Action |
|---|---|---|
| ≥3 items share one rule, any age | `merge` | Collapse into one themed file. |
| reads ≥ 2, ledger span ≥ 30d | `promote` | Route to `AGENTS.md` or `~/.claude/CLAUDE.md`, then archive the file. |
| coverage < 30d | `hold` | Untouched. Not listed as a candidate. |
| coverage ≥ 60d, reads 0 | `archive` | Move to `archive/`, unlink from index. |
| coverage ≥ 30d, reads 0–2, index line > 200 chars | `compact` | Rewrite the **index line** to ≤200 chars. Body untouched. |
| coverage ≥ 30d, reads 0–2, already compact | `hold` | Nothing to do before the 60d gate. |

`created` uses the filename date prefix, not mtime — editing a lesson does not restart its clock.

## Why two clocks

Eviction and compaction are not the same risk, so they do not share a threshold.

**Compaction is lossless and reversible.** It rewrites one index line; the lesson body — where the detail lives — is untouched. The cost it addresses is incurred every session, because the index loads on every request whether or not the lesson is ever opened. The arithmetic is direct: a ~380-character index line is roughly 95 tokens, so a 24-line index costs ~2.3k tokens on every request. Capping lines at 200 characters halves that without evicting anything. That action does not need to wait.

**Eviction is a bet against a signal that under-counts by construction** (see [LEDGER-FORMAT.md](LEDGER-FORMAT.md)). It keeps the long floor.

The original single floor was set at 60 days because that is 2× the 30-day transcript window, so a *first* run would have one untruncated cycle of evidence. That premise expires once the ledger exists and is checkpointed: from then on, coverage is continuous from the item's creation, and a second window buys nothing. The floor was left at 60 for eviction anyway — not for evidence, but because a wrong `archive` is the only verdict here that loses something a user has to notice to recover.

An early corpus therefore produces empty `archive` and `compact` groups. That is the correct output, not a failed run.

## Coverage, not age

```
coverage(item) = observed time since the item existed
               = Σ over recorded scan windows of (window ∩ item lifetime),
                 overlapping windows merged first
```

Windows come from `scans[]` in the ledger, and must be merged before summing — the same day observed by two runs is one day of coverage, not two. Age would count time nobody was watching: if the skill is not run for 40 days, transcripts prune at 30 and a 10-day hole opens, yet raw age keeps accruing. An item must not age into eviction on unobserved time.

Where the ledger has run continuously since before the oldest item, coverage equals age and this distinction is numerically a no-op. Report it as coverage regardless — the two diverge silently and only after the gap has already happened.

## Cap the archive group

At most **5** `archive` proposals per run, oldest coverage first. The rest hold to the next run.

Items are authored in bursts, so they come due in bursts: a corpus seeded over a few days puts its whole first cohort past the floor in the same week. A twenty-row archive table gets approved wholesale without the per-item read that [Verdicts are proposals](#verdicts-are-proposals) requires, which defeats the check. Same reasoning as the one-theme-per-run limit on merges.

## Why merge and promote ignore the floors

The floors protect *eviction* decisions from thin evidence. Neither of these is an eviction.

Merging is bloat-driven and lossless — the rule survives, the cases survive, the originals sit in `archive/` with pointers — so nothing is at risk from doing it early. The cost it addresses (index lines loaded every session) is incurred immediately, not after 60 days.

Promotion rests on *positive* evidence: an item is moved because it was demonstrably read, not because nothing was observed. Waiting adds no information — a floor only ever suppresses a rule that has already proven it earns its place.

Cluster on the **rule**, not the topic. Two lessons about pytest are not a cluster; five lessons that all say *verify the claim against the artifact instead of accepting it* are, whatever subsystem each was learned in. If a merged file cannot state one rule in one sentence, the cluster was topical and should be split back.

Keep merges to one theme per run. A merge that rewrites half the corpus is unreviewable.

## Promotion routing

| The rule is… | Goes to | Form |
|---|---|---|
| specific to this repo — its paths, pipelines, conventions, deployment | `<cwd>/AGENTS.md` | One-line directive + link to the archived lesson for rationale. Cross-agent, not Claude-only. |
| true of the harness or tooling in any repo | user-level global instructions (`~/.claude/CLAUDE.md`, or the equivalent for your harness) | One terse line. This file is read on every request in every project — anything vague costs attention everywhere. |
| durable project *fact* rather than a rule | the memory store | A memory file. Facts are Memory's job; rules are Lessons'. |
| neither general nor repo-specific | stays a lesson | Leave the file. Mark `compact` only if its index line is over 200 chars. |

A promoted lesson moves to `archive/` and loses its index line: the rule now loads automatically, so leaving it in the index pays the context cost twice.

Promotion is append-only on the target file. Never rewrite or reorder existing instructions in `AGENTS.md` or `CLAUDE.md` during a curate run — that is a separate, deliberate edit.

## Verdicts are proposals

Every threshold here is a heuristic over a signal that under-counts by construction (see [LEDGER-FORMAT.md](LEDGER-FORMAT.md)). A lesson can be load-bearing without ever being read — it may have been absorbed into the way a task was approached. So:

- read the item before proposing `archive` for it, and drop the verdict if the content is still obviously live;
- state the evidence for each row, never just the verdict, and name which floor it was measured against;
- prefer `compact` over `archive` whenever the rule is still sound — a long index line is a formatting problem, not grounds for eviction;
- archive, never delete — a wrong archive verdict costs one `mv` to undo.

The 5-row archive cap exists to keep the first of these affordable. If a run wants to propose more, that is the signal to propose fewer and read them properly.
