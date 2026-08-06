# Verdict policy

## Table

Evaluate **top-down; first match wins.**

| Condition | Verdict | Action |
|---|---|---|
| ≥3 items share one rule, any age | `merge` | Collapse into one themed file. |
| reads ≥ 2, from ≥2 sessions, `read_days` spanning ≥ 7d, ledger observation ≥ 30d | `promote?` | **Nominate only** — never applied without per-item confirmation. See [Promotion is nominated, never decided](#promotion-is-nominated-never-decided). |
| coverage < 30d | `hold` | Untouched. Not listed as a candidate. |
| coverage ≥ 60d, reads 0 | `archive` | Move to `archive/`, unlink from index. |
| coverage ≥ 30d, reads 0–2, index line > 200 chars | `compact` | Rewrite the **index line** to ≤200 chars. Body untouched. |
| coverage ≥ 30d, reads 0–2, already compact | `hold` | Nothing to do before the 60d gate. |

`created` uses the filename date prefix, not mtime — editing a lesson does not restart its clock.

"Ledger observation ≥ 30d" is the only condition here that is **not** per-item: it is the total merged span of `scans[]`, asking whether the ledger has watched long enough for a 7-day gap between reads to mean anything. Everything else in the table is a property of the item.

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

## Why promotion counts episodes, not reads

A raw read count has no time dimension, and that is the whole problem. Two reads while a topic is hot are one episode: the file was open because its subject was the active task. Two reads weeks apart are *recurrence* — and recurrence is the only thing that supports the claim promotion makes, which is not "this was useful once" but "this keeps coming up, so load it on every request forever."

**Distinct days is not enough, and this was measured, not assumed.** Every item in the corpus that had ever reached `reads: 2` when the gate was written — all three of them:

| item | read days | span |
|---|---|---|
| a project setup memory | 07-15, 07-16 | **1d** — written ~07-14; one episode crossing midnight |
| a lesson on citing greps | 08-02, 08-05 | 3d |
| a memory of harness gotchas | 07-15, 07-26 | 11d — genuine recurrence |

A `≥2 distinct days` rule promotes the first of those. Consecutive-day reads are the same sitting with a sleep in the middle. Only the **span** between first and last read separates heat from recurrence, so the gate is written on span.

The fix is to add a dimension, not to raise the number. Requiring `reads ≥ 3` would be strictly worse: nothing in the corpus had ever reached 3, so the verdict would simply never fire — and the count is biased low to begin with (see below), so a bigger threshold demands more evidence from the one source that happens to be observable.

**Span, not `last_read − created`.** The obvious cheaper gate — "still being read N days after it was written" — is unsafe here: every memory carries `created_estimated: true`, and one has a `last_read` five days *before* its recorded creation. Span is computed from observed reads alone and never consults `created`.

`read_sessions` and `read_days` are unioned across runs, never summed. A session that straddles a window boundary is seen by two runs, and adding the per-run counts would manufacture recurrence out of one sitting.

## The count only sees one harness

`reads` comes from Claude Code session transcripts. Work done in another tool against the same repo — Copilot, an editor, a different agent — reads these files without leaving a trace the scanner can find. The count is therefore not a sample of your use; it is your *Claude Code share* of it.

The bias is one-directional, so it is safe in one place and dangerous in another:

- **For `promote`,** it means under-promotion. That is tolerable, and it is the reason the threshold stays at 2 rather than rising.
- **For `archive`,** it is the live hazard: a rule leaned on daily in another tool reads as `reads: 0` here and comes due for eviction on schedule. Nothing in the ledger can distinguish that from a genuinely dead lesson.

This is why `archive` keeps the 60-day floor, the 5-row cap, and the requirement to read the item first. Those are not ceremony — they are the only defence against a blind spot the data cannot see.

## Promotion is nominated, never decided

`promote?` produces **nominations**. The skill never promotes anything the user has not confirmed item by item, and confirming one nomination says nothing about the next.

Three reasons the group approval used for `archive`, `compact` and `merge` is not enough here:

- **It is the widest-blast-radius action in the skill.** Every other verdict rearranges the corpus. Promotion writes into `AGENTS.md` or the global instructions file — text that then loads on every request in every session, and that no later curate run will ever revisit, because the ledger stops tracking a rule once it leaves the corpus. There is no `reads: 0` for a promoted line.
- **The evidence is one-harness evidence.** Under Copilot, or an editor, or any tool that writes no Claude Code transcript, the counts are silent (see above). A rule can be load-bearing for a year and never clear the gate. Nomination-only keeps the skill from mistaking its own blind spot for a verdict.
- **The wording matters more than the decision.** A promoted rule is one line that has to survive out of context. That line is worth reading before it is written, which a grouped yes/no does not allow.

Two consequences:

- **Confirmation is per item, and shows the artifact.** Name the target file and the exact line to be appended, with the evidence beside it. The user may accept, reword, retarget, or skip — and rewording is the expected case, not an exception.
- **The user may nominate anything.** Any live item can be promoted on request whatever the counts say, and the report must say so. This is the only route by which a rule used exclusively outside Claude Code ever gets promoted; without it the blind spot is permanent.

The thresholds in the table therefore rank a shortlist — they no longer decide anything. That is the right weight for them: on the corpus they were derived from, only one item in three that reached `reads: 2` also cleared the span, so an automatic gate this tight would spend most runs firing on nothing while the rules that actually earned promotion sat unseen in another tool's history.

## Promotion routing

| The rule is… | Goes to | Form |
|---|---|---|
| specific to this repo — its paths, pipelines, conventions, deployment | `<cwd>/AGENTS.md` | One-line directive + link to the archived lesson for rationale. Cross-agent, not Claude-only. |
| true of the harness or tooling in any repo | user-level global instructions (`~/.claude/CLAUDE.md`, or the equivalent for your harness) | One terse line. This file is read on every request in every project — anything vague costs attention everywhere. |
| durable project *fact* rather than a rule | the memory store | A memory file. Facts are Memory's job; rules are Lessons'. |
| neither general nor repo-specific | stays a lesson | Leave the file. Mark `compact` only if its index line is over 200 chars. |

Route each nomination *before* asking for confirmation — the target file is half of what the user is agreeing to, and "promote this" means nothing until it reads "append this line to that file".

A promoted lesson moves to `archive/` and loses its index line: the rule now loads automatically, so leaving it in the index pays the context cost twice.

Promotion is append-only on the target file. Never rewrite or reorder existing instructions in `AGENTS.md` or `CLAUDE.md` during a curate run — that is a separate, deliberate edit.

## Verdicts are proposals

Every threshold here is a heuristic over a signal that under-counts by construction (see [LEDGER-FORMAT.md](LEDGER-FORMAT.md)). A lesson can be load-bearing without ever being read — it may have been absorbed into the way a task was approached. So:

- read the item before proposing `archive` for it, and drop the verdict if the content is still obviously live;
- state the evidence for each row, never just the verdict, and name which floor it was measured against;
- prefer `compact` over `archive` whenever the rule is still sound — a long index line is a formatting problem, not grounds for eviction;
- archive, never delete — a wrong archive verdict costs one `mv` to undo.

The 5-row archive cap exists to keep the first of these affordable. If a run wants to propose more, that is the signal to propose fewer and read them properly.
